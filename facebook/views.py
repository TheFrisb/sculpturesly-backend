from django.conf import settings
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from carts.models import Cart
from orders.models import Order
from products.models import Product, ProductVariant

from .schemas.meta_conversion_schemas import MetaCustomData
from .serializers import (
    AddToCartSerializer,
    BaseTrackingSerializer,
    PurchaseSerializer,
    ViewContentSerializer,
)
from .services.meta_catalogue_service import MetaCatalogueService
from .tasks import send_meta_event_task
from .utils import build_user_context


class BaseFacebookView(APIView):
    permission_classes = [permissions.AllowAny]

    def dispatch_event(
        self, event_name, event_id, url, user_context, custom_data
    ):  # noqa
        send_meta_event_task(
            event_name=event_name,
            event_id=event_id,
            user_data_dict=user_context.model_dump(),
            custom_data_dict=custom_data.model_dump(),
            url=url,
        )


class ViewContentView(BaseFacebookView):
    def post(self, request):
        serializer = ViewContentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        product = get_object_or_404(Product, slug=data["product_slug"])
        price = product.base_price
        content_id = str(product.id)

        if data.get("variant_sku"):
            variant = ProductVariant.objects.filter(sku=data["variant_sku"]).first()
            if variant:
                price = variant.price
                content_id = str(variant.id)

        custom_data = MetaCustomData(
            content_name=product.title, content_ids=[content_id], value=float(price)
        )

        self.dispatch_event(
            "ViewContent",
            data["event_id"],
            data["url"],
            build_user_context(request),
            custom_data,
        )
        return Response({"status": "tracked"})


class AddToCartView(BaseFacebookView):
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        variant = get_object_or_404(ProductVariant, sku=data["variant_sku"])

        custom_data = MetaCustomData(
            content_name=variant.product.title,
            content_ids=[str(variant.id)],
            value=float(variant.price) * data["quantity"],
        )

        self.dispatch_event(
            "AddToCart",
            data["event_id"],
            data["url"],
            build_user_context(request),
            custom_data,
        )
        return Response({"status": "tracked"})


class InitiateCheckoutView(BaseFacebookView):
    def post(self, request):
        serializer = BaseTrackingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session_key = request.session.session_key
        if not session_key:
            return Response(
                {
                    "detail": "Session cookie missing.",
                    "code": "missing_session",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = get_object_or_404(
            Cart, session_key=request.session.session_key, status="ACTIVE"
        )

        content_ids = [str(item.product_variant.id) for item in cart.items.all()]

        custom_data = MetaCustomData(
            content_ids=content_ids,
            num_items=len(content_ids),
            value=float(cart.total_price),
        )

        self.dispatch_event(
            "InitiateCheckout",
            data["event_id"],
            data["url"],
            build_user_context(request),
            custom_data,
        )
        return Response({"status": "tracked"})


class PurchaseView(BaseFacebookView):
    def post(self, request):
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = get_object_or_404(Order, order_number=data["order_number"])

        user_context = build_user_context(request)
        if order.shipping_address:
            addr = order.shipping_address
            user_context.email = order.email
            user_context.first_name = addr.first_name
            user_context.last_name = addr.last_name
            user_context.phone = addr.phone
            user_context.city = addr.city
            user_context.state = addr.state
            user_context.zip_code = addr.postal_code
            user_context.country = str(addr.country)

        content_ids = [
            str(item.product_variant.id)
            for item in order.items.all()
            if item.product_variant
        ]

        custom_data = MetaCustomData(
            value=float(order.total_amount),
            content_ids=content_ids,
            order_id=order.order_number,
            num_items=len(content_ids),
        )

        self.dispatch_event(
            "Purchase",
            order.order_number,
            data["url"],
            user_context,
            custom_data,
        )
        return Response({"status": "tracked"})


class MetaCatalogFeedView(View):
    filename = "meta_catalog.csv"

    def get(self, request, *args, **kwargs):
        domain = settings.BACKEND_BASE_URL

        service = MetaCatalogueService(
            backend_domain=settings.BACKEND_BASE_URL,
            frontend_domain=settings.FRONTEND_BASE_URL,
            currency="EUR",
            brand_name="Sculpturesly",
        )

        response = StreamingHttpResponse(
            service.generate_feed(save_to_file=False), content_type="text/csv"
        )

        response["Content-Disposition"] = f'attachment; filename="{self.filename}"'
        return response
