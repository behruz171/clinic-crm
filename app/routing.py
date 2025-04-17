from django.urls import re_path
from .consumers import *  # Consumer classini import qilish

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),  # WebSocket URL
    re_path(r"ws/notificationsglobal/$", NotificationGlobalConsumer.as_asgi()),
    re_path(r'ws/clinic-notifications/(?P<clinic_id>\d+)/$', ClinicNotificationConsumer.as_asgi()),
]