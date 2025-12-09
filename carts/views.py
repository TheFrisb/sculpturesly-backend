from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.utils import get_session_key
from .constants import CART_SESSION_COOKIE_LABEL
from .models import Cart, CartItem
from .serializers import (
    CartItemAddSerializer,
    CartItemUpdateSerializer,
    CartSerializer,
)
from .utils import get_cart_from_request


class CartViewSet(viewsets.GenericViewSet):
    serializer_class = CartSerializer

    def list(self, request, *args, **kwargs):
        cart = get_cart_from_request(request, True, True)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="items")
    def add_item(self, request):
        cart = get_cart_from_request(request, True, False)

        serializer = CartItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variant_id = serializer.validated_data["product_variant_id"]
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
            cart_item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                product_variant_id=variant_id,
                defaults={"quantity": 0},
            )

            new_quantity = cart_item.quantity + quantity

            if new_quantity > cart_item.product_variant.stock_quantity:
                return Response(
                    {
                        "error": f"Only {cart_item.product_variant.stock_quantity} in stock."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_item.quantity = new_quantity
            cart_item.save()

        return self.list(request)

    @action(detail=True, methods=["patch"], url_path="update")
    def update_item_quantity(self, request, pk=None):
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_quantity = serializer.validated_data["quantity"]

        cart_session_key = get_session_key(request, CART_SESSION_COOKIE_LABEL, False)

        with transaction.atomic():
            cart_item = get_object_or_404(
                CartItem.objects.select_for_update(),
                pk=pk,
                cart__session_key=cart_session_key,
            )

            if new_quantity > cart_item.product_variant.stock_quantity:
                return Response(
                    {"error": "Not enough stock."}, status=status.HTTP_400_BAD_REQUEST
                )

            cart_item.quantity = new_quantity
            cart_item.save()

        return self.list(request)

    @action(detail=True, methods=["delete"], url_path="remove")
    def remove_item(self, request, pk=None):
        cart_session_key = get_session_key(request, CART_SESSION_COOKIE_LABEL, False)

        cart_item = get_object_or_404(
            CartItem, pk=pk, cart__session_key=cart_session_key
        )
        cart_item.delete()

        return self.list(request)
