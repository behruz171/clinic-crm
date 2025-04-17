from channels.generic.websocket import AsyncWebsocketConsumer
import json
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Query params orqali token olish
        query_string = parse_qs(self.scope["query_string"].decode())
        token = query_string.get("token", [None])[0]

        if not token:
            await self.close()
            return
        
        # Token orqali userni olish
        user = await self.get_user_from_token(token)
        if user is None:
            await self.close()
            return

        self.user = user
        self.group_name = f"notifications_{self.user.id}"

        # Guruhga qo‘shish
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Guruhdan chiqarish
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_message(self, event):
        # WebSocket orqali xabar yuborish
        await self.send(text_data=json.dumps({
            "title": event["title"],
            "message": event["message"],
            "timestamp": event["timestamp"],
        }))

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            return User.objects.get(id=user_id)
        except Exception as e:
            return None


class ClinicNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.clinic_id = self.scope['url_route']['kwargs']['clinic_id']
        self.group_name = f"clinic_notifications_{self.clinic_id}"

        # Guruhga ulanish
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Guruhdan uzilish
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def notification_message(self, event):
        # Xabarni WebSocket orqali yuborish
        await self.send(text_data=json.dumps({
            "title": event["title"],
            "message": event["message"],
            "timestamp": event["timestamp"],
        }))


class NotificationGlobalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "global_notifications"

        # Guruhga ulanish
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Guruhdan uzilish
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def notification_message(self, event):
        # Xabarni WebSocket orqali yuborish
        await self.send(text_data=json.dumps({
            "title": event["title"],
            "message": event["message"],
            "timestamp": event["timestamp"],
        }))