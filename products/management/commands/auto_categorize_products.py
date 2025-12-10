import concurrent.futures
import json

import openai
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from products.models import Category, Product


class Command(BaseCommand):
    help = "Auto-assign categories using OpenAI. Processes products in batches."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size", type=int, default=20, help="Products per OpenAI call"
        )
        parser.add_argument(
            "--max-workers", type=int, default=3, help="Parallel threads"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of products to process",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "OPENAI_API_KEY", None):
            self.stdout.write(
                self.style.ERROR("OPENAI_API_KEY is missing from settings.")
            )
            return

        category_tree_str, category_lookup = self.get_category_context()

        self.stdout.write(f"Loaded {len(category_lookup)} categories.")

        products = Product.objects.all().order_by("-created_at")
        if options["limit"]:
            products = products[: options["limit"]]

        total_products = products.count()
        if total_products == 0:
            self.stdout.write("No products found.")
            return

        self.stdout.write(f"Processing {total_products} products with LLM...")

        batch_size = options["batch_size"]
        products_list = list(products)
        batches = [
            products_list[i : i + batch_size]
            for i in range(0, total_products, batch_size)
        ]

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=options["max_workers"]
        ) as executor:
            future_to_batch = {
                executor.submit(
                    self.process_batch, batch, category_tree_str, category_lookup
                ): batch
                for batch in batches
            }

            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    result_msg = future.result()
                    self.stdout.write(result_msg)
                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(f"Batch generated an exception: {exc}")
                    )

    def get_category_context(self):
        categories = Category.objects.all().select_related("parent")
        lookup = {c.title.lower(): c for c in categories}

        lines = []
        for cat in categories:
            if cat.parent is None:
                lines.append(f"- {cat.title}")
                children = cat.children.all()
                for child in children:
                    lines.append(f"  - {child.title}")

        return "\n".join(lines), lookup

    def process_batch(self, batch, category_tree_str, category_lookup):
        connection.close()

        products_data = []
        for p in batch:
            size_info = p.specifications.get("dimensions", "") or ""
            products_data.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "description": p.description[:200],
                    "specs": size_info,
                }
            )

        prompt = f"""
        You are an inventory assistant. 
        Assign the most relevant categories from the provided CATEGORY TREE to the PRODUCTS list.

        RULES:
        1. Use ONLY exact names from the CATEGORY TREE.
        2. A product can have multiple categories (Poly-hierarchy).
        3. Example: A "Garden Truck" goes in "Vehicles" AND "Garden Statues".
        4. Example: A "Mini Astronaut" goes in "Astronauts" AND "Accents".
        5. Return ONLY valid JSON in this format: {{ "product_id": ["Category A", "Category B"] }}

        CATEGORY TREE:
        {category_tree_str}

        PRODUCTS:
        {json.dumps(products_data)}
        """

        try:
            client = openai.Client(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise JSON generator."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            mapping = json.loads(content)

            count = 0
            updated_logs = []

            for p_id_str, cat_names in mapping.items():
                try:
                    p_id = int(p_id_str)
                    product = next((p for p in batch if p.id == p_id), None)

                    if product:
                        cats_to_add = []
                        valid_names = []

                        for name in cat_names:
                            cat_obj = category_lookup.get(name.strip().lower())
                            if cat_obj:
                                cats_to_add.append(cat_obj)
                                valid_names.append(cat_obj.title)

                        if cats_to_add:
                            product.categories.add(*cats_to_add)
                            count += 1
                            updated_logs.append(
                                f'   [UPDATED] "{product.title}" -> {valid_names}'
                            )

                except Exception as e:
                    updated_logs.append(f"   [ERROR] Processing ID {p_id_str}: {e}")

            summary = self.style.SUCCESS(
                f"Batch complete: Updated {count}/{len(batch)} products."
            )
            details = "\n".join(updated_logs)

            return f"{summary}\n{details}"

        except Exception as e:
            return self.style.ERROR(f"OpenAI Call Failed: {e}")
