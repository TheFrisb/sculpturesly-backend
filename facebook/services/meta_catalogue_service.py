import csv
import os
from decimal import Decimal
from typing import Any, Dict, Iterator, List, Union

from django.conf import settings
from django.utils.html import strip_tags

# Import your models
from products.models import Product, ProductVariant


class Echo:
    """
    A helper class that implements the file-like interface.
    Instead of writing to a buffer, it simply returns the value.
    This allows us to use the csv module for streaming.
    """

    def write(self, value):
        return value


class MetaCatalogueService:
    """
    Generates a Facebook/Instagram Catalog compliant CSV feed.
    """

    CSV_HEADERS = [
        "id",
        "title",
        "description",
        "availability",
        "condition",
        "price",
        "sale_price",
        "link",
        "image_link",
        "brand",
        "item_group_id",
        "google_product_category",
        "color",
        "size",
        "gender",
        "age_group",
        "additional_image_link",
    ]

    def __init__(
        self,
        backend_domain: str,
        frontend_domain: str,
        currency: str = "USD",
        brand_name: str = "MyBrand",
    ):
        self.backend_domain = backend_domain.rstrip("/")
        self.frontend_domain = frontend_domain.rstrip("/")
        self.currency = currency
        self.brand_name = brand_name

    def get_queryset(self):
        return (
            ProductVariant.objects.filter(product__status=Product.Status.PUBLISHED)
            .select_related("product", "product__product_type")
            .prefetch_related(
                "product__categories",
                "gallery_images",
                "product__gallery_images",
            )
            .order_by("product__id", "id")
        )

    def _build_absolute_url(self, path: str, to_backend: bool) -> str:
        if not path:
            return ""
        if path.startswith("http"):
            return path

        domain = self.backend_domain if to_backend else self.frontend_domain
        return f"{domain}{path}"

    def _format_price(self, amount: Decimal) -> str:
        if amount is None:
            return ""
        return f"{amount:.2f} {self.currency}"

    def _get_availability(self, variant: ProductVariant) -> str:
        return "in stock" if variant.stock_quantity > 0 else "out of stock"

    def _extract_attribute(self, attributes: dict, keys: List[str]) -> str:
        for key in keys:
            if key in attributes:
                return str(attributes[key])
            for attr_key, val in attributes.items():
                if attr_key.lower() == key.lower():
                    return str(val)
        return ""

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = strip_tags(text)
        return " ".join(text.split())

    def process_variant(self, variant: ProductVariant) -> Dict[str, Any]:
        product = variant.product

        price_val = variant.price
        sale_price_val = None
        if variant.compare_at_price and variant.compare_at_price > variant.price:
            price_val = variant.compare_at_price
            sale_price_val = variant.price

        product_url = f"/products/{product.slug}?sku={variant.sku}"
        main_image = variant.image.url if variant.image else product.thumbnail.url

        gallery_imgs = [img.image.url for img in variant.gallery_images.all()]
        if not gallery_imgs:
            gallery_imgs = [img.image.url for img in product.gallery_images.all()]
        additional_images = ",".join(
            [self._build_absolute_url(url, True) for url in gallery_imgs[:10]]
        )

        category = product.categories.first()
        google_category = category.title if category else ""

        color = self._extract_attribute(
            variant.attributes, ["Color", "Colour", "Shade"]
        )
        size = self._extract_attribute(variant.attributes, ["Size", "Dimensions"])
        gender = (
            self._extract_attribute(variant.attributes, ["Gender", "Sex"]) or "unisex"
        )

        return {
            "id": variant.sku,
            "title": self._clean_text(product.title),
            "description": self._clean_text(product.description),
            "availability": self._get_availability(variant),
            "condition": "new",
            "price": self._format_price(price_val),
            "sale_price": self._format_price(sale_price_val) if sale_price_val else "",
            "link": self._build_absolute_url(product_url, False),
            "image_link": self._build_absolute_url(main_image, True),
            "brand": self.brand_name,
            "item_group_id": product.id,
            "google_product_category": google_category,
            "color": color,
            "size": size,
            "gender": gender,
            "age_group": "adult",
            "additional_image_link": additional_images,
        }

    def generate_feed(
        self, save_to_file: bool = False, filename: str = "meta_catalog.csv"
    ) -> Union[str, Iterator[str]]:
        """
        Main entry point.

        :param save_to_file: If True, saves to MEDIA_ROOT and returns the file path.
                             If False, returns a generator (iterator) for streaming.

        :param filename: Name of the file (used for saving or download header).
        """
        if save_to_file:
            return self._generate_to_file(filename)
        else:
            return self._generate_stream()

    def _generate_to_file(self, filename: str) -> str:
        output_dir = os.path.join(settings.MEDIA_ROOT, "feeds")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        with open(output_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.CSV_HEADERS)
            writer.writeheader()

            for variant in self.get_queryset().iterator(chunk_size=1000):
                writer.writerow(self.process_variant(variant))

        return output_path

    def _generate_stream(self) -> Iterator[str]:
        pseudo_buffer = Echo()
        writer = csv.DictWriter(pseudo_buffer, fieldnames=self.CSV_HEADERS)

        yield writer.writeheader()

        for variant in self.get_queryset().iterator(chunk_size=1000):
            yield writer.writerow(self.process_variant(variant))
