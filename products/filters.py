import django_filters
from .models import Product, Category


class ProductFilter(django_filters.FilterSet):
    categories__slug = django_filters.CharFilter(method="filter_category_tree")

    class Meta:
        model = Product
        fields = ["collections__slug"]

    def filter_category_tree(self, queryset, name, value):
        """
        Filters products by category slug, including all MPTT descendants.
        """
        try:
            category = Category.objects.get(slug=value)
            categories_tree = category.get_descendants(include_self=True)

            return queryset.filter(categories__in=categories_tree).distinct()

        except Category.DoesNotExist:
            return queryset.none()
