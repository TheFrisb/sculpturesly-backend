from django.core.management.base import BaseCommand
from django.utils.text import slugify

from products.models import Attribute, ProductType


class Command(BaseCommand):
    help = "Creates initial attributes (Width, Height, Depth) and the Sculpture product type."

    def handle(self, *args, **options):
        target_attributes = ["Width", "Height", "Depth", "Color"]

        created_attr_objects = []

        self.stdout.write("--- Processing Attributes ---")

        for name in target_attributes:
            slug = slugify(name)
            attr, created = Attribute.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "choices": [],
                },
            )
            created_attr_objects.append(attr)

            if created:
                self.stdout.write(self.style.SUCCESS(f'Attribute Created: "{name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Attribute Existed: "{name}"'))

        self.stdout.write("\n--- Processing Product Type ---")

        pt_name = "Sculpture"
        product_type, created = ProductType.objects.get_or_create(name=pt_name)

        if created:
            self.stdout.write(self.style.SUCCESS(f'ProductType Created: "{pt_name}"'))
        else:
            self.stdout.write(self.style.WARNING(f'ProductType Existed: "{pt_name}"'))

        product_type.allowed_attributes.add(*created_attr_objects)

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully linked attributes {target_attributes} to "{pt_name}"'
            )
        )
