import io
import json
from pathlib import Path

from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from PIL import Image

# Replace 'your_app_name' with your actual app name
from products.models import Category, Product, ProductType, ProductVariant


class Command(BaseCommand):
    help = "Import products. Resolves image paths relative to JSON file location."

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the JSON file")

    def get_placeholder_image(self):
        """Generates a simple 100x100 grey image in memory."""
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        img_io = io.BytesIO()
        img.save(img_io, format="JPEG")
        return ContentFile(img_io.getvalue(), name="placeholder.jpg")

    def handle(self, *args, **options):
        json_path = Path(options["json_file"]).resolve()
        json_dir = json_path.parent  # Get directory containing the JSON file

        if not json_path.exists():
            raise CommandError(f"File {json_path} does not exist")

        # 1. Fetch Prerequisites
        try:
            category = Category.objects.get(title="Animals")
        except Category.DoesNotExist:
            raise CommandError("Category 'Animals' does not exist.")

        try:
            product_type = ProductType.objects.get(name="Sculpture")
            allowed_attribute_slugs = list(
                product_type.allowed_attributes.values_list("slug", flat=True)
            )
        except ProductType.DoesNotExist:
            raise CommandError("ProductType 'Sculpture' does not exist.")

        # 2. Load Data
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.stdout.write(f"Importing {len(data)} products from {json_dir}...")
        success_count = 0

        for item in data:
            try:
                with transaction.atomic():
                    clean_title = item.get("clean_title") or item.get("title")
                    sku = item.get("sku")

                    # --- FIX: Resolve Image Path Relative to JSON Directory ---
                    relative_img_path = item.get("local_image_path")
                    full_img_path = None

                    if relative_img_path:
                        # Combine JSON dir with relative path
                        full_img_path = json_dir / relative_img_path

                    # Check if file exists at that resolved path
                    has_image = full_img_path and full_img_path.exists()

                    if not has_image and relative_img_path:
                        self.stdout.write(
                            self.style.WARNING(f"Image not found at: {full_img_path}")
                        )

                    # --- Product Creation ---
                    product, created = Product.objects.get_or_create(
                        slug=slugify(clean_title),
                        defaults={
                            "title": clean_title,
                            "product_type": product_type,
                            "status": Product.Status.PUBLISHED,
                            "description": item.get("title", ""),
                            "base_price": 0.00,
                            # Use placeholder initially to satisfy NOT NULL constraint
                            "thumbnail": self.get_placeholder_image(),
                        },
                    )

                    product.categories.add(category)

                    # Save Real Product Image
                    if has_image:
                        # Update if it's a new product OR the current one is just a placeholder
                        if created or "placeholder" in str(product.thumbnail):
                            with open(full_img_path, "rb") as img_file:
                                product.thumbnail.save(
                                    full_img_path.name, File(img_file), save=True
                                )

                    # --- Attribute Logic ---
                    variant_attributes = {}

                    if "width_cm" in item and item["width_cm"]:
                        variant_attributes["width"] = item["width_cm"]
                    if "height_cm" in item and item["height_cm"]:
                        variant_attributes["height"] = item["height_cm"]
                    if "depth_cm" in item and item["depth_cm"]:
                        variant_attributes["depth"] = item["depth_cm"]

                    # Autofill missing required attributes
                    for required_slug in allowed_attribute_slugs:
                        if required_slug not in variant_attributes:
                            variant_attributes[required_slug] = "null"

                    # --- Variant Creation ---
                    variant, v_created = ProductVariant.objects.update_or_create(
                        sku=sku,
                        defaults={
                            "product": product,
                            "price": 0.00,
                            "stock_quantity": 0,
                            "attributes": variant_attributes,
                            # Use placeholder initially
                            "image": self.get_placeholder_image(),
                        },
                    )

                    # Save Real Variant Image
                    if has_image:
                        with open(full_img_path, "rb") as img_file:
                            variant.image.save(
                                full_img_path.name, File(img_file), save=True
                            )

                    variant.full_clean()
                    variant.save()

                    success_count += 1
                    status_msg = "Created" if v_created else "Updated"
                    self.stdout.write(self.style.SUCCESS(f"[{status_msg}] {sku}"))

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to import item {item.get('sku', 'Unknown')}: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully imported {success_count} products.")
        )
