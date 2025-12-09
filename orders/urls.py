from django.urls import path

from .views import CheckoutView, OrderRetrieveView

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("<str:pk>/", OrderRetrieveView.as_view(), name="retrieve-order"),
]
