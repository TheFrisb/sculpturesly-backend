from django.conf import settings
from django.db import models


# Create your models here.
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrderableModel(models.Model):
    sort_order = models.IntegerField(default=0, blank=False, null=True)

    class Meta:
        abstract = True


class SeoModel(models.Model):
    seo_metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="SEO Overrides",
        help_text="Override defaults. Keys: title, description, robots, etc.",
    )

    class Meta:
        abstract = True

    def get_frontend_url(self, slug=None):
        frontend_base_url = settings.FRONTEND_BASE_URL.rstrip()

        if slug is not None:
            return frontend_base_url + slug

        if hasattr(self, "slug"):
            return frontend_base_url + getattr(self, "slug")

        return None

    def get_seo_data(self):
        site_name = settings.BRAND_NAME
        backend_base_url = settings.BACKEND_BASE_URL.rstrip()

        obj_title = getattr(self, "title", "") or getattr(self, "name", "")
        obj_description = getattr(self, "description", "")
        img_field = getattr(self, "thumbnail", None) or getattr(self, "image", None)
        img_url = ""
        if img_field and hasattr(img_field, "url"):
            img_url = f"{backend_base_url}{img_field.url}"

        is_product = hasattr(self, "base_price")
        og_type = "product" if is_product else "website"

        data = {
            "title": obj_title,
            "description": obj_description,
            "canonical": self.get_frontend_url(),
            # Open Graph
            "ogTitle": obj_title,
            "ogDescription": obj_description,
            "ogImage": img_url,
            "ogUrl": self.get_frontend_url(),
            "ogType": og_type,
            "ogSiteName": site_name,
            # Twitter
            "twitterCard": "summary_large_image",
            "twitterTitle": obj_title,
            "twitterDescription": obj_description,
            "twitterImage": img_url,
            # Robots
            "robots": "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1",
        }

        # ---------------------------------------
        if is_product and getattr(self, "base_price", None) is not None:
            data["price"] = {
                "amount": str(getattr(self, "base_price")),
                "currency": "EUR",
            }

        overrides = self.seo_metadata or {}

        data.update(overrides)

        return data
