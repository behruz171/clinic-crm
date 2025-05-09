# utils/exception_handler.py
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from custom_admin.models import ApiIssue
import traceback
from utils.ip_utils import get_location_from_ip

def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    request = context.get("request")
    user = getattr(request, "user", None)
    path = request.path

    try:
        ip_address = get_client_ip(request)
        location_data = get_location_from_ip(ip_address)

        # 401 holatda foydalanuvchi aniqlanmagan bo‘lishi mumkin
        if response is not None and response.status_code == 401:
            ApiIssue.objects.create(
                clinic=None,
                api_name=path,
                issue_description=str(exc),
                status="unauthorized",
                ip_address=ip_address,
                location=(
                    f"{location_data.get('city')}, {location_data.get('region')}, "
                    f"{location_data.get('country')}"
                ) if not location_data.get("error") else "Unknown"
            )
        elif user and user.is_authenticated and hasattr(user, "clinic"):
            ApiIssue.objects.create(
                clinic=user.clinic,
                api_name=path,
                issue_description=str(exc),
                status="error",
                ip_address=ip_address,
                location=(
                    f"{location_data.get('city')}, {location_data.get('region')}, "
                    f"{location_data.get('country')}, {location_data.get('latitude')}, {location_data.get('longitude')}"
                ) if not location_data.get("error") else "Unknown"
            )
    except Exception as e:
        print("API xatoni log qilishda muammo:", e)

    return response