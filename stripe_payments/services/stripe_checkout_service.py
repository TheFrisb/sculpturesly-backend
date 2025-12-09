import stripe
from django.conf import settings
from rest_framework.exceptions import APIException

from carts.constants import CART_SESSION_COOKIE_LABEL
from common.utils import get_session_key
from orders.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeCheckoutService:
    def __init__(self, order: Order, request=None):
        self.order = order
        self.request = request

    def _get_line_items(self):
        """
        Maps OrderItems to Stripe Line Items.
        """
        line_items = []

        for item in self.order.items.all():
            unit_amount = int(item.unit_price * 100)

            item_data = {
                "price_data": {
                    "currency": "eur",
                    "unit_amount": unit_amount,
                    "product_data": {
                        "name": item.product_name,
                        "metadata": {"sku": item.product_sku},
                    },
                },
                "quantity": item.quantity,
            }

            if item.product_variant and item.product_variant.image:
                if self.request:
                    image_url = self.request.build_absolute_uri(
                        item.product_variant.image.url
                    )
                    item_data["price_data"]["product_data"]["images"] = [image_url]

            line_items.append(item_data)

        return line_items

    def create_checkout_session(self):
        """
        Creates a Stripe Checkout Session and returns the URL.
        """
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=self._get_line_items(),
                mode="payment",
                customer_email=self.order.email,
                metadata={
                    "order_number": self.order.order_number,
                    "order_id": str(self.order.id),
                    "cart_session_key": str(
                        get_session_key(self.request, CART_SESSION_COOKIE_LABEL, False)
                    ),
                },
                success_url=f"{settings.FRONTEND_BASE_URL}/thank-you/{self.order.id}",
                cancel_url=f"{settings.FRONTEND_BASE_URL}/checkout",
                client_reference_id=str(self.order.id),
            )

            return checkout_session.url

        except stripe.error.StripeError as e:
            raise APIException(f"Stripe Error: {str(e)}")
