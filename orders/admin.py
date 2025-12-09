# Register your models here.
from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderAddress, OrderItem


class OrderItemInline(admin.TabularInline):
    """
    Allows editing items directly within the Order page.
    Using TabularInline saves vertical space.
    """

    model = OrderItem
    extra = 0  # Don't show empty extra rows

    # Use raw_id_fields for product_variant so the page doesn't crash
    # trying to load a dropdown of thousands of products.
    raw_id_fields = ["product_variant"]

    fields = [
        "product_variant",
        "product_sku",
        "product_name",
        "quantity",
        "unit_price",
        "total_price",
    ]

    # Make calculated fields readonly to ensure data integrity
    readonly_fields = ["total_price"]

    # If you want to strictly preserve snapshot data, make these readonly too:
    # readonly_fields = ["product_sku", "product_name", "total_price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "email",
        "status_badge",  # Custom color-coded status
        "total_amount",
        "is_paid_icon",  # Custom boolean icon
        "created_at",
    ]

    list_filter = [
        "status",
        "is_paid",
        "created_at",
        "updated_at",
    ]

    search_fields = [
        "order_number",
        "email",
        "id",
        "stripe_payment_intent_id",
        "shipping_address__first_name",
        "shipping_address__last_name",
        "shipping_address__email",
    ]

    # Readonly fields to prevent accidental edits to critical identifiers
    readonly_fields = [
        "id",
        "order_number",
        "created_at",
        "updated_at",
        "stripe_payment_intent_id",
    ]

    # Grouping fields makes the UI much cleaner
    fieldsets = (
        (
            "Order Identification",
            {"fields": ("id", "order_number", "status", "created_at")},
        ),
        (
            "Customer Details",
            {"fields": ("email", "shipping_address", "billing_address")},
        ),
        (
            "Financials",
            {"fields": ("total_amount", "is_paid", "stripe_payment_intent_id")},
        ),
    )

    inlines = [OrderItemInline]

    # Optimization: Loading an order list with addresses triggers N+1 queries.
    # select_related fixes this by fetching addresses in the initial query.
    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("shipping_address", "billing_address")
        )

    # --- Custom Visuals ---

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        """
        Color-codes the status for quick visual scanning.
        """
        colors = {
            "PENDING": "orange",
            "PAID": "blue",
            "PROCESSING": "info",
            "SHIPPED": "purple",
            "DELIVERED": "green",
            "CANCELLED": "red",
            "REFUNDED": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Paid", ordering="is_paid", boolean=True)
    def is_paid_icon(self, obj):
        return obj.is_paid

    # --- Custom Actions ---

    @admin.action(description="Mark selected orders as PAID")
    def make_paid(self, request, queryset):
        updated = queryset.update(status=Order.Status.PAID, is_paid=True)
        self.message_user(request, f"{updated} orders marked as PAID.")

    @admin.action(description="Mark selected orders as SHIPPED")
    def make_shipped(self, request, queryset):
        updated = queryset.update(status=Order.Status.SHIPPED)
        self.message_user(request, f"{updated} orders marked as SHIPPED.")

    @admin.action(description="Mark selected orders as DELIVERED")
    def make_delivered(self, request, queryset):
        updated = queryset.update(status=Order.Status.DELIVERED)
        self.message_user(request, f"{updated} orders marked as DELIVERED.")

    actions = [make_paid, make_shipped, make_delivered]


@admin.register(OrderAddress)
class OrderAddressAdmin(admin.ModelAdmin):
    """
    Usually accessed via the Order inline, but useful to have separate
    if you need to search specifically for an address across all orders.
    """

    list_display = ["full_name", "email", "city", "country", "created_at"]

    search_fields = ["first_name", "last_name", "email", "address_line_1", "zip_code"]

    list_filter = ["country", "created_at"]

    @admin.display(description="Full Name")
    def full_name(self, obj):
        return f
