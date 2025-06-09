from rest_framework import permissions
from custom_admin.models import *
from datetime import date, datetime
from app2.models import *

class IsClinicAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'

class IsSameClinicUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.clinic == request.user.clinic 


class HasActiveSubscription(permissions.BasePermission):
    """
    Foydalanuvchi klinikasi uchun faol va amal qilayotgan subscription borligini tekshiradi.
    """

    def has_permission(self, request, view):
        user = request.user
        # Agar user autentifikatsiya qilinmagan bo‘lsa yoki AllowAny bo‘lsa, ruxsat bermaydi
        if not user.is_authenticated:
            return False
        clinic = getattr(user, 'clinic', None)
        if not clinic:
            return False
        today = date.today()
        # Subscription mavjud va faol, sanasi to‘g‘ri bo‘lishi kerak
        return ClinicSubscription.objects.filter(
            clinic=clinic,
            status='active',
            start_date__lte=today,
            end_date__gte=today
        ).exists()


class IsNurseWorkingNow(permissions.BasePermission):
    message = "Sizning ish vaqtingiz tugadi yoki sizga ruxsat yo'q."

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            self.message = "Avval tizimga kiring."
            return False

        # if getattr(user, 'role', None) not in ['nurse', 'doctor', 'admin']:
        #     self.message = "Sizga ushbu amal uchun ruxsat yo'q."
        #     return False

        if getattr(user, 'role', None) == 'director':
            # self.message = "Direktor uchun ushbu amal cheklangan."
            return True

        now = datetime.now()
        day_of_week = now.strftime('%A').lower()
        try:
            schedule = NurseSchedule.objects.get(user=user, day=day_of_week)
        except NurseSchedule.DoesNotExist:
            self.message = "Bugungi kun uchun jadval topilmadi."
            return False

        if not schedule.is_working:
            self.message = "Siz bugun ishlamaysiz."
            return False

        now_time = now.time()
        if not (schedule.start_time <= now_time <= schedule.end_time):
            self.message = "Sizning ish vaqtingiz tugadi."
            return False

        return True