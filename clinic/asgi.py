import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from app.routing import websocket_urlpatterns  # WebSocket marshrutlarini import qilish
from channels.auth import AuthMiddlewareStack
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(  # Foydalanuvchi autentifikatsiyasini qo‘shish
        URLRouter(websocket_urlpatterns)
    ),  # WebSocket'lar uchun marshrut
})