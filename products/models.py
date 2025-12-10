import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from common.models import TimestampedModel, SeoModel
from common.utils import get_unique_slug


def get_product_slug(instance):
    if hasattr(instance, "slug"):
        return instance.slug
    if hasattr(instance, "product"):
        return instance.product.slug
    if hasattr(instance, "variant"):
        return instance.variant.product.slug
    return "unassigned"


def product_thumbnail_upload_to(instance, filename):
    ext = filename.split(".")[-1].lower()
    slug = get_product_slug(instance)
    return f"products/{slug}/thumbnail/{uuid.uuid4()}.{ext}"


def variant_image_upload_to(instance, filename):
    """Stores specific variant images (e.g. Red Shirt)."""
    ext = filename.split(".")[-1].lower()
    slug = get_product_slug(instance)
    return f"products/{slug}/variants/{uuid.uuid4()}.{ext}"


def product_gallery_upload_to(instance, filename):
    """Stores general gallery images."""
    ext = filename.split(".")[-1].lower()
    slug = get_product_slug(instance)
    return f"products/{slug}/gallery/{uuid.uuid4()}.{ext}"


class Attribute(models.Model):

    name = models.CharField(max_length=255, verbose_name=_("Attribute Name"))
    slug = models.SlugField(max_length=255, unique=True)

    choices = models.JSONField(
        default=list, blank=True, verbose_name=_("Valid Choices")
    )

    def __str__(self):
        return self.name


class ProductType(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Type Name"))
    allowed_attributes = models.ManyToManyField(
        Attribute, related_name="product_types", verbose_name=_("Allowed Attributes")
    )

    def __str__(self):
        return self.name


class Category(MPTTModel, SeoModel, TimestampedModel):
    title = models.CharField(max_length=255, verbose_name=_("Category Name"))
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent Category"),
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["title"]

    class MPTTMeta:
        order_insertion_by = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = get_unique_slug(self.__class__, slugify(self.title), self)
        super().save(*args, **kwargs)


class Collection(SeoModel, TimestampedModel):
    title = models.CharField(max_length=255, verbose_name=_("Collection Name"))
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    products = models.ManyToManyField("Product", related_name="collections", blank=True)
    image = models.ImageField(upload_to="collections/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Collection")
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = get_unique_slug(self.__class__, slugify(self.title), self)
        super().save(*args, **kwargs)


class Product(SeoModel, TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        ARCHIVED = "ARCHIVED", _("Archived")
        PUBLISHED = "PUBLISHED", _("Published")

    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("Product Type"),
    )

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)

    categories = models.ManyToManyField(
        Category, related_name="products", blank=True, verbose_name=_("Categories")
    )

    thumbnail = models.ImageField(upload_to=product_thumbnail_upload_to)
    specifications = models.JSONField(default=dict, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default="0.00")

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = get_unique_slug(self.__class__, slugify(self.title), self)
        super().save(*args, **kwargs)

    def get_frontend_url(self, slug=None):
        base_frontend_url = settings.FRONTEND_BASE_URL

        return f"{base_frontend_url}/products/{self.slug}"

    def __str__(self):
        return self.title


class ProductVariant(TimestampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=255, unique=True, db_index=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stock_quantity = models.PositiveIntegerField(default=0)

    image = models.ImageField(upload_to=variant_image_upload_to)

    attributes = models.JSONField(default=dict)

    class Meta:
        ordering = ["sku"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "attributes"], name="unique_variant_attributes"
            )
        ]
        indexes = [
            GinIndex(fields=["attributes"], name="variant_attributes_gin"),
            models.Index(fields=["price"]),
        ]

    def __str__(self):
        return f"{self.product.title} ({self.sku})"

    def clean(self):
        super().clean()

        if not hasattr(self, "product") or not self.product.product_type:
            return

        # 1. Fetch Rules
        allowed_attrs_qs = self.product.product_type.allowed_attributes.all()
        allowed_map = {attr.slug: attr.choices for attr in allowed_attrs_qs}

        submitted_keys = set(self.attributes.keys())
        allowed_keys = set(allowed_map.keys())

        # 2. Check for Forbidden Attributes (Security)
        invalid_keys = submitted_keys - allowed_keys
        if invalid_keys:
            raise ValidationError(
                f"Attributes {invalid_keys} are not allowed for this product type."
            )

        # 3. Check for Missing Required Attributes (Integrity)
        missing_keys = allowed_keys - submitted_keys
        if missing_keys:
            raise ValidationError(f"Missing required attributes: {missing_keys}")

        # 4. Check Values against Choices (Business Logic)
        for key, value in self.attributes.items():
            valid_choices = allowed_map.get(key)
            if valid_choices and value not in valid_choices:
                raise ValidationError(
                    f"Value '{value}' is not valid for '{key}'. Allowed: {valid_choices}"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProductGalleryImage(TimestampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="gallery_images"
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to=product_gallery_upload_to)
    alt_text = models.CharField(max_length=255, blank=True)
    is_feature = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Gallery Image")
        verbose_name_plural = _("Gallery Images")
