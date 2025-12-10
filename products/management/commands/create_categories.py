from django.core.management.base import BaseCommand

from products.models import Category


class Command(BaseCommand):
    help = "Creates hierarchical categories: Animals, Wall Art, Accents, Outdoor, Collections"

    def handle(self, *args, **options):
        category_structure = {
            "Animals": ["Wild", "Farm", "Birds", "Aquatic"],
            "Wall Art": ["Abstract", "Mounted Heads", "Reliefs"],
            "Accents": ["Astronauts", "Human Figures", "Vehicles"],
            "Outdoor": ["Garden Statues", "Yard Art", "Large Scale"],
            "Collections": ["Space Age", "Industrial", "Minimalist"],
        }

        self.stdout.write("Checking and creating category hierarchy...")

        for parent_name, children in category_structure.items():
            parent_obj, created = Category.objects.get_or_create(
                title=parent_name,
                defaults={"parent": None},
            )

            self._log_output(parent_name, created, level=0)

            for child_name in children:
                child_obj, child_created = Category.objects.get_or_create(
                    title=child_name,
                    defaults={"parent": parent_obj},
                )

                if not child_created and child_obj.parent != parent_obj:
                    child_obj.parent = parent_obj
                    child_obj.save()
                    self.stdout.write(
                        self.style.NOTICE(
                            f'\tMOVED: "{child_name}" under "{parent_name}"'
                        )
                    )

                self._log_output(child_name, child_created, level=1)

    def _log_output(self, name, created, level=0):
        indent = "\t" * level
        if created:
            self.stdout.write(self.style.SUCCESS(f'{indent}CREATED: "{name}"'))
        else:
            self.stdout.write(self.style.WARNING(f'{indent}EXISTED: "{name}"'))
