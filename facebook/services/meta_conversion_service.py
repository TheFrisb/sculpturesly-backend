import hashlib
import logging
import time
from typing import Optional

from django.conf import settings
from facebook_business.adobjects.serverside.action_source import ActionSource
from facebook_business.adobjects.serverside.custom_data import CustomData
from facebook_business.adobjects.serverside.event import Event
from facebook_business.adobjects.serverside.event_request import EventRequest
from facebook_business.adobjects.serverside.user_data import UserData
from facebook_business.api import FacebookAdsApi

from facebook.schemas.meta_conversion_schemas import MetaCustomData, MetaUserData

logger = logging.getLogger(__name__)


class MetaConversionService:
    def __init__(self):
        self.app_id = settings.META_APP_ID
        self.app_secret = settings.META_APP_SECRET
        self.access_token = settings.META_SYSTEM_USER_TOKEN
        self.pixel_id = settings.META_DATASET_ID
        self.test_event_code = settings.META_APP_SECRET

        FacebookAdsApi.init(
            app_id=self.app_id,
            app_secret=self.app_secret,
            access_token=self.access_token,
        )

    def _hash_pii(self, data: str) -> Optional[str]:  # noqa
        """SHA256 hashing required by Meta."""
        if not data:
            return None
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _map_user_data(self, data: MetaUserData) -> UserData:
        """Maps Pydantic model to Meta SDK UserData with hashing."""
        return UserData(
            emails=[self._hash_pii(data.email)] if data.email else None,
            phones=[self._hash_pii(data.phone)] if data.phone else None,
            first_names=[self._hash_pii(data.first_name)] if data.first_name else None,
            last_names=[self._hash_pii(data.last_name)] if data.last_name else None,
            cities=[self._hash_pii(data.city)] if data.city else None,
            states=[self._hash_pii(data.state)] if data.state else None,
            zip_codes=[self._hash_pii(data.zip_code)] if data.zip_code else None,
            country_codes=[self._hash_pii(data.country)] if data.country else None,
            external_ids=(
                [self._hash_pii(data.external_id)] if data.external_id else None
            ),
            client_ip_address=data.client_ip_address,
            client_user_agent=data.client_user_agent,
            fbp=data.fbp,
            fbc=data.fbc,
        )

    def _map_custom_data(self, data: MetaCustomData) -> CustomData | None:  # noqa
        """Maps Pydantic model to Meta SDK CustomData."""
        if not data:
            return None

        return CustomData(
            currency=data.currency,
            value=data.value,
            content_ids=data.content_ids,
            content_type=data.content_type,
            content_name=data.content_name,
            num_items=data.num_items,
            order_id=data.order_id,
            status=data.status,
        )

    def send_event(
        self,
        event_name: str,
        event_id: str,
        user_data: MetaUserData,
        custom_data: Optional[MetaCustomData] = None,
        event_source_url: str = None,
    ):
        """
        Sends an event to the Meta Conversions API.
        """

        try:
            fb_user_data = self._map_user_data(user_data)
            fb_custom_data = self._map_custom_data(custom_data) if custom_data else None

            event = Event(
                event_name=event_name,
                event_time=int(time.time()),
                user_data=fb_user_data,
                custom_data=fb_custom_data,
                event_source_url=event_source_url,
                action_source=ActionSource.WEBSITE,
                event_id=str(event_id),
            )

            event_request = EventRequest(
                events=[event],
                pixel_id=self.pixel_id,
                test_event_code=self.test_event_code if self.test_event_code else None,
            )

            response = event_request.execute()
            logger.info(f"Meta CAPI Success [{event_name}]: {response}")
            return response

        except Exception as e:
            logger.error(f"Meta CAPI Error [{event_name}]: {e}", exc_info=True)
            return None
