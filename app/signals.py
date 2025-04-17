from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *
from app2.models import *
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


@receiver(post_save, sender=User)
def create_nurse_schedule(sender, instance, created, **kwargs):
    if created and instance.role == 'nurse':
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in days_of_week:
            NurseSchedule.objects.create(
                user=instance,
                day=day,
                start_time="09:00",
                end_time="18:00",
                is_working=True
            )



# NotificationConsumer uchun signal ------------------------------

@receiver(post_save, sender=Cabinet)
def create_cabinet_notification(sender, instance, created, **kwargs):
    if created:
        ClinicNotification.objects.create(
            title="Yangi kabinet qo'shildi",
            message=f"Yangi kabinet: {instance.name} ({instance.branch.name}) qo'shildi.",
            clinic=instance.branch.clinic
        )
    else:
        ClinicNotification.objects.create(
            title="Kabinet ma'lumotlari o'zgartirildi",
            message=f"Kabinet: {instance.name} ({instance.branch.name}) ma'lumotlari o'zgartirildi.",
            clinic=instance.branch.clinic
        )

@receiver(post_save, sender=Customer)
def create_customer_notification(sender, instance, created, **kwargs):
    if created:
        ClinicNotification.objects.create(
            title="Yangi mijoz qo'shildi",
            message=f"Yangi mijoz: {instance.full_name} ({instance.branch.name}) qo'shildi.",
            clinic=instance.branch.clinic
        )
    else:
        ClinicNotification.objects.create(
            title="Mijoz ma'lumotlari o'zgartirildi",
            message=f"Mijoz: {instance.full_name} ({instance.branch.name}) ma'lumotlari o'zgartirildi.",
            clinic=instance.branch.clinic
        )

@receiver(post_save, sender=User)
def create_user_notification(sender, instance, created, **kwargs):
    if created:
        ClinicNotification.objects.create(
            title="Yangi foydalanuvchi qo'shildi",
            message=f"Yangi foydalanuvchi: {instance.get_full_name()} ({instance.clinic.name}) qo'shildi.",
            clinic=instance.clinic
        )
    else:
        ClinicNotification.objects.create(
            title="Foydalanuvchi ma'lumotlari o'zgartirildi",
            message=f"Foydalanuvchi: {instance.get_full_name()} ({instance.clinic.name}) ma'lumotlari o'zgartirildi.",
            clinic=instance.clinic
        )

@receiver(post_save, sender=Meeting)
def create_meeting_notification(sender, instance, created, **kwargs):
    if created:
        ClinicNotification.objects.create(
            title="Yangi uchrashuv qo'shildi",
            message=f"Yangi uchrashuv: {instance.customer.full_name} va {instance.doctor.get_full_name()} ({instance.branch.name}) qo'shildi.",
            clinic=instance.branch.clinic
        )
    else:
        ClinicNotification.objects.create(
            title="Uchrashuv ma'lumotlari o'zgartirildi",
            message=f"Uchrashuv: {instance.customer.full_name} va {instance.doctor.get_full_name()} ({instance.branch.name}) ma'lumotlari o'zgartirildi.",
            clinic=instance.branch.clinic
        )