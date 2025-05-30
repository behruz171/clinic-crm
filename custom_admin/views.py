from datetime import datetime
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets
from .models import *
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import *
from rest_framework.permissions import IsAdminUser
from app.serializers import LoginSerializer
from django.contrib.auth import authenticate
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
            subscription = ClinicSubscription.objects.get(clinic_id=clinic_id)
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