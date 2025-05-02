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
    if not instance.clinic:
        return  # Klinikaga bog'lanmagan foydalanuvchilar uchun xabar yubormaslik
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


@receiver(post_save, sender=Task)
def send_task_notification_to_doctor(sender, instance, created, **kwargs):
    """
    Task yaratilganda yoki yangilanganda doctor uchun xabar yuborish.
    """
    if instance.assignee.role == 'doctor':  # Faqat doctor uchun
        # Real-time xabar yuborish
        message = f"Sizga yangi vazifa berildi: {instance.title}\n{instance.description}\n{instance.created_by.username} tomonidan"

        ClinicNotification.objects.create(
            title="Yangi vazifa",
            message=message,
            clinic=instance.assignee.clinic,
            branch=instance.assignee.branch
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{instance.assignee.id}",
            {
                "type": "notification_message",
                "title": "Yangi vazifa",
                "message": message,
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

@receiver(post_save, sender=Meeting)
def send_meeting_update_notification_to_doctor(sender, instance, created, **kwargs):
    """
    Meeting o'zgarganda doctor uchun xabar yuborish.
    """
    print(f"Signal ishladi: Meeting ID {instance.id}, Doctor: {instance.doctor}")

    if instance.doctor and instance.doctor.role == 'doctor':  # Faqat doctor uchun
        ClinicNotification.objects.create(
            title="Uchrashuv yangilandi",
            message=f"Sizning uchrashuvingiz yangilandi: {instance.customer.full_name} bilan",
            clinic=instance.branch.clinic,
            branch=instance.branch
        )
        # Real-time xabar yuborish
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{instance.doctor.id}",
            {
                "type": "notification_message",
                "title": "Uchrashuv yangilandi",
                "message": f"Sizning uchrashuvingiz yangilandi: {instance.customer.full_name} bilan",
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )


@receiver(post_save, sender=Task)
def send_task_notification_to_creator(sender, instance, created, **kwargs):
    """
    Task yaratilganda yoki yangilanganda faqat vazifani yaratgan foydalanuvchiga xabar yuborish.
    """
    message = None  # Default qiymat
    if created:
        message = f"Yangi vazifa yaratildi: {instance.title}\nMuhimligi: {instance.priority}\nBoshlanish vaqti: {instance.start_time}"
    else:
        message = f"Vazifa yangilandi: {instance.title}\nMuhimligi: {instance.priority}\nBoshlanish vaqti: {instance.start_time}"

    # Vazifani yaratgan foydalanuvchiga xabar yuborish
    creator = instance.assignee  # Vazifani yaratgan foydalanuvchi
    print(f"send_task_notification_to_creator signal ishladi {creator.id}")
    if creator:

        ClinicNotification.objects.create(
            title="Vazifa haqida xabar",
            message=message,
            clinic=instance.assignee.clinic,
            branch=instance.assignee.branch
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{creator.id}",  # Guruh nomi yaratgan foydalanuvchi ID'si bilan
            {
                "type": "notification_message",
                "title": "Vazifa haqida xabar",
                "message": message,
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )


@receiver(post_save, sender=Customer)
def send_customer_notification(sender, instance, created, **kwargs):
    """
    Bemor yaratilganda faqat o'sha bemor yaratilgan branchga bog'langan admin foydalanuvchilarga xabar yuborish.
    """
    if created:
        message = f"Yangi bemor qo'shildi: {instance.full_name}\nTelefon: {instance.phone_number}"

        ClinicNotification.objects.create(
            title="Yangi bemor",
            message=message,
            clinic=instance.branch.clinic,
            branch=instance.branch
        )
        # Branchga bog'langan admin foydalanuvchilarni olish
        admins = User.objects.filter(role='admin', branch=instance.branch)
        channel_layer = get_channel_layer()
        for admin in admins:
            async_to_sync(channel_layer.group_send)(
                f"clinic_notifications_{admin.id}",
                {
                    "type": "notification_message",
                    "title": "Yangi bemor",
                    "message": message,
                    "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )


@receiver(post_save, sender=Cabinet)
def send_cabinet_notification(sender, instance, created, **kwargs):
    """
    Kabinet yaratilganda yoki tamir holati o'zgarganda faqat o'sha branchga bog'langan admin foydalanuvchilarga xabar yuborish.
    """
    if created:
        message = f"Yangi kabinet qo'shildi: {instance.name}\nFilial: {instance.branch.name}"
    elif instance.status == 'repair':
        message = f"Kabinet tamirga kirdi: {instance.name}\nFilial: {instance.branch.name}"
    elif instance.status == 'available':
        message = f"Kabinet tamirdan chiqdi: {instance.name}\nFilial: {instance.branch.name}"

    ClinicNotification.objects.create(
        title="Kabinet haqida xabar",
        message=message,
        clinic=instance.branch.clinic,
        branch=instance.branch
    )
    # Branchga bog'langan admin foydalanuvchilarni olish
    admins = User.objects.filter(role='admin', branch=instance.branch)
    channel_layer = get_channel_layer()
    for admin in admins:
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{admin.id}",
            {
                "type": "notification_message",
                "title": "Kabinet haqida xabar",
                "message": message,
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

@receiver(post_save, sender=User)
def send_employee_notification_to_director(sender, instance, created, **kwargs):
    if not instance or not instance.clinic:
        return  # clinic yo'q bo'lsa signal ishlamasin
    """
    Xodimlar yaratilganda yoki holati o'zgarganda faqat o'sha branchga bog'langan direktor foydalanuvchilarga xabar yuborish.
    """
    if created:
        message = f"Yangi xodim qo'shildi: {instance.get_full_name()}\nLavozim: {instance.role}"
    else:
        message = f"Xodim ma'lumotlari o'zgartirildi: {instance.get_full_name()}\nHolati: {instance.status}"

    ClinicNotification.objects.create(
        title="Xodim haqida xabar",
        message=message,
        clinic=instance.branch.clinic,
        branch=instance.branch
    )

    # Branchga bog'langan direktor foydalanuvchilarni olish
    directors = User.objects.filter(role='director', branch=instance.branch)
    channel_layer = get_channel_layer()
    for director in directors:
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{director.id}",
            {
                "type": "notification_message",
                "title": "Xodim haqida xabar",
                "message": message,
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

@receiver(post_save, sender=Task)
def send_task_status_notification(sender, instance, created, **kwargs):

    """
    Vazifa bajarilmagan yoki kechikkan bo'lsa faqat vazifani yaratgan foydalanuvchiga xabar yuborish.
    """
    print("send_task_status_notification signal ishladi")
    message = None  # Default qiymat

    if instance.status == 'overdue':
        message = f"Vazifa kechikdi: {instance.title}\nBajarilishi kerak edi: {instance.end_date}"
    elif instance.status == 'in_progress':
        message = f"Vazifa bajarilmoqda: {instance.title}\nBajarilishi kerak: {instance.end_date}"

    # Faqat message aniqlangan bo'lsa, xabar yuborish
    if message:
        creator = instance.assignee  # Vazifani yaratgan foydalanuvchi
        
        if creator:

            ClinicNotification.objects.create(
                title="Vazifa holati",
                message=message,
                clinic=creator.clinic,
                branch=creator.branch
            )

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"clinic_notifications_{creator.id}",
                {
                    "type": "notification_message",
                    "title": "Vazifa holati",
                    "message": message,
                    "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )