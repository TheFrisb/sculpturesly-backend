# stripe_payments/views.py

import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from stripe_payments.services.stripe_webhook_service import StripeWebhookService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Endpoint to receive updates from Stripe.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("Stripe Webhook: Invalid Payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe Webhook: Invalid Signature")
        return HttpResponse(status=400)

    try:
        service = StripeWebhookService()
        service.process_event(event, request)

        return HttpResponse(status=200)

    except Exception as e:
        logger.error(f"Webhook Processing Error: {str(e)}", exc_info=True)
        return HttpResponse(status=500)
