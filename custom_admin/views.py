from datetime import datetime
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from .models import *
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from .serializers import *
from rest_framework.permissions import IsAdminUser
from app.serializers import LoginSerializer
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from app.serializers import *
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from app.pagination import *
from decimal import Decimal

class ClinicSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = ClinicSubscription.objects.all()
    serializer_class = ClinicSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Faqat superuserlar va `role=director` bo'lgan foydalanuvchilar uchun ma'lumotlarni cheklash.
        """
        user = self.request.user
        if user.is_superuser:
            return ClinicSubscription.objects.all()
        elif user.role == 'director':
            return ClinicSubscription.objects.filter(clinic__director=user)
        return ClinicSubscription.objects.none()
    
    def create(self, request, *args, **kwargs):
        clinic_id = request.data.get('clinic')
        if ClinicSubscription.objects.filter(clinic_id=clinic_id, status='active').exists():
            return Response(
                {"clinic": "Ushbu klinikaning faol obunasi allaqachon mavjud."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAdminUser]  # Faqat superuserlar uchun ruxsat


class ClinicDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, clinic_id, *args, **kwargs):
            try:
                clinic = Clinic.objects.get(id=clinic_id)
                subscription = ClinicSubscription.objects.filter(clinic=clinic).first()
                director = User.objects.filter(clinic=clinic, role='director').first()

                # Klinikaga tegishli barcha branchlar
                branches = Branch.objects.filter(clinic=clinic)

                # Klinikaga bog'liq barcha modellar uchun taxminiy hajm hisoblash (obyekt soniga asoslangan)
                user_count = User.objects.filter(clinic=clinic).count()
                branch_count = branches.count()
                patient_count = Customer.objects.filter(branch__in=branches).count()
                appointment_count = Customer.objects.filter(branch__in=branches).count()
                meeting_count = Meeting.objects.filter(branch__in=branches).count()

                # Taxminiy saqlash hajmi (MB) — bu siz belgilagan o'rtacha qiymatlar asosida
                total_storage_used_mb = (
                    user_count * 0.2 +           # Har bir foydalanuvchi ~0.2 MB
                    branch_count * 0.5 +         # Har bir filial ~0.5 MB
                    patient_count * 0.3 +        # Har bir bemor ~0.3 MB
                    appointment_count * 0.1 +    # Har bir qabul ~0.1 MB
                    meeting_count * 0.15         # Har bir uchrashuv ~0.15 MB
                )

                total_storage_used_gb = round(total_storage_used_mb / 1024, 2)  # MB -> GB

                data = {
                    "clinic_name": clinic.name,
                    "director": f"{director.first_name} {director.last_name}" if director else "Noma'lum",
                    # "address": clinic.address,
                    "phone": clinic.phone_number,
                    "email": clinic.email,
                    "status": clinic.is_active,
                    "storage": {
                        "used": total_storage_used_gb,
                        "allocated": subscription.plan.storage_limit_gb if subscription else 0,
                        "remaining": round(float(subscription.plan.storage_limit_gb) - total_storage_used_gb, 2) if subscription else 0
                    }
                }
                return Response(data, status=200)

            except Clinic.DoesNotExist:
                return Response({"error": "Klinika topilmadi."}, status=404)
    def patch(self, request, clinic_id, *args, **kwargs):
        clinic = get_object_or_404(Clinic, pk=clinic_id)
        serializer = ClinicSerializer(clinic, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, clinic_id, *args, **kwargs):
        clinic = get_object_or_404(Clinic, pk=clinic_id)
        clinic.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class BranchListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, clinic_id, *args, **kwargs):
        branches = Branch.objects.filter(clinic_id=clinic_id)
        data = []

        for branch in branches:
            # Foydalanuvchilarni rollar bo'yicha hisoblash
            doctors = User.objects.filter(branch=branch, role="doctor").count()
            administrators = User.objects.filter(branch=branch, role="admin").count()
            nurses = User.objects.filter(branch=branch, role="nurse").count()
            total_employees = User.objects.filter(branch=branch).count()

            # Bemorlarni hisoblash
            patients = Customer.objects.filter(branch=branch).count()

            # Filial ma'lumotlarini yig'ish
            data.append({
                "name": branch.name,
                "address": branch.address,
                "phone": branch.phone_number,
                "doctors": doctors,
                "administrators": administrators,
                "nurses": nurses,
                "total_employees": total_employees,
                "patients": patients
            })

        return Response(data, status=200)


class SubscriptionDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, clinic_id, *args, **kwargs):
        try:
            subscription = ClinicSubscription.objects.filter(clinic_id=clinic_id, status='active').first()
            data = {
                "plan_name": subscription.plan.name,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "discount": subscription.discount,
                "trial_period": subscription.plan.trial_period_days
            }
            return Response(data, status=200)
        except ClinicSubscription.DoesNotExist:
            return Response({"error": "Obuna ma'lumotlari topilmadi."}, status=404)


class FinancialDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, clinic_id, *args, **kwargs):
        try:
            clinic = Clinic.objects.get(id=clinic_id)
            subscription = ClinicSubscription.objects.filter(clinic=clinic).first()

            branches = Branch.objects.filter(clinic=clinic)

            # Klinikaga bog'liq ma'lumotlar soni
            user_count = User.objects.filter(clinic=clinic).count()
            branch_count = branches.count()
            patient_count = Customer.objects.filter(branch__in=branches).count()
            customer_count = Customer.objects.filter(branch__in=branches).count()
            meeting_count = Meeting.objects.filter(branch__in=branches).count()

            # Taxminiy saqlash hajmini hisoblash (MB)
            total_storage_used_mb = (
                user_count * 0.2 +
                branch_count * 0.5 +
                patient_count * 0.3 +
                customer_count * 0.1 +
                meeting_count * 0.15
            )
            total_storage_used_gb = round(total_storage_used_mb / 1024, 2)
            
            # Moliyaviy hisoblash
            storage_cost_per_gb = 10000  # So'm
            data_storage_cost = total_storage_used_gb * storage_cost_per_gb
            data_storage_cost = total_storage_used_gb * storage_cost_per_gb
            subscription_price = subscription.plan.price if subscription else 0

            discount_amount = Decimal(0)
            if subscription and subscription.discount:
                try:
                    discount_percentage = Decimal(subscription.discount.strip('%')) / Decimal(100)
                    discount_amount = subscription_price * (Decimal(1) - discount_percentage)
                except ValueError:
                    discount_amount = subscription_price  # Agar discount noto'g'ri formatda bo'lsa, to'liq narxni hisoblaymiz

            # Klinikaga ajratilgan joyning summasini hisoblash
            allocated_storage_cost = Decimal(0)
            if subscription and subscription.plan.storage_limit_gb:
                allocated_storage_cost = Decimal(subscription.plan.storage_limit_gb) * Decimal(storage_cost_per_gb)
            net_profit = round(discount_amount - allocated_storage_cost, 2)
            data = {
                "subscription_price": round(subscription_price, 2),  # Tarif narxi
                "discount_amount": round(discount_amount, 2),       # Discountdan keyingi summa
                "data_storage_cost": round(data_storage_cost, 2),   # Saqlash narxi
                "allocated_storage_cost": round(allocated_storage_cost, 2),  # Ajratilgan joy summasi
                "net_profit": net_profit,                           # Net foyda
                "estimated_storage_used_gb": total_storage_used_gb  # Taxminiy ishlatilgan joy
            }
            return Response(data, status=200)

        except Clinic.DoesNotExist:
            return Response({"error": "Klinika topilmadi."}, status=404)



class BranchStatisticsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, clinic_id, *args, **kwargs):
        branches = Branch.objects.filter(clinic_id=clinic_id)
        data = []

        for branch in branches:
            # Xodimlar statistikasi
            doctors = User.objects.filter(branch=branch, role="doctor").count()
            admins = User.objects.filter(branch=branch, role="admin").count()
            nurses = User.objects.filter(branch=branch, role="nurse").count()
            total_employees = User.objects.filter(branch=branch).count()

            # Bemorlar statistikasi
            total_patients = Customer.objects.filter(branch=branch).count()
            daily_patients = Customer.objects.filter(branch=branch, created_at__date__gte=datetime.now().date()).count()
            monthly_patients = Customer.objects.filter(branch=branch, created_at__date__gte=(datetime.now() - timedelta(days=30))).count()
            yearly_patients = Customer.objects.filter(branch=branch, created_at__date__gte=(datetime.now() - timedelta(days=365))).count()

            # Filial ma'lumotlarini yig'ish
            data.append({
                "branch_name": branch.name,
                "employees": {
                    "total": total_employees,
                    "doctors": doctors,
                    "admins": admins,
                    "nurses": nurses,
                },
                "patients": {
                    "total": total_patients,
                    "daily": daily_patients,
                    "monthly": monthly_patients,
                    "yearly": yearly_patients,
                }
            })

        return Response(data, status=200)


class ApiIssueViewSet(viewsets.ModelViewSet):
    queryset = ApiIssue.objects.all().order_by('-reported_at')
    serializer_class = ApiIssueSerializer

    def get_permissions(self):
        """
        POST so'rovlar uchun `AllowAny`, boshqa operatsiyalar uchun `IsAuthenticated`.
        """
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """
        PATCH so'rovlar uchun alohida serializer ishlatish.
        """
        if self.action in ['update', 'partial_update']:
            return ApiIssueUpdateSerializer
        return super().get_serializer_class()

    def partial_update(self, request, *args, **kwargs):
        """
        Statusni yangilash va hal qilingan vaqtni qo'shish.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Muammo holati muvaffaqiyatli yangilandi."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SuperuserLoginView(APIView):
    permission_classes = [AllowAny]  # Superuser login uchun ruxsatni boshqarish

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)

            if user and user.is_superuser:  # Faqat superuserlarni tekshirish
                refresh = RefreshToken.for_user(user)
                return Response({
                    'token': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role,
                        'is_superuser': user.is_superuser
                    }
                })
            return Response(
                {'error': "Faqat superuserlar tizimga kira oladi yoki noto'g'ri login/parol."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClinicListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        clinics = Clinic.objects.all()
        paginator = CustomPagination()
        result_page = paginator.paginate_queryset(clinics, request)

        data = []

        for clinic in result_page:  # SHU YERDA o‘zgartirish kiritildi
            branches = Branch.objects.filter(clinic=clinic)
            branch_count = branches.count()
            total_employees = User.objects.filter(branch__in=branches).count()

            subscription = ClinicSubscription.objects.filter(clinic=clinic, status='active').first()
            subscription_plan = subscription.plan.name if subscription and subscription.plan else "Noma'lum"
            storage_limit = subscription.plan.storage_limit_gb if subscription and subscription.plan else 0

            storage_used = 0
            for branch in branches:
                patients_storage = branch.users.count() * 0.01
                employees_storage = branch.users.count() * 0.005
                storage_used += patients_storage + employees_storage
            storage_used = round(storage_used, 2)

            director = User.objects.filter(clinic=clinic, role="director").first()
            director_name = f"{director.first_name} {director.last_name}" if director else "Noma'lum"

            status = "Faol" if getattr(clinic, "is_active", True) else "Faol emas"

            data.append({
                "id": clinic.id,
                "clinic_name": clinic.name,
                "director": director_name,
                "branches": branch_count,
                "employees": total_employees,
                "subscription_plan": subscription_plan,
                "storage": f"{storage_used} GB / {storage_limit} GB",
                "subscription_period": f"{subscription.start_date} - {subscription.end_date}" if subscription else "Noma'lum",
                "status": status,
            })

        return paginator.get_paginated_response(data)


class ClinicSubscriptionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClinicSubscription.objects.all().order_by('-start_date')
    serializer_class = ClinicSubscriptionSerializer
    permission_classes = [IsAdminUser]  # Faqat superuserlar uchun ruxsat


class ClinicSubscriptionHistoryInIDView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, clinic_id, *args, **kwargs):
        user = request.user
        # Faqat superuser yoki shu klinikaning direktori ko‘ra oladi
        if not (user.is_superuser or (user.role == 'director' and user.clinic_id == clinic_id)):
            return Response({"detail": "Ruxsat yo‘q."}, status=403)

        subscriptions = ClinicSubscription.objects.filter(clinic_id=clinic_id).order_by('-start_date')

        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get('page_size', 10))
        result_page = paginator.paginate_queryset(subscriptions, request)

        data = []
        for sub in result_page:
            data.append({
                "plan": sub.plan.name if sub.plan else None,
                "start_date": sub.start_date,
                "end_date": sub.end_date,
                "status": sub.status,
                "discount": sub.discount,
                "paid_amount": sub.paid_amount,
                # "created_at": sub.created_at,
                # "updated_at": sub.updated_at,
            })
        return paginator.get_paginated_response(data)

class ClinicSelectListView(APIView):
    permission_classes = [IsAuthenticated]  # Faqat autentifikatsiya qilingan foydalanuvchilar uchun

    def get(self, request, *args, **kwargs):
        search_query = request.query_params.get('search', '')  # Qidiruv so'rovi
        clinics = Clinic.objects.filter(name__icontains=search_query)  # Klinikalarni qidiruv bo'yicha filtrlash
        data = clinics.values('id', 'name')  # Faqat kerakli maydonlarni qaytarish
        return Response(data, status=200)


class SubscriptionPlanSelectListView(APIView):
    permission_classes = [IsAuthenticated]  # Faqat autentifikatsiya qilingan foydalanuvchilar uchun

    def get(self, request, *args, **kwargs):
        search_query = request.query_params.get('search', '')  # Qidiruv so'rovi
        plans = SubscriptionPlan.objects.filter(name__icontains=search_query)  # Rejalarni qidiruv bo'yicha filtrlash
        data = plans.values('id', 'name', 'price', 'storage_limit_gb', 'trial_period_days')  # Faqat kerakli maydonlarni qaytarish
        return Response(data, status=200)


class ClinicTariffStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        clinic = request.user.clinic

        # Eng so‘nggi faol subscription
        subscription = ClinicSubscription.objects.filter(
            clinic=clinic, status='active'
        ).order_by('-end_date').first()
        if not subscription:
            return Response({"detail": "Faol tarif topilmadi."}, status=404)

        plan = subscription.plan

        # Klinikadagi userlar statistikasi
        total_directors = User.objects.filter(role='director', clinic=clinic).count()
        total_admins = User.objects.filter(role='admin', clinic=clinic).count()
        total_doctors = User.objects.filter(role='doctor', clinic=clinic).count()
        total_branches = Branch.objects.filter(clinic=clinic).count()

        data = {
            "tariff": {
                "name": plan.name,
                "description": plan.description,
                "storage_limit_gb": plan.storage_limit_gb,
                "trial_period_days": plan.trial_period_days,
                "price": plan.price,
                "director_limit": plan.director_limit,
                "admin_limit": plan.admin_limit,
                "doctor_limit": plan.doctor_limit,
                "branch_limit": plan.branch_limit,
            },
            "usage": {
                "directors": total_directors,
                "admins": total_admins,
                "doctors": total_doctors,
                "branches": total_branches,
            },
            "limits": {
                "directors_left": max(plan.director_limit - total_directors, 0),
                "admins_left": max(plan.admin_limit - total_admins, 0),
                "doctors_left": max(plan.doctor_limit - total_doctors, 0),
                "branches_left": max(plan.branch_limit - total_branches, 0),
            },
            "subscription": {
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "status": subscription.status,
                "paid_amount": subscription.paid_amount,
                "discount": subscription.discount,
                "description_discount": subscription.description_discount,
            }
        }
        return Response(data)


class InactiveClinicViewSet(viewsets.ModelViewSet):
    queryset = InactiveClinic.objects.select_related('clinic').all()
    permission_classes = [IsAdminUser]
    serializer_class = InactiveClinicSerializer  # Yangi serializer yozing

    @action(detail=True, methods=['post'])
    def add_days(self, request, pk=None):
        obj = self.get_object()
        days = int(request.data.get('days', 1))
        comment = request.data.get('comment', '')

        obj.inactive_days += days
        obj.comment = comment
        obj.save(update_fields=['inactive_days', 'comment'])

        # Klinikaga email yuborish
        clinic = obj.clinic
        if clinic.email:
            from django.core.mail import send_mail
            send_mail(
                subject="Klinikangiz faol emasligi haqida ogohlantirish",
                message=f"Hurmatli {clinic.name}, sizning klinikangizga {days} kun qo‘shildi.\n\nIzoh: {comment}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[clinic.email],
                fail_silently=True,
            )

        return Response({'status': 'days added', 'inactive_days': obj.inactive_days, 'comment': obj.comment})

    @action(detail=True, methods=['post'])
    def notify(self, request, pk=None):
        obj = self.get_object()
        clinic = obj.clinic
        if clinic.email:
            send_mail(
                subject="Klinika faol emasligi haqida ogohlantirish",
                message=f"Hurmatli {clinic.name}, sizning klinikangiz foydalanuvchilari {obj.inactive_days} kundan beri faol emas.",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[clinic.email],
                fail_silently=True,
            )
            obj.notified = True
            obj.save(update_fields=['notified'])
            return Response({'status': 'notified'})
        return Response({'error': 'Clinic email not found'}, status=status.HTTP_400_BAD_REQUEST)



class ClinicNotifyView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, clinic_id):
        title = request.data.get('title')
        message = request.data.get('message')
        if not title or not message:
            return Response({'error': 'title va message majburiy.'}, status=400)

        # Klinikani va direktorini topish
        clinic = get_object_or_404(Clinic, pk=clinic_id)
        director = clinic.users.filter(role='director').first()

        # Notification modeliga yozish
        ClinicNotification.objects.create(
            title=title,
            message=message,
            clinic=clinic,
            status='director'
        )

        # Real-time notification (WebSocket)
        if director:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"clinic_notifications_{director.id}",
                {
                    "type": "notification_message",
                    "title": title,
                    "message": message,
                    "timestamp": now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        # Klinikaga email yuborish
        if clinic.email:
            send_mail(
                subject=title,
                message=message,
                from_email="noreply@yourdomain.uz",
                recipient_list=[clinic.email],
                fail_silently=True,
            )

        return Response({'status': 'notification sent'})