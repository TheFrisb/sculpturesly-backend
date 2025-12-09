import uuid

from common.utils import get_session_key, replace_session_key
from .constants import CART_SESSION_COOKIE_LABEL
from .models import Cart


def get_cart_from_request(request, auto_create=False, prefetch_items=True):
    cart_key = get_session_key(request, CART_SESSION_COOKIE_LABEL, True)

    qs = Cart.objects.filter(session_key=cart_key, status=Cart.Status.ACTIVE)

    if prefetch_items:
        qs = qs.prefetch_related(
            "items",
            "items__product_variant",
            "items__product_variant__product",
        )

    cart = qs.first()

    if not cart and auto_create:
        new_key = str(uuid.uuid4())
        replace_session_key(request, CART_SESSION_COOKIE_LABEL, new_key)
        cart = Cart.objects.create(session_key=new_key, status=Cart.Status.ACTIVE)

    return cart


def get_new_cart_session(request):
    replace_session_key(request, CART_SESSION_COOKIE_LABEL, str(uuid.uuid4()))
