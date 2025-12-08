from rest_framework import serializers


class BaseTrackingSerializer(serializers.Serializer):
    event_id = serializers.CharField(required=True)
    url = serializers.URLField(required=True)


class ViewContentSerializer(BaseTrackingSerializer):
    product_slug = serializers.SlugField(required=True)
    variant_sku = serializers.CharField(required=False, allow_null=True)


class AddToCartSerializer(BaseTrackingSerializer):
    variant_sku = serializers.CharField(required=True)
    quantity = serializers.IntegerField(min_value=1, default=1)


class PurchaseSerializer(BaseTrackingSerializer):
    order_number = serializers.CharField(required=True)
