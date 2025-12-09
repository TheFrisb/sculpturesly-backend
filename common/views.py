from django_countries import countries
from rest_framework.response import Response
from rest_framework.views import APIView

from common.constants import EU_COUNTRY_CODES


class EUCountryListView(APIView):
    def get(self, request):
        data = [
            {
                "code": code,
                "name": countries.name(code),
                "flag": request.build_absolute_uri(f"flags/{code.lower()}.gif"),
            }
            for code in EU_COUNTRY_CODES
        ]

        return Response(data)
