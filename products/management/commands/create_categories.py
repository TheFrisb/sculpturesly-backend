from django.core.management.base import BaseCommand
from products.models import Category


class Command(BaseCommand):
    help = "Creates initial root categories: Animals, Wall art, Misc"

    def handle(self, *args, **options):
        category_names = ["Animals", "Wall art", "Misc"]

        self.stdout.write("Checking and creating categories...")

        for name in category_names:
            category, created = Category.objects.get_or_create(
                title=name,
                defaults={"parent": None},
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'CREATED: "{name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'EXISTED: "{name}"'))
