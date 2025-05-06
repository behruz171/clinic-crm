from celery import shared_task
from django.utils.timezone import now
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Task, User, ClinicNotification
from django.utils.timezone import now, localtime
from clinic.celery import app
from celery.schedules import crontab
from datetime import timedelta, datetime, time
from app.models import *
from django.db.models import F, Value, CharField, Count
from django.db.models.functions import Concat
import logging
logger = logging.getLogger(__name__)
# @shared_task
# def send_uncompleted_tasks_notification():
#     """
#     Har kuni 23:59 da director uchun bajarilmagan vazifalar haqida xabar yuborish.
#     """
#     clinics = User.objects.filter(role='director').values_list('clinic', flat=True).distinct()
#     for clinic_id in clinics:
#         director = User.objects.filter(role='director', clinic_id=clinic_id).first()
#         if not director:
#             continue

#         # Ushbu klinikaga tegishli bajarilmagan vazifalarni olish
#         uncompleted_tasks = Task.objects.filter(
#             assignee__clinic_id=clinic_id,
#             status__in=['pending', 'in_progress']
#         )

#         if uncompleted_tasks.exists():
#             message = "Bajarilmagan vazifalar:\n"
#             for task in uncompleted_tasks:
#                 message += f"- {task.title} (Holati: {task.get_status_display()})\n"

#             # ClinicNotification saqlash
#             ClinicNotification.objects.create(
#                 title="Bajarilmagan vazifalar",
#                 message=message,
#                 clinic=director.clinic,
#                 branch=None
#             )

#             # Real-time xabar yuborish
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 f"clinic_notifications_{director.id}",
#                 {
#                     "type": "notification_message",
#                     "title": "Bajarilmagan vazifalar",
#                     "message": message,
#                     "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
#                 }
#             )

@shared_task
def send_daily_meeting_report():
    """
    Har kuni soat 23:59 da bugungi uchrashuvlar hisobotini yaratish va real-time xabar yuborish.
    """
    today = localtime(now()).date()  # Bugungi sana
    meetings = Meeting.objects.filter(date__date=today)  # Bugungi uchrashuvlar

    # Status bo'yicha hisoblash
    cancelled_count = meetings.filter(status='cancelled').count()
    finished_count = meetings.filter(status='finished').count()

    # Hisobot matni
    report_message = (
        f"Bugungi uchrashuvlar hisobot:\n"
        f"- Bekor qilinganlar: {cancelled_count}\n"
        f"- Yakunlanganlar: {finished_count}\n"
    )

    # Klinikaga xabar yuborish
    clinics = meetings.values_list('branch__clinic', flat=True).distinct()
    logger.info(f"Clinics found: {clinics}")
    for clinic_id in clinics:
        # Klinikaga tegishli direktorlarni topish
        directors = User.objects.filter(role='director', clinic_id=clinic_id)
        for director in directors:
            # ClinicNotification saqlash
            try:
                ClinicNotification.objects.create(
                    title="Kunlik uchrashuvlar hisobot",
                    message=report_message,
                    clinic=director.clinic,
                    status='director'
                )
                logger.info(f"Notification saved for clinic_id: {clinic_id} and director_id: {director.id}")
            except Exception as e:
                logger.error(f"Error saving ClinicNotification for clinic_id: {clinic_id} and director_id: {director.id} - {str(e)}")

            # Real-time xabar yuborish
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"clinic_notifications_{director.id}",  # Director ID asosida guruh nomi
                {
                    "type": "notification_message",
                    "title": "Kunlik uchrashuvlar hisobot",
                    "message": report_message,
                    "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

@shared_task
def send_weekly_financial_report():
    """
    Har haftada direktor uchun daromad va xarajat hisobotini yuborish.
    """
    today = localtime(now()).date()
    start_of_week = today - timedelta(days=today.weekday())  # Haftaning bosh sanasi (Dushanba)
    end_of_week = start_of_week + timedelta(days=6)  # Haftaning oxiri (Yakshanba)

    # Haftalik boshlanishi va tugashini datetime formatida olish
    start_of_week_dt = datetime.combine(start_of_week, time.min)
    end_of_week_dt = datetime.combine(end_of_week, time.max)

    # Daromad (income)
    income = Meeting.objects.filter(
        created_at__range=(start_of_week_dt, end_of_week_dt)
    ).aggregate(
        total_income=models.Sum('payment_amount')
    )['total_income'] or 0

    # Xarajat (expenses)
    expenses = CashWithdrawal.objects.filter(
        created_at__range=(start_of_week_dt, end_of_week_dt)
    ).aggregate(
        total_expenses=models.Sum('amount')
    )['total_expenses'] or 0

    # Hisobot matni
    report_message = (
        f"📊 *Haftalik moliyaviy hisobot:*\n"
        f"📅 {start_of_week.strftime('%Y-%m-%d')} - {end_of_week.strftime('%Y-%m-%d')}\n\n"
        f"💰 Daromad: {income:,.2f} so'm\n"
        f"💸 Xarajat: {expenses:,.2f} so'm\n"
    )

    # Direktorlarga yuborish
    directors = User.objects.filter(role='director')
    for director in directors:
        if director.clinic:  # Faqat klinikasi bor direktorlar
            ClinicNotification.objects.create(
                title="Haftalik moliyaviy hisobot",
                message=report_message,
                clinic=director.clinic,
                status='director'
            )
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"clinic_notifications_{director.id}",
                {
                    "type": "notification_message",
                    "title": "Haftalik moliyaviy hisobot",
                    "message": report_message,
                    "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )





@shared_task
def send_monthly_financial_report():
    """
    Har oyda direktor uchun daromad va xarajat hisobotini yuborish.
    """
    today = localtime(now()).date()
    start_of_month = today.replace(day=1)  # Oyning bosh sanasi
    end_of_month = (start_of_month + timedelta(days=31)).replace(day=1) - timedelta(days=1)  # Oyning oxirgi sanasi

    # Daromadlarni hisoblash
    income = Meeting.objects.filter(created_at__range=(start_of_month, end_of_month)).aggregate(
        total_income=models.Sum('payment_amount')
    )['total_income'] or 0

    # Xarajatlarni hisoblash
    expenses = CashWithdrawal.objects.filter(
        created_at__range=(start_of_month, end_of_month)
    ).aggregate(total_expenses=models.Sum('amount'))['total_expenses'] or 0

    # Hisobot matni
    report_message = (
        f"Oylik moliyaviy hisobot:\n"
        f"- Daromad: {income} so'm\n"
        f"- Xarajat: {expenses} so'm\n"
    )

    # Klinikaga xabar yuborish
    directors = User.objects.filter(role='director')
    for director in directors:
        # ClinicNotification orqali xabar yuborish
        ClinicNotification.objects.create(
            title="Oylik moliyaviy hisobot",
            message=report_message,
            clinic=director.clinic,
            status='director'
        )

        # WebSocket orqali real vaqt xabari yuborish
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{director.id}",
            {
                "type": "notification_message",
                "title": "Oylik moliyaviy hisobot",
                "message": report_message,
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )






@shared_task
def send_top_doctors_report(period='weekly'):
    """
    Har hafta yoki oyda eng ko'p bemor qabul qilgan shifokorlar haqida hisobot yuborish.
    """
    today = localtime(now()).date()

    # Haftalik yoki oylik davrni belgilash
    if period == 'weekly':
        start_date = today - timedelta(days=today.weekday())  # Hafta boshidan
        end_date = start_date + timedelta(days=6)  # Hafta oxirigacha
        title = "Haftalik eng ko'p bemor qabul qilgan shifokorlar"
    elif period == 'monthly':
        start_date = today.replace(day=1)  # Oy boshidan
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)  # Oy oxirigacha
        title = "Oylik eng ko'p bemor qabul qilgan shifokorlar"
    else:
        return  # Periodni noto‘g‘ri kiritsangiz, hech narsa qilmaydi

    # Vaqtni aniq belgilash
    start_datetime = localtime(now()).replace(year=start_date.year, month=start_date.month, day=start_date.day, hour=0, minute=0, second=0)
    end_datetime = localtime(now()).replace(year=end_date.year, month=end_date.month, day=end_date.day, hour=23, minute=59, second=59)

    # Eng ko'p bemor qabul qilgan shifokorlarni topish
    top_doctors = (
        Meeting.objects.filter(created_at__range=(start_datetime, end_datetime))  # Davr bo'yicha filtr
        .annotate(
            doctor_full_name=Concat(
                F('doctor__first_name'),
                Value(' '),
                F('doctor__last_name'),
                output_field=CharField()
            )
        )
        .values('doctor__id', 'doctor_full_name')  # Shifokorning ID va to'liq ismi
        .annotate(total_patients=Count('id'))  # Har bir shifokorga qabul qilingan bemorlar soni
        .order_by('-total_patients')[:5]  # Eng ko'p bemor qabul qilgan 5 shifokorni olish
    )

    # Hisobot matnini tayyorlash
    report_message = f"{title}:\n"
    for doctor in top_doctors:
        report_message += f"- {doctor['doctor_full_name']}: {doctor['total_patients']} bemor\n"

    # Klinikadagi barcha direktorlar uchun xabar yuborish
    directors = User.objects.filter(role='director')
    for director in directors:
        ClinicNotification.objects.create(
            title=title,
            message=report_message,
            clinic=director.clinic,
            status='director'
        )

        # WebSocket orqali real vaqt xabari yuborish
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{director.id}",
            {
                "type": "notification_message",
                "title": title,
                "message": report_message,
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )


@shared_task
def send_new_patients_report(period='weekly'):
    """
    Har hafta yoki oyda yangi qo'shilgan bemorlar haqida hisobot yuborish.
    """
    today = localtime(now()).date()
    if period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        title = "Haftalik yangi qo'shilgan bemorlar"
    elif period == 'monthly':
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        title = "Oylik yangi qo'shilgan bemorlar"

    # Yangi bemorlarni aniqlash
    new_patients = Customer.objects.filter(created_at__date__range=(start_date, end_date))

    # Hisobot matni
    report_message = f"{title}:\n"
    for patient in new_patients:
        report_message += f"- {patient.full_name} ({patient.phone_number})\n"

    # Klinikaga xabar yuborish
    directors = User.objects.filter(role='director')
    for director in directors:
        ClinicNotification.objects.create(
            title=title,
            message=report_message,
            clinic=director.clinic,
            status='admin'
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"clinic_notifications_{director.id}",
            {
                "type": "notification_message",
                "title": title,
                "message": report_message,
                "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )