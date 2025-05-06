from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from app.models import *
from app2.models import *
from .serializers import *
from app.serializers import *
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.db.models.functions import ExtractMonth, ExtractWeekDay
from datetime import datetime, timedelta

class VitalSignViewSet(viewsets.ModelViewSet):
    """
    Hayotiy ko'rsatkichlar bilan ishlash uchun ViewSet.
    """
    queryset = VitalSign.objects.all()
    serializer_class = VitalSignSerializer

    def perform_create(self, serializer):
        """
        Hayotiy ko'rsatkichlarni yaratishda bemor (Customer) ma'lumotlarini ulash.
        """
        customer_id = self.request.data.get('customer_id')
        if customer_id:
            customer = Customer.objects.get(id=customer_id)
            serializer.save(customer=customer)
        else:
            raise ValueError("Customer ID'si talab qilinadi.")
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Bemorning hayotiy ko'rsatkichlari tarixini ko'rsatish.
        """
        customer = Customer.objects.get(pk=pk)
        vital_signs = customer.vital_signs.all().order_by('-recorded_at')
        serializer = VitalSignSerializer(vital_signs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def chart_data(self, request, pk=None):
        """
        Diagramma uchun bemorning barcha hayotiy ko'rsatkichlarini qaytarish.
        """
        customer = get_object_or_404(Customer, pk=pk)
        vital_signs = customer.vital_signs.all().order_by('recorded_at')  # Vaqt bo'yicha tartiblangan
        data = {
            "temperature": [{"time": vs.recorded_at, "value": vs.temperature} for vs in vital_signs],
            "blood_pressure": [{"time": vs.recorded_at, "value": vs.blood_pressure} for vs in vital_signs],
            "heart_rate": [{"time": vs.recorded_at, "value": vs.heart_rate} for vs in vital_signs],
            "respiratory_rate": [{"time": vs.recorded_at, "value": vs.respiratory_rate} for vs in vital_signs],
            "oxygen_saturation": [{"time": vs.recorded_at, "value": vs.oxygen_saturation} for vs in vital_signs],
        }
        return Response(data)




class MedicineViewSet(viewsets.ModelViewSet):
    """
    Dorilar ro'yxati bilan ishlash uchun ViewSet.
    """
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer

    def perform_create(self, serializer):
        """
        Medicine yaratilganda token orqali foydalanuvchining filialini ulash.
        """
        user = self.request.user
        if not hasattr(user, 'branch'):
            raise PermissionDenied("Foydalanuvchining filial ma'lumoti mavjud emas.")
        serializer.save(branch=user.branch)


class MedicineScheduleViewSet(viewsets.ModelViewSet):
    """
    Dori berish jadvali bilan ishlash uchun ViewSet.
    """
    queryset = MedicineSchedule.objects.all()
    serializer_class = MedicineScheduleSerializer


class MedicineHistoryViewSet(viewsets.ModelViewSet):
    """
    Dori berish tarixi bilan ishlash uchun ViewSet.
    """
    queryset = MedicineHistory.objects.all()
    serializer_class = MedicineHistorySerializer


class NurseScheduleViewSet(viewsets.ModelViewSet):
    queryset = NurseSchedule.objects.all()
    serializer_class = NurseScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter schedules for the logged-in user if they are a nurse
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return NurseSchedule.objects.filter(user_id=user_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        # Ensure a schedule is created for all 7 days if not already present
        user = serializer.validated_data['user']
        day = serializer.validated_data['day']
        if NurseSchedule.objects.filter(user=user, day=day).exists():
            raise serializers.ValidationError(f"Schedule for {day} already exists for this nurse.")
        serializer.save()


class HospitalizationViewSet(viewsets.ModelViewSet):
    queryset = Hospitalization.objects.all()
    serializer_class = HospitalizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            return Hospitalization.objects.filter(patient_id=patient_id)
        return super().get_queryset()


class FAQViewSet(viewsets.ModelViewSet):
    """
    FAQ va rasmlar bilan ishlash uchun ViewSet.
    """
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer

    def create(self, request, *args, **kwargs):
        """
        FAQ yaratish va rasmlarni yuklash.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_images = serializer.validated_data.pop('uploaded_images', [])  # Yuklangan rasmlarni olish
        faq = FAQ.objects.create(**serializer.validated_data)

        # Rasmlarni saqlash va FAQ bilan bog'lash
        for image in uploaded_images:
            faq_image = FAQImages.objects.create(image=image)
            faq.images.add(faq_image)

        faq.save()
        return Response(self.get_serializer(faq).data)

class MeetingFilterView(APIView):
    """
    Meeting uchun filtrlash API.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Foydalanuvchining klinikasi
        if not user.clinic:
            return Response({"error": "Foydalanuvchi hech qanday klinikaga bog'lanmagan."}, status=400)

        # Branchlar
        branches = Branch.objects.filter(clinic=user.clinic)
        branch_serializer = BranchSerializer(branches, many=True)

        # Tanlangan branchga bog'liq Customers
        branch_id = request.query_params.get('branch_id')
        customers = Customer.objects.filter(branch_id=branch_id) if branch_id else []
        customer_serializer = CustomerSerializer(customers, many=True)

        # Tanlangan branchga bog'liq Doctors
        doctors = User.objects.filter(branch_id=branch_id, role='doctor') if branch_id else []
        doctor_serializer = DoctorSerializer(doctors, many=True)

        # Tanlangan branchga bog'liq Cabinets
        cabinets = Cabinet.objects.filter(branch_id=branch_id) if branch_id else []
        cabinet_serializer = CabinetSerializer(cabinets, many=True)

        doctor_id = request.query_params.get('doctor')  # Tanlangan shifokor
        cabinet_id = request.query_params.get('cabinet')  # Tanlangan kabinet
        date = request.query_params.get('date')  # Tanlangan sana
        # Band vaqtlar
        busy_times_query = Meeting.objects.filter(branch_id=branch_id)

        if doctor_id:
            busy_times_query = busy_times_query.filter(doctor_id=doctor_id)
        if cabinet_id:
            busy_times_query = busy_times_query.filter(room_id=cabinet_id)
        if date:
            busy_times_query = busy_times_query.filter(date__date=date)  # Faqat sana bo'yicha filtr
        
        busy_times = busy_times_query.values('date')
        for busy_time in busy_times:
            if isinstance(busy_time['date'], datetime.datetime):  # Agar datetime bo'lsa
                busy_time['date'] = busy_time['date'].isoformat()  # ISO formatga o'tkazish
        busy_time_serializer = BusyTimeSerializer(busy_times, many=True)

        return Response({
            "branches": branch_serializer.data,
            "customers": customer_serializer.data,
            "doctors": doctor_serializer.data,
            "cabinets": cabinet_serializer.data,
            "busy_times": busy_time_serializer.data
        })


class PasswordResetRequestView(APIView):
    """
    Foydalanuvchiga 6 xonali tasdiqlash kodini yuborish uchun API.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            user.generate_reset_code()  # Tasdiqlash kodini yaratish

            # Email yuborish
            subject = "Parolni tiklash uchun tasdiqlash kodi"
            message = f"Parolni tiklash uchun tasdiqlash kodi: {user.reset_password_code}\n\nKod 10 daqiqa davomida amal qiladi."
            send_mail(subject, message, settings.EMAIL_HOST_USER, [email])

            return Response({"detail": "Tasdiqlash kodi emailga yuborildi."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetCodeVerifyView(APIView):
    """
    Tasdiqlash kodini tekshirish va vaqtinchalik token yaratish uchun API.
    """
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordResetCodeSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = serializer.validated_data['code']

            try:
                user = User.objects.get(email=email, reset_password_code=code)
            except User.DoesNotExist:
                return Response({"error": "Email yoki kod noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)

            # Kodning amal qilish muddatini tekshirish
            if user.reset_password_code_expiry < now():
                return Response({"error": "Tasdiqlash kodi muddati o'tgan."}, status=status.HTTP_400_BAD_REQUEST)

            # Vaqtinchalik token yaratish
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            # Kodni o'chirish
            user.reset_password_code = None
            user.reset_password_code_expiry = None
            user.save()

            return Response({"detail": "Tasdiqlash kodi to'g'ri.", "token": access_token}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetChangeView(APIView):
    """
    Parolni o'zgartirish uchun API (token orqali).
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetChangeSerializer(data=request.data)
        if serializer.is_valid():
            new_password = serializer.validated_data['new_password']
            confirm_password = serializer.validated_data['confirm_password']

            if new_password != confirm_password:
                return Response({"error": "Parollar mos emas."}, status=status.HTTP_400_BAD_REQUEST)

            # Foydalanuvchini olish (token orqali)
            user = request.user

            # Parolni o'zgartirish
            user.set_password(new_password)
            user.save()

            return Response({"detail": "Parol muvaffaqiyatli o'zgartirildi."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarkNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        notification_id = request.data.get('notification_id')

        if not notification_id:
            return Response({"error": "Notification ID is required."}, status=400)

        notification = Notification.objects.get(id=notification_id)
        read_status, created = NotificationReadStatus.objects.get_or_create(
            user=request.user,
            notification=notification
        )
        read_status.is_read = True
        read_status.read_at = now()
        read_status.save()

        return Response({"detail": "Notification marked as read."})


class MarkClinicNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        clinic_notification_id = request.data.get('clinic_notification_id')

        if not clinic_notification_id:
            return Response({"error": "Clinic Notification ID is required."}, status=400)

        clinic_notification = ClinicNotification.objects.get(id=clinic_notification_id)
        read_status, created = ClinicNotificationReadStatus.objects.get_or_create(
            user=request.user,
            clinic_notification=clinic_notification
        )
        read_status.is_read = True
        read_status.read_at = now()
        read_status.save()

        return Response({"detail": "Clinic Notification marked as read."})


class MarkAllNotificationsAsReadView(APIView):
    """
    Foydalanuvchi uchun barcha Notification va ClinicNotification xabarnomalarini o'qilgan deb belgilaydi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Notification xabarnomalarini o'qilgan deb belgilash
        notifications = Notification.objects.all()
        for notification in notifications:
            read_status, created = NotificationReadStatus.objects.get_or_create(
                user=request.user,
                notification=notification
            )
            read_status.is_read = True
            read_status.read_at = now()
            read_status.save()

        # ClinicNotification xabarnomalarini o'qilgan deb belgilash
        clinic_notifications = ClinicNotification.objects.all()
        for clinic_notification in clinic_notifications:
            read_status, created = ClinicNotificationReadStatus.objects.get_or_create(
                user=request.user,
                clinic_notification=clinic_notification
            )
            read_status.is_read = True
            read_status.read_at = now()
            read_status.save()

        return Response({"detail": "All notifications marked as read."})


class MarkAllNotificationsAsReadView(APIView):
    """
    Foydalanuvchi uchun barcha Notification xabarnomalarini o'qilgan deb belgilaydi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        notifications = Notification.objects.all()
        for notification in notifications:
            read_status, created = NotificationReadStatus.objects.get_or_create(
                user=request.user,
                notification=notification
            )
            read_status.is_read = True
            read_status.read_at = now()
            read_status.save()

        return Response({"detail": "All notifications marked as read."})

class MarkAllClinicNotificationsAsReadView(APIView):
    """
    Foydalanuvchi uchun barcha ClinicNotification xabarnomalarini o'qilgan deb belgilaydi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        clinic_notifications = ClinicNotification.objects.all().filter(
            clinic=request.user.clinic
        )
        for clinic_notification in clinic_notifications:
            read_status, created = ClinicNotificationReadStatus.objects.get_or_create(
                user=request.user,
                clinic_notification=clinic_notification
            )
            read_status.is_read = True
            read_status.read_at = now()
            read_status.save()

        return Response({"detail": "All clinic notifications marked as read."})
    



class UnreadNotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Foydalanuvchining o'qilmagan bildirishnomalar sonini qaytaradi.
        """
        user = request.user

        # Foydalanuvchiga tegishli NotificationReadStatus yozuvlarini olish
        read_status_notifications = NotificationReadStatus.objects.filter(user=user).values_list('notification_id', flat=True)

        # O'qilmagan bildirishnomalar sonini aniqlash
        unread_count = Notification.objects.filter(
            Q(id__in=read_status_notifications, read_statuses__is_read=False) |
            Q(~Q(id__in=read_status_notifications))
        ).distinct().count()

        return Response({'unread_count': unread_count})


class UnreadClinicNotificationCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Foydalanuvchining o'qilmagan klinik bildirishnomalar sonini qaytaradi.
        """
        user = request.user

        # Foydalanuvchining o'qigan bildirishnomalari (idlari)
        read_ids = ClinicNotificationReadStatus.objects.filter(user=user, is_read=True).values_list('clinic_notification_id', flat=True)

        # Foydalanuvchining hali o‘qimagan klinik bildirishnomalari
        if user.role == 'doctor':
            unread_count = ClinicNotification.objects.filter(branch=user.branch).exclude(id__in=read_ids).count()
        else:
            unread_count = ClinicNotification.objects.filter(clinic=user.clinic).exclude(id__in=read_ids).count()

        return Response({'unread_count': unread_count})


class DashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Hozirgi oy va o'tgan oyning boshlanish va tugash sanalari
        today = datetime.today()
        first_day_of_this_month = today.replace(day=1)
        first_day_of_last_month = (first_day_of_this_month - timedelta(days=1)).replace(day=1)
        last_day_of_last_month = first_day_of_this_month - timedelta(days=1)

        # Filial bo'yicha ma'lumotlarni olish
        if branch_id == 'all':
            customers = Customer.objects.filter(branch__clinic=clinic, created_at__gte=first_day_of_this_month)
            doctors = User.objects.filter(clinic=clinic, role='doctor', date_joined__gte=first_day_of_this_month)
            cabinets = Cabinet.objects.filter(branch__clinic=clinic, created_at__gte=first_day_of_this_month)
            meetings = Meeting.objects.filter(branch__clinic=clinic, created_at__gte=first_day_of_this_month)
        else:
            customers = Customer.objects.filter(branch_id=branch_id, branch__clinic=clinic, created_at__gte=first_day_of_this_month)
            doctors = User.objects.filter(branch_id=branch_id, clinic=clinic, role='doctor', date_joined__gte=first_day_of_this_month)
            cabinets = Cabinet.objects.filter(branch_id=branch_id, branch__clinic=clinic, created_at__gte=first_day_of_this_month)
            meetings = Meeting.objects.filter(branch_id=branch_id, branch__clinic=clinic, created_at__gte=first_day_of_this_month)

        # O'tgan oy uchun ma'lumotlarni olish
        if branch_id == 'all':
            last_month_customers = Customer.objects.filter(branch__clinic=clinic, created_at__range=[first_day_of_last_month, last_day_of_last_month]).count()
            last_month_doctors = User.objects.filter(clinic=clinic, role='doctor', date_joined__range=[first_day_of_last_month, last_day_of_last_month]).count()
            last_month_cabinets = Cabinet.objects.filter(branch__clinic=clinic, created_at__range=[first_day_of_last_month, last_day_of_last_month]).count()
            last_month_meetings = Meeting.objects.filter(branch__clinic=clinic, created_at__range=[first_day_of_last_month, last_day_of_last_month]).count()
        else:
            last_month_customers = Customer.objects.filter(branch_id=branch_id, branch__clinic=clinic, created_at__range=[first_day_of_last_month, last_day_of_last_month]).count()
            last_month_doctors = User.objects.filter(branch_id=branch_id, clinic=clinic, role='doctor', date_joined__range=[first_day_of_last_month, last_day_of_last_month]).count()
            last_month_cabinets = Cabinet.objects.filter(branch_id=branch_id, branch__clinic=clinic, created_at__range=[first_day_of_last_month, last_day_of_last_month]).count()
            last_month_meetings = Meeting.objects.filter(branch_id=branch_id, branch__clinic=clinic, created_at__range=[first_day_of_last_month, last_day_of_last_month]).count()

        # Hozirgi oy uchun ma'lumotlarni hisoblash
        current_month_customers = customers.count()
        current_month_doctors = doctors.count()
        current_month_cabinets = cabinets.count()
        current_month_meetings = meetings.count()

        # O'zgarish foizini hisoblash
        def calculate_percentage_change(current, previous):
            if previous == 0:
                return 0 if current == 0 else 100
            return round(((current - previous) / previous) * 100, 2)

        customer_growth = calculate_percentage_change(current_month_customers, last_month_customers)
        doctor_growth = calculate_percentage_change(current_month_doctors, last_month_doctors)
        cabinet_growth = calculate_percentage_change(current_month_cabinets, last_month_cabinets)
        meeting_growth = calculate_percentage_change(current_month_meetings, last_month_meetings)

        # Javobni shakllantirish
        data = {
            "customers": {
                "total": current_month_customers,
                "growth": customer_growth
            },
            "doctors": {
                "total": current_month_doctors,
                "growth": doctor_growth
            },
            "cabinets": {
                "total": current_month_cabinets,
                "growth": cabinet_growth
            },
            "meetings": {
                "total": current_month_meetings,
                "growth": meeting_growth
            }
        }

        return Response(data)


class WeeklyAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Bugungi sana va haftaning boshlanish sanasi
        today = datetime.today()
        start_of_week = today - timedelta(days=today.weekday())  # Dushanba

        # Filial bo'yicha uchrashuvlarni olish
        if branch_id == 'all':
            meetings = Meeting.objects.filter(branch__clinic=clinic, date__date__gte=start_of_week)
        else:
            meetings = Meeting.objects.filter(branch_id=branch_id, branch__clinic=clinic, date__date__gte=start_of_week)

        # Haftalik uchrashuvlarni kunlar bo'yicha guruhlash
        weekly_data = meetings.annotate(day=ExtractWeekDay('date')).values('day').annotate(count=Count('id')).order_by('day')

        # Haftalik ma'lumotlarni shakllantirish
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        data = {day: 0 for day in days}
        for item in weekly_data:
            data[days[item['day'] - 1]] = item['count']

        return Response({'weekly_appointments': data})


class PatientDistributionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Filial bo'yicha mijozlarni olish
        if branch_id == 'all':
            customers = Customer.objects.filter(branch__clinic=clinic)
        else:
            customers = Customer.objects.filter(branch_id=branch_id, branch__clinic=clinic)

        # Jinsi bo'yicha guruhlash
        male_count = customers.filter(gender='male').count()
        female_count = customers.filter(gender='female').count()

        return Response({
            'male': male_count,
            'female': female_count
        })


class MonthlyCustomerTrendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Yil boshidan boshlab mijozlarni olish
        start_of_year = datetime(datetime.today().year, 1, 1)

        if branch_id == 'all':
            customers = Customer.objects.filter(branch__clinic=clinic, created_at__gte=start_of_year)
        else:
            customers = Customer.objects.filter(branch_id=branch_id, branch__clinic=clinic, created_at__gte=start_of_year)

        # Har oy bo'yicha guruhlash
        monthly_data = customers.annotate(month=ExtractMonth('created_at')).values('month').annotate(count=Count('id')).order_by('month')

        # Har oy uchun ma'lumotlarni shakllantirish
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        data = {month: 0 for month in months}
        for item in monthly_data:
            data[months[item['month'] - 1]] = item['count']

        return Response({'monthly_customer_trend': data})


class RecentPatientsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Filial bo'yicha mijozlarni olish
        if branch_id == 'all':
            customers = Customer.objects.filter(branch__clinic=clinic).order_by('-created_at')[:5]
        else:
            customers = Customer.objects.filter(branch_id=branch_id, branch__clinic=clinic).order_by('-created_at')[:5]

        # Mijozlar ma'lumotlarini qaytarish
        data = [
            {
                "full_name": customer.full_name,
                "age": customer.age,
                "diagnosis": customer.status,
                "created_at": customer.created_at.strftime('%Y-%m-%d')
            }
            for customer in customers
        ]

        return Response({"recent_patients": data})

class PendingTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Filial bo'yicha bugungi vazifalarni olish
        today = datetime.today().date()
        if branch_id == 'all':
            tasks = Task.objects.filter(branch__clinic=clinic, due_date=today, status='pending')
        else:
            tasks = Task.objects.filter(branch_id=branch_id, branch__clinic=clinic, due_date=today, status='pending')

        # Vazifalar ma'lumotlarini qaytarish
        data = [
            {
                "title": task.title,
                "assignee": f"{task.assignee.first_name} {task.assignee.last_name}",
                "due_date": task.due_date.strftime('%Y-%m-%d'),
                "priority": task.priority,
                "status": task.status
            }
            for task in tasks
        ]

        return Response({"pending_tasks": data})

class CabinetUtilizationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Filial bo'yicha kabinetlardan foydalanish statistikasi
        if branch_id == 'all':
            cabinets = Cabinet.objects.filter(branch__clinic=clinic)
        else:
            cabinets = Cabinet.objects.filter(branch_id=branch_id, branch__clinic=clinic)

        # Har bir kabinet uchun uchrashuvlar sonini hisoblash
        data = []
        for cabinet in cabinets:
            total_meetings = Meeting.objects.filter(room=cabinet).count()
            utilization_percentage = (total_meetings / 100) * 100  # Foydalanish foizi (misol uchun)
            data.append({
                "cabinet_name": cabinet.name,
                "utilization": utilization_percentage
            })

        return Response({"cabinet_utilization": data})