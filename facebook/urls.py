from django.urls import path

from .views import (
    AddToCartView,
    InitiateCheckoutView,
    MetaCatalogFeedView,
    PurchaseView,
    ViewContentView,
)

app_name = "facebook"

urlpatterns = [
    path("conversions/view-content/", ViewContentView.as_view(), name="view_content"),
    path("conversions/add-to-cart/", AddToCartView.as_view(), name="add_to_cart"),
    path(
        "conversions/initiate-checkout/",
        InitiateCheckoutView.as_view(),
        name="initiate_checkout",
    ),
    path("conversions/purchase/", PurchaseView.as_view(), name="purchase"),
    path("catalogue/feed/", MetaCatalogFeedView.as_view(), name="meta_catalogue_feed"),
]
