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
    """
    Hamshira faqat o‘zining jadvalidagi ish kuni va ish vaqtida, is_working=True bo‘lsa ruxsat.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False
        
        if getattr(user, 'role', None) not in ['nurse', 'doctor', 'admin']:
            return False

        now = datetime.now()
        day_of_week = now.strftime('%A').lower()  # 'monday', 'tuesday', ...
        try:
            schedule = NurseSchedule.objects.get(user=user, day=day_of_week)
        except NurseSchedule.DoesNotExist:
            return False

        if not schedule.is_working:
            return False

        # Ish vaqti ichida ekanligini tekshirish
        now_time = now.time()
        if schedule.start_time <= now_time <= schedule.end_time:
            return True
        return False