from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import TimestampedModel
from products.models import ProductVariant


# Create your models here.
class Cart(TimestampedModel):
    class Status(models.TextChoices):
        ABANDONED = "ABANDONED", _("Abandoned")
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    session_key = models.CharField(max_length=255, db_index=True)

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        return f"Cart {self.id} ({self.status}) - {self.session_key[:10]}..."


class CartItem(TimestampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.product_variant.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product_variant.sku}"
