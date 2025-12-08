from facebook.schemas.meta_conversion_schemas import MetaUserData


def build_user_context(request) -> MetaUserData:
    """Helper to extract standard request data into our Pydantic Model"""
    return MetaUserData(
        client_ip_address=request.META.get("REMOTE_ADDR"),
        client_user_agent=request.META.get("HTTP_USER_AGENT"),
        fbp=request.COOKIES.get("_fbp"),
        fbc=request.COOKIES.get("_fbc"),
        email=request.user.email if request.user.is_authenticated else None,
        external_id=str(request.user.id) if request.user.is_authenticated else None,
    )
