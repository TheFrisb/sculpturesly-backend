import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from carts.models import Cart
from orders.models import Order

logger = logging.getLogger(__name__)


class StripeWebhookService:
    def process_event(self, event, request):
        """
        Dispatcher that routes the Stripe Event to the specific handler.
        """
        event_type = event["type"]

        if event_type == "checkout.session.completed":
            return self._handle_checkout_session_completed(
                event["data"]["object"], request
            )

        logger.info(f"Unhandled Stripe event type: {event_type}")
        return None

    def _handle_checkout_session_completed(self, session, request):
        """
        Handles successful payment.
        """
        metadata = session.get("metadata", {})

        order_id = metadata.get("order_id")
        cart_session_key = metadata.get("cart_session_key")
        stripe_payment_intent = session.get("payment_intent")

        logger.info(
            f"Processing checkout success for Order ID: {order_id} and Cart Session Key: {cart_session_key}"
        )

        if not order_id:
            logger.error("Stripe Session missing client_reference_id")
            return

        with transaction.atomic():
            self._save_paid_order(order_id, payment_intent_id=stripe_payment_intent)

        self._save_paid_cart(cart_session_key, request)

    def _save_paid_order(self, order_id, payment_intent_id):
        try:
            order = Order.objects.select_for_update().get(id=order_id)

            if order.is_paid:
                logger.info(
                    f"Order {order.order_number} is already marked as paid. Skipping."
                )
                return

            order.is_paid = True
            order.status = Order.Status.PAID
            order.stripe_payment_intent_id = payment_intent_id
            order.save()

            logger.info(f" Order {order.id} marked as PAID via Webhook.")

        except ObjectDoesNotExist:
            logger.error(f"Order {order_id} not found during webhook processing.")
        except Exception as e:
            logger.error(f"Error updating Order {order_id}: {str(e)}", exc_info=True)
            raise e

    def _save_paid_cart(self, cart_session_key, request):
        try:
            cart = Cart.objects.get(session_key=cart_session_key)
            cart.status = Cart.Status.COMPLETED
            cart.save()

            logger.info(f"Cart: {cart.id} marked as COMPLETED via Webhook.")
        except ObjectDoesNotExist:
            logger.error(
                f"Cart with session key: {cart_session_key} not found during webhook processing."
            )
        except Exception as e:
            logger.error(
                f"Error updating Cart with session key: {cart_session_key}: {str(e)}",
                exc_info=True,
            )
            raise e
