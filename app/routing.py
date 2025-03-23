from django.urls import re_path
from .consumers import NotificationConsumer  # Consumer classini import qilish

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", NotificationConsumer.as_asgi()),  # WebSocket URL
]