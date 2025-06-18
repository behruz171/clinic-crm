from rest_framework import permissions
from custom_admin.models import *
from datetime import date, datetime
from django.utils import timezone
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


class CanCreateUserByPlanLimit(permissions.BasePermission):
    message = "Tarif bo‘yicha foydalanuvchi limiti tugagan."

    def has_permission(self, request, view):
        if request.method != 'POST':
            return True
        
        clinic = getattr(request.user, 'clinic', None)
        if not clinic:
            return False

        today = timezone.now().date()
        active_sub = (
            ClinicSubscription.objects
            .filter(clinic=clinic, start_date__lte=today, end_date__gte=today)
            .order_by('-end_date')
            .first()
        )
        if not active_sub:
            self.message = "Faol tarif topilmadi."
            return False

        plan = active_sub.plan
        # Foydalanuvchi roli POST bodyda bo'lishi kerak
        role = request.data.get('role')
        if role == 'director':
            limit = plan.director_limit
            count = clinic.users.filter(role='director').count()
        elif role == 'admin':
            limit = plan.admin_limit
            count = clinic.users.filter(role='admin').count()
        elif role == 'doctor':
            limit = plan.doctor_limit
            count = clinic.users.filter(role='doctor').count()
        else:
            return True  # Boshqa rollar uchun cheklov yo'q

        return count < limit

class CanCreateBranchByPlanLimit(permissions.BasePermission):
    message = "Tarif bo‘yicha filial limiti tugagan."

    def has_permission(self, request, view):
        clinic = getattr(request.user, 'clinic', None)
        if not clinic:
            return False

        today = timezone.now().date()
        active_sub = (
            ClinicSubscription.objects
            .filter(clinic=clinic, start_date__lte=today, end_date__gte=today)
            .order_by('-end_date')
            .first()
        )
        if not active_sub:
            self.message = "Faol tarif topilmadi."
            return False

        plan = active_sub.plan
        limit = plan.branch_limit
        count = clinic.branches.count()
        return count < limit