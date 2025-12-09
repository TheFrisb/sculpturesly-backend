import logging

from django.core.exceptions import ValidationError
from rest_framework import generics, status, views
from rest_framework.response import Response

from carts.models import Cart
from carts.utils import get_cart_from_request
from stripe_payments.services.stripe_checkout_service import StripeCheckoutService

from .models import Order
from .serializers import OrderCreateSerializer, OrderReadSerializer
from .services import create_order_from_cart

logger = logging.getLogger(__name__)


class CheckoutView(views.APIView):
    """
    Handles checkout flow with a flat, linear architecture.
    """

    def post(self, request):
        cart = self._get_validated_cart(request)
        if not cart:
            return Response(
                {"error": "Cart is empty or not found.", "code": "cart_empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Checkout validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = self._create_local_order(request, cart, serializer.validated_data)
            checkout_url = self._initiate_stripe_payment(request, order)

            return Response(
                {
                    "status": "success",
                    "order_number": order.order_number,
                    "checkout_url": checkout_url,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValidationError as e:
            logger.warning(f"Domain validation error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return self._handle_unexpected_error(e)

    def _get_validated_cart(self, request):
        cart = get_cart_from_request(request, False, True)

        if not cart or cart.items.count() == 0:
            return None

        return cart

    def _create_local_order(self, request, cart, validated_data):
        shipping_data = validated_data["shipping_address"]
        billing_data = validated_data.get("billing_address")

        shipping_data["email"] = validated_data["email"]

        order = create_order_from_cart(
            user=request.user,
            cart=cart,
            shipping_data=shipping_data,
            billing_data=billing_data,
        )
        logger.info(f"Order created locally: {order.order_number}")
        return order

    def _initiate_stripe_payment(self, request, order):
        stripe_service = StripeCheckoutService(order, request=request)
        url = stripe_service.create_checkout_session()
        logger.info(f"Stripe session created for {order.order_number}")
        return url

    def _handle_unexpected_error(self, error):
        logger.error(f"Checkout Process Failed: {str(error)}", exc_info=True)

        return Response(
            {"error": "Unable to process payment. Please try again later."},
            status=status.HTTP_502_BAD_GATEWAY,
        )


class OrderRetrieveView(generics.RetrieveAPIView):
    serializer_class = OrderReadSerializer
    queryset = Order.objects.all()
