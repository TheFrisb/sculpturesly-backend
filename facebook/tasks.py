# from celery import shared_task
import logging

from facebook.schemas.meta_conversion_schemas import MetaCustomData, MetaUserData
from facebook.services.meta_conversion_service import MetaConversionService

logger = logging.getLogger(__name__)


# @shared_task
def send_meta_event_task(event_name, event_id, user_data_dict, custom_data_dict, url):
    service = MetaConversionService()
    try:
        user_data = MetaUserData(**user_data_dict)
        custom_data = MetaCustomData(**custom_data_dict)
        service.send_event(event_name, event_id, user_data, custom_data, url)
    except Exception as e:
        logger.exception(f"An error occurred when sending a Meta Pixel Event: {e}")
