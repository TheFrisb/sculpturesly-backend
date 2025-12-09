from django.urls import path

from .views import EUCountryListView

urlpatterns = [
    path(
        "supported-countries/", EUCountryListView.as_view(), name="eu-country-list-view"
    )
]
