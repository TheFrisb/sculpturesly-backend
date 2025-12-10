from rest_framework import serializers

from .models import (
    Attribute,
    Category,
    Collection,
    Product,
    ProductGalleryImage,
    ProductType,
    ProductVariant,
)

# --- CATEGORY SERIALIZERS ---


class CategorySerializer(serializers.ModelSerializer):
    seo_metadata = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "image",
            "parent",
            "seo_metadata",
        ]

    def get_seo_metadata(self, obj):
        return obj.get_seo_data()


class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    seo_metadata = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "title", "slug", "image", "children", "seo_metadata"]

    def get_children(self, obj):
        if hasattr(obj, "children_prefetched"):
            children = obj.children_prefetched
        else:
            children = obj.get_children()

        if children:
            return CategoryTreeSerializer(
                children, many=True, context=self.context
            ).data
        return []

    def get_seo_metadata(self, obj):
        return obj.get_seo_data()


# --- COLLECTION SERIALIZERS ---


class CollectionSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Collection
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "image",
            "is_active",
            "product_count",
        ]


# --- PRODUCT RELATED SERIALIZERS ---
class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["id", "name", "slug", "choices"]


class ProductTypeSerializer(serializers.ModelSerializer):
    allowed_attributes = AttributeSerializer(many=True, read_only=True)

    class Meta:
        model = ProductType
        fields = [
            "id",
            "name",
            "allowed_attributes",
        ]


class ProductGalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGalleryImage
        fields = ["id", "image", "alt_text", "is_feature", "variant"]


class ProductVariantSerializer(serializers.ModelSerializer):
    is_in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "sku",
            "price",
            "compare_at_price",
            "stock_quantity",
            "is_in_stock",
            "image",
            "attributes",
        ]

    def get_is_in_stock(self, obj):  # noqa
        return obj.stock_quantity > 0


class ProductListSerializer(serializers.ModelSerializer):
    category_names = serializers.StringRelatedField(source="categories", many=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "status",
            "thumbnail",
            "base_price",
            "category_names",
            "created_at",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    product_type = ProductTypeSerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    gallery_images = ProductGalleryImageSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    seo_metadata = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "slug",
            "status",
            "description",
            "base_price",
            "thumbnail",
            "specifications",
            "product_type",
            "categories",
            "variants",
            "gallery_images",
            "seo_metadata",
        ]

    def get_seo_metadata(self, obj):
        return obj.get_seo_data()
