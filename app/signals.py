from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json

@receiver(post_save, sender=User)
def send_welcome_and_password_email(sender, instance, created, **kwargs):
    # Email yuborish funksiyasini olib tashlaymiz
    pass

# @receiver(post_save, sender=Notification)
# def send_notification_email(sender, instance, created, **kwargs):
#     if created:  # Faqat yangi notification yaratilganda
#         instance.send_notification()

# @receiver(post_save, sender=ClinicNotification)
# def send_clinic_notification_email(sender, instance, created, **kwargs):
#     if created:  # Faqat yangi clinic notification yaratilganda
#         instance.send_notification()

@receiver(post_save, sender=UserNotification)
def send_realtime_notification(sender, instance, created, **kwargs):
    """Yangi bildirishnoma qo‘shilganda WebSocket orqali yuborish"""
    if created:  # Faqat yangi qo‘shilgan notification
        channel_layer = get_channel_layer()
        user_id = instance.recipient.id  # Qabul qiluvchi foydalanuvchi ID si
        group_name = f"notifications_{user_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification_message",  # `NotificationConsumer` da shu nom bo‘lishi kerak
                "title": instance.title,
                "message": instance.message,
                "timestamp": instance.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            }
        )