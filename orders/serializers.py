from django_countries.serializer_fields import CountryField
from rest_framework import serializers

from products.serializers import ProductVariantSerializer

from .models import Order, OrderAddress, OrderItem


class OrderAddressSerializer(serializers.ModelSerializer):
    country = CountryField(country_dict=True)

    class Meta:
        model = OrderAddress
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_sku",
            "product_name",
            "attributes",
            "quantity",
            "unit_price",
            "total_price",
            "variant",
        ]


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = OrderAddressSerializer(read_only=True)
    billing_address = OrderAddressSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "email",
            "total_amount",
            "created_at",
            "shipping_address",
            "billing_address",
            "items",
            "is_paid",
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    shipping_address = OrderAddressSerializer()
    billing_address = OrderAddressSerializer(required=False, allow_null=True)

    class Meta:
        model = Order
        fields = ["email", "shipping_address", "billing_address"]
