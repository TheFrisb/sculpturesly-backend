import logging
import uuid

logger = logging.getLogger(__name__)


def get_unique_slug(model_class, base_slug, instance=None, counter=1):
    """
    Generate a unique slug, appending a counter if necessary.
    """
    slug = base_slug if counter == 1 else f"{base_slug}-{counter}"
    queryset = model_class.objects.filter(slug=slug)
    if instance:
        queryset = queryset.exclude(pk=instance.pk)
    if not queryset.exists():
        return slug
    return get_unique_slug(model_class, base_slug, instance, counter + 1)


def get_session_key(request, session_key_label, auto_create=True):
    session_key = request.session.get(session_key_label)

    if not session_key and auto_create:
        logger.debug(
            f"Request has no session key with label: {session_key_label}, creating one."
        )

        session_key = str(uuid.uuid4())
        request.session[session_key_label] = session_key
        request.session.modified = True

    logger.debug(f"[Session]: Returned: {session_key} for label: {session_key_label}")

    return session_key


def replace_session_key(request, session_key_label, new_key):
    request.session[session_key_label] = new_key
    request.session.modified = True

    logger.debug(f"[Session]: Set key: {session_key_label} to: {new_key}")
