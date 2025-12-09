from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from products.filters import ProductFilter
from products.models import Category, Collection, Product
from products.serializers import (
    CategoryTreeSerializer,
    CollectionSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class CategoryListView(ListAPIView):
    serializer_class = CategoryTreeSerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(parent__isnull=True).prefetch_related("children")


class CollectionListView(ListAPIView):
    serializer_class = CollectionSerializer

    def get_queryset(self):
        return Collection.objects.filter(is_active=True)


class ProductViewSet(ReadOnlyModelViewSet):
    queryset = Product.objects.filter(status=Product.Status.PUBLISHED).order_by(
        "-created_at"
    )
    lookup_field = "slug"
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ["title", "description", "specifications"]
    ordering_fields = ["base_price", "created_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == "retrieve":
            return queryset.prefetch_related(
                "variants",
                "gallery_images",
                "categories",
                "product_type__allowed_attributes",
                "collections",
            )

        return queryset.prefetch_related("categories")
