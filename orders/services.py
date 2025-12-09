from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Order, OrderAddress, OrderItem


def create_order_from_cart(user, cart, shipping_data, billing_data=None):
    if cart.items.count() == 0:
        raise ValidationError("Cannot create order from empty cart.")

    with transaction.atomic():
        shipping_address = OrderAddress.objects.create(**shipping_data)

        if billing_data:
            billing_address = OrderAddress.objects.create(**billing_data)
        else:
            billing_address = OrderAddress.objects.create(**shipping_data)

        order = Order.objects.create(
            # user=user if user.is_authenticated else None,
            email=shipping_data["email"],
            shipping_address=shipping_address,
            billing_address=billing_address,
            total_amount=cart.total_price,
            status=Order.Status.PENDING,
        )

        order_items = []
        for cart_item in cart.items.select_related(
            "product_variant", "product_variant__product"
        ):
            variant = cart_item.product_variant

            item = OrderItem(
                order=order,
                product_variant=variant,
                product_sku=variant.sku,
                product_name=variant.product.title,
                attributes=variant.attributes,
                unit_price=variant.price,
                quantity=cart_item.quantity,
                total_price=cart_item.total_price,
            )
            order_items.append(item)

        OrderItem.objects.bulk_create(order_items)

        return order
