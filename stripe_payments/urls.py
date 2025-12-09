from django.urls import path

from .views import stripe_webhook

urlpatterns = [path("webhooks/", stripe_webhook)]
