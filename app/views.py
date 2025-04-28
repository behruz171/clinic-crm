from datetime import datetime  # Fix the import for datetime
from django.shortcuts import render
from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from .models import *
from .serializers import *
from .permissions import IsClinicAdmin
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import JsonResponse
from rest_framework.views import APIView
from .models import CustomUserManager
from django.contrib.auth.decorators import login_required
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Count, Sum, Avg, Subquery, OuterRef
import pandas as pd
from django.http import HttpResponse
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import date, timedelta
from django.db.models.functions import ExtractMonth
from django.db import IntegrityError
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from .pagination import CustomPagination
import calendar


token_param = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description="JWT Token: Bearer <token>",
    type=openapi.TYPE_STRING
)

# Create your views here.

class ClinicViewSet(viewsets.ModelViewSet):
    serializer_class = ClinicSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Faqat token orqali kelayotgan foydalanuvchining clinicini qaytaradi.
        """
        user = self.request.user
        if not user.is_authenticated:
            return Clinic.objects.none()  # Agar foydalanuvchi autentifikatsiya qilinmagan bo'lsa, bo'sh queryset qaytariladi
        return Clinic.objects.filter(id=user.clinic.id)  # Foydalanuvchining clinicini qaytaradi


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['specialization', 'role', 'branch', 'status']
    search_fields = ['first_name', 'last_name']
    pagination_class = CustomPagination  # Pagination qo'shildi
    

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        return User.objects.filter(clinic=user.clinic)

    def perform_create(self, serializer):
        user_data = serializer.validated_data
        email = user_data.pop('email')  # Extract email from user_data
        random_password = get_random_string(length=8)  # Generate a random password

        # Automatically set the clinic from the authenticated user
        clinic = self.request.user.clinic

        # Ensure the username is unique
        if User.objects.filter(username=email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        # Create the user with the random password
        user = User.objects.create_user(
            username=email,  # Set username to email
            email=email,
            password=random_password,
            clinic=clinic,
            **user_data  # Pass the remaining fields
        )

        # Send the password to the user's email
        subject = "Your Account Credentials"
        message = f"Dear {user.get_full_name()},\n\nYour account has been created successfully.\n\nUsername: {email}\nPassword: {random_password}\n\nPlease log in and change your password as soon as possible."
        try:
            gmail = send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )
            print('ishlayapti', gmail)
        except Exception as e:
            print(f"Failed to send email: {e}")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset().exclude(role='director'))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Yangi foydalanuvchi qo'shish",
        manual_parameters=[token_param],
        request_body=UserSerializer,
        responses={
            201: UserSerializer,
            400: 'Bad Request',
            401: 'Unauthorized'
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Foydalanuvchi tizimga kirishi",
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Muvaffaqiyatli kirish",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'token': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            401: "Noto'g'ri login yoki parol"
        }
    )
    @action(detail=False, methods=['post'], permission_classes=[])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)
            
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'token': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                    'filial': bool(user.branch),  # True if the user has a branch
                    'user_settings': bool(user.first_name and user.last_name)  # True if the user has both first and last name
                })
            return Response(
                {'error': "Noto'g'ri login yoki parol"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SignupView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Yangi klinika va foydalanuvchi qo'shish",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'clinic_name': openapi.Schema(type=openapi.TYPE_STRING, description='Klinika nomi'),
                'clinic_phone': openapi.Schema(type=openapi.TYPE_STRING, description='Klinika telefoni'),
                'clinic_license': openapi.Schema(type=openapi.TYPE_STRING, description='Klinika litsenziyasi'),
                'user_email': openapi.Schema(type=openapi.TYPE_STRING, description='Foydalanuvchi emaili'),
            },
            required=['clinic_name', 'clinic_phone', 'clinic_license', 'user_email']
        ),
        responses={
            200: openapi.Response(
                description="Muvaffaqiyatli yaratildi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'clinic_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            ),
            400: "Bad Request"
        }
    )
    def post(self, request):
        clinic_name = request.data.get('clinic_name')
        clinic_phone = request.data.get('clinic_phone')
        clinic_license = request.data.get('clinic_license')
        user_email = request.data.get('user_email')

        user_manager = CustomUserManager()

        try:
            clinic, user = user_manager.create_clinic_and_user(
                clinic_name, clinic_phone, clinic_license, user_email
            )
        except IntegrityError as e:
            if 'unique constraint' in str(e).lower():
                if 'license_number' in str(e).lower():
                    return Response(
                        {"error": "Klinika litsenziya raqami allaqachon mavjud."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif 'email' in str(e).lower():
                    return Response(
                        {"error": "Foydalanuvchi emaili allaqachon mavjud."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(
                {"error": "Ma'lumotlarni saqlashda xatolik yuz berdi."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Xatolik yuz berdi: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return JsonResponse({
            'message': 'Clinic and user created successfully',
            'clinic_id': clinic.id,
            'user_id': user.id
        })

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

class UserNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = UserNotification.objects.all()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return UserNotification.objects.none()
        user = self.request.user
        if not user.is_authenticated:
            return UserNotification.objects.none()
        return UserNotification.objects.filter(recipient=user)

    def perform_create(self, serializer):
        sender = self.request.user
        recipient = serializer.validated_data['recipient']

        if sender.clinic != recipient.clinic:
            raise serializers.ValidationError("You can only send notifications to users within the same clinic.")

        serializer.save(sender=sender)

class CabinetViewSet(viewsets.ModelViewSet):
    queryset = Cabinet.objects.all()
    serializer_class = CabinetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'type', 'floor', 'branch']
    search_fields = ['name', 'description']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Cabinet.objects.none()
        return Cabinet.objects.filter(branch__clinic=user.clinic)

    def perform_create(self, serializer):
        cabinet = serializer.save()
        if cabinet.user.exists():
            for user in cabinet.user.all():
                if user.branch != cabinet.branch:
                    return Response({"error": "User's branch must match the cabinet's branch."}, status=status.HTTP_400_BAD_REQUEST)
        cabinet.save()

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['gender', 'status']
    search_fields = ['full_name', 'email', 'phone_number', 'location']
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        branch_id = self.kwargs.get('branch_id')  # Get branch_id from the URL
        queryset = Customer.objects.filter(branch__clinic=user.clinic)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save()
    
    def list(self, request, *args, **kwargs):
        """
        Returns simplified customer data for the list view.
        """
        queryset = self.get_queryset().values(
            'id',
            'full_name',  # Ism
            'age',        # Yosh
            'gender',     # Jins
            'phone_number',  # Telefon
            'status',     # Holat
            'branch',
            # 'updated_at',  # Oxirgi tashrif
        ).annotate(
            diagnosis=Subquery(  # Oxirgi uchrashuvdagi tashxis
                Meeting.objects.filter(customer=OuterRef('id'))
                .order_by('-date')  # Eng oxirgi uchrashuvni olish
                .values('diognosis')[:1]  # Faqat tashxisni qaytarish
            ),
            doctor=Subquery(  # Oxirgi uchrashuvdagi shifokor
                Meeting.objects.filter(customer=OuterRef('id'))
                .order_by('-date')  # Eng oxirgi uchrashuvni olish
                .values('doctor__first_name')[:1]  # Faqat shifokor ismini qaytarish
            ),
            updated_at=Subquery(  # Oxirgi uchrashuv sanasi
                Meeting.objects.filter(customer=OuterRef('id'))
                .order_by('-date')  # Eng oxirgi uchrashuvni olish
                .values('date')[:1]  # Faqat bitta qiymatni qaytarish
            )
        ).distinct()

        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(page)

        return Response(list(queryset))

    def retrieve(self, request, *args, **kwargs):
        """
        Returns detailed customer data for a single customer.
        """
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='export/pdf')
    def export_all_customers_pdf(self, request):
        """
        Exports all customers to a PDF file.
        """
        customers = self.get_queryset()
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 40, "Barcha mijozlar ro'yxati")
        p.setFont("Helvetica", 12)
        y = height - 60

        for customer in customers:
            p.drawString(30, y, f"Ism: {customer.full_name}")
            y -= 20
            p.drawString(30, y, f"Yosh: {customer.age}")
            y -= 20
            p.drawString(30, y, f"Jins: {customer.get_gender_display()}")
            y -= 20
            p.drawString(30, y, f"Telefon: {customer.phone_number}")
            y -= 20
            p.drawString(30, y, f"Oxirgi tashrif: {customer.updated_at.strftime('%Y-%m-%d')}")
            y -= 40  # Add extra space between customers

            if y < 40:  # Check if we need to create a new page
                p.showPage()
                p.setFont("Helvetica", 12)
                y = height - 40

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=customers.pdf'
        return response

    @action(detail=False, methods=['get'], url_path='export/excel')
    def export_all_customers_excel(self, request):
        """
        Exports all customers to an Excel file.
        """
        customers = self.get_queryset()
        data = []
        for customer in customers:
            data.append({
                'Ism': customer.full_name,
                'Yosh': customer.age,
                'Jins': customer.get_gender_display(),
                'Telefon': customer.phone_number,
                'Oxirgi tashrif': customer.updated_at.strftime('%Y-%m-%d'),
                'Holat': customer.get_status_display(),
            })

        # Create a DataFrame using pandas
        df = pd.DataFrame(data)
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Customers')
        writer.close()  # Use close() instead of save()
        output.seek(0)

        # Create the HTTP response with the Excel file
        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=customers.xlsx'
        return response

    @action(detail=True, methods=['get'], url_path='export/pdf')
    def export_single_customer_pdf(self, request, pk=None):
        """
        Exports a single customer's data to a PDF file.
        """
        customer = self.get_object()
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 40, f"Mijoz ma'lumotlari: {customer.full_name}")
        p.setFont("Helvetica", 12)
        y = height - 60

        p.drawString(30, y, f"Ism: {customer.full_name}")
        y -= 20
        p.drawString(30, y, f"Yosh: {customer.age}")
        y -= 20
        p.drawString(30, y, f"Jins: {customer.get_gender_display()}")
        y -= 20
        p.drawString(30, y, f"Telefon: {customer.phone_number}")
        y -= 20
        p.drawString(30, y, f"Oxirgi tashrif: {customer.updated_at.strftime('%Y-%m-%d')}")
        y -= 20
        p.drawString(30, y, f"Holat: {customer.get_status_display()}")

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=customer_{customer.id}.pdf'
        return response

    @action(detail=True, methods=['get'], url_path='export/excel')
    def export_single_customer_excel(self, request, pk=None):
        """
        Exports a single customer's data to an Excel file.
        """
        customer = self.get_object()
        data = [{
            'Ism': customer.full_name,
            'Yosh': customer.age,
            'Jins': customer.get_gender_display(),
            'Telefon': customer.phone_number,
            'Oxirgi tashrif': customer.updated_at.strftime('%Y-%m-%d'),
            'Holat': customer.get_status_display(),
        }]

        df = pd.DataFrame(data)
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Customer')
        writer.close()  # Yangi metoddan foydalanamiz
        output.seek(0)

        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=customer_{customer.id}.xlsx'
        return response

class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'branch', 'doctor', 'customer']
    search_fields = ['comment']

    def get_queryset(self):
        user = self.request.user
        branch_id = self.kwargs.get('branch_id')
        customer_id = self.request.query_params.get('customer_id')

        queryset = Meeting.objects.filter(branch__clinic=user.clinic)

        if branch_id and branch_id != 'all-filial':
            queryset = queryset.filter(branch_id=branch_id)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset

    def perform_create(self, serializer):
        meeting = serializer.save()
        if meeting.customer.branch != meeting.branch:
            raise serializers.ValidationError("Meeting's branch must match the customer's branch.")
        if meeting.doctor.branch != meeting.branch:
            raise serializers.ValidationError("Meeting's branch must match the doctor's branch.")
        meeting.save()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def daily_meetings(self, request):
        """
        Kunlik qabullarni chiqarish.
        """
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            filter_date = date.today()

        # Kunlik qabullarni filtrlash
        meetings = self.get_queryset().filter(date__date=filter_date)
        serializer = self.get_serializer(meetings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def weekly_meetings(self, request):
        """
        Haftalik qabullarni chiqarish.
        """
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            filter_date = date.today()

        # Haftaning boshlanish va tugash sanasini hisoblash
        start_of_week = filter_date - timedelta(days=filter_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Haftalik qabullarni filtrlash
        meetings = self.get_queryset().filter(date__date__range=(start_of_week, end_of_week))
        serializer = self.get_serializer(meetings, many=True)
        return Response(serializer.data)

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['clinic']
    search_fields = ['name', 'address', 'phone_number', 'email']
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Branch.objects.none()
        return Branch.objects.filter(clinic=user.clinic)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(clinic=user.clinic)  # Automatically set the clinic from the authenticated user

class UserStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        branch_id = request.query_params.get('branch_id')
        role = request.query_params.get('role')  # Get role filter from query parameters
        status = request.query_params.get('status')  # Get status filter from query parameters
        export_format = request.query_params.get('export')  # Get export format (pdf or excel)

        if branch_id:
            branch = Branch.objects.filter(id=branch_id, clinic=clinic).first()
            if not branch:
                return Response({"error": "Branch not found or does not belong to the clinic."}, status=status.HTTP_404_NOT_FOUND)
            users = User.objects.filter(clinic=clinic, branch=branch)
        else:
            users = User.objects.filter(clinic=clinic)

        # Apply filters for role and status
        if role:
            users = users.filter(role=role)
        if status:
            users = users.filter(status=status)

        total_users = users.count()
        active_users = users.filter(status='faol').count()
        inactive_users = users.filter(status='nofaol').count()
        on_leave_users = users.filter(status='tatilda').count()
        total_salary = users.aggregate(Sum('salary'))['salary__sum'] or 0

        role_distribution = users.values('role').annotate(count=Count('role'))

        data = {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'on_leave_users': on_leave_users,
            'total_salary': total_salary,
            'role_distribution': role_distribution,
        }

        # Export data if requested
        if export_format == 'pdf':
            return self.export_pdf(users)
        elif export_format == 'excel':
            return self.export_excel(users)

        return Response(data)

    def export_pdf(self, users):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 40, "User Statistics")
        p.setFont("Helvetica", 12)
        y = height - 60

        for user in users:
            p.drawString(30, y, f"Name: {user.get_full_name()}")
            y -= 20
            p.drawString(30, y, f"Role: {user.get_role_display()}")
            y -= 20
            p.drawString(30, y, f"Status: {user.get_status_display()}")
            y -= 20
            p.drawString(30, y, f"Salary: {user.salary}")
            y -= 40  # Add extra space between users

            if y < 40:  # Check if we need to create a new page
                p.showPage()
                p.setFont("Helvetica", 12)
                y = height - 40

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=user_statistics.pdf'
        return response

    def export_excel(self, users):
        data = []
        for user in users:
            data.append({
                'Name': user.get_full_name(),
                'Role': user.get_role_display(),
                'Status': user.get_status_display(),
                'Salary': user.salary,
            })

        df = pd.DataFrame(data)
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='User Statistics')
        writer.save()
        output.seek(0)

        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=user_statistics.xlsx'
        return response

class CabinetStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        branch_id = request.query_params.get('branch_id')
        if branch_id:
            branch = Branch.objects.filter(id=branch_id, clinic=clinic).first()
            if not branch:
                return Response({"error": "Branch not found or does not belong to the clinic."}, status=status.HTTP_404_NOT_FOUND)
            cabinets = Cabinet.objects.filter(branch=branch)
        else:
            cabinets = Cabinet.objects.filter(branch__clinic=clinic)

        total_cabinets = cabinets.count()
        available_cabinets = cabinets.filter(status='available').count()
        occupied_cabinets = cabinets.filter(status='creating').count()
        repair_cabinets = cabinets.filter(status='repair').count()

        type_distribution = cabinets.values('type').annotate(count=Count('type'))

        data = {
            'total_cabinets': total_cabinets,
            'available_cabinets': available_cabinets,
            'occupied_cabinets': occupied_cabinets,
            'repair_cabinets': repair_cabinets,
            'type_distribution': type_distribution,
        }

        return Response(data)

class ExportCustomersExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        customers = Customer.objects.filter(branch__clinic=user.clinic)

        data = []
        for customer in customers:
            data.append({
                'Ism': customer.full_name,
                'Yosh': customer.age,
                'Jins': customer.get_gender_display(),
                'Telefon': customer.phone_number,
                'Oxirgi tashrif': customer.updated_at.strftime('%Y-%m-%d'),
                'Holat': customer.get_status_display(),
            })

        df = pd.DataFrame(data)
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Customers')
        writer.save()
        output.seek(0)

        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=customers.xlsx'
        return response

class ExportCustomersPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        customers = Customer.objects.filter(branch__clinic=user.clinic)

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 40, "Bemorlar Ro'yxati")
        p.setFont("Helvetica", 12)
        y = height - 60

        for customer in customers:
            p.drawString(30, y, f"Ism: {customer.full_name}")
            y -= 20
            p.drawString(30, y, f"Yosh: {customer.age}")
            y -= 20
            p.drawString(30, y, f"Jins: {customer.get_gender_display()}")
            y -= 20
            p.drawString(30, y, f"Telefon: {customer.phone_number}")
            y -= 20
            p.drawString(30, y, f"Oxirgi tashrif: {customer.updated_at.strftime('%Y-%m-%d')}")
            y -= 20
            p.drawString(30, y, f"Holat: {customer.get_status_display()}")
            y -= 40  # Add extra space between customers

            if y < 40:  # Check if we need to create a new page
                p.showPage()
                p.setFont("Helvetica", 12)
                y = height - 40

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=customers.pdf'
        return response

@login_required
def get_notifications(request):
    notifications = UserNotification.objects.filter(recipient=request.user).order_by('-timestamp')[:5]
    data = [{"title": n.title, "message": n.message, "timestamp": n.timestamp.strftime("%Y-%m-%d %H:%M:%S")} for n in notifications]
    return JsonResponse(data, safe=False)

def notifications_view(request):
    return render(request, 'index.html')

def clinic_notifications_view(request):
    return render(request, 'index2.html')

def notification_global_view(request):
    return render(request, 'index3.html')

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['type', 'floor', 'status']
    search_fields = ['description']

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def details(self, request, pk=None):
        room = self.get_object()
        customers = room.customers.all()

        customer_data = [
            {
                "full_name": customer.full_name,
                "age": customer.age,
                "gender": customer.get_gender_display(),
                "admission_date": customer.created_at.strftime('%Y-%m-%d'),
                "expected_discharge_date": customer.updated_at.strftime('%Y-%m-%d'),
                "remaining_days": max((customer.updated_at - customer.created_at).days, 0),
                "status": customer.get_status_display(),
                "notes": "Patient recovering well",  # Example notes
            }
            for customer in customers
        ]

        room_data = {
            "room_number": room.id,
            "type": room.get_type_display(),
            "floor": room.floor,
            "capacity": f"{customers.count()}/{room.capacity}",
            "daily_price": f"UZS {room.daily_price:,.2f}",
            "status": room.get_status_display(),
            "description": room.description,
            "current_customers": customer_data,
        }

        return Response(room_data)

    def perform_create(self, serializer):
        room = serializer.save()
        if room.customers.count() > room.capacity:
            raise serializers.ValidationError("The number of customers exceeds the room's capacity.")
        room.save()

    def perform_update(self, serializer):
        room = serializer.save()
        for customer in room.customers.all():
            # Check if the customer already has a history for this room
            if not RoomHistory.objects.filter(room=room, customer=customer).exists():
                RoomHistory.objects.create(
                    room=room,
                    customer=customer,
                    admission_date=customer.created_at.date(),
                    discharge_date=customer.updated_at.date(),
                    total_payment=room.daily_price * (customer.updated_at - customer.created_at).days
                )
        if room.customers.count() > room.capacity:
            raise serializers.ValidationError("The number of customers exceeds the room's capacity.")
        room.save()

class FinancialReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Get the time period from query parameters
        period = request.query_params.get('period', 'year')  # Default to 'year'
        year = int(request.query_params.get('year', datetime.now().year))
        quarter = int(request.query_params.get('quarter', 1))
        month = int(request.query_params.get('month', datetime.now().month))

        # Filter meetings (income) based on the selected period and branch
        meetings = Meeting.objects.filter(branch__clinic=clinic)
        if branch_id and branch_id != 'all-filial':
            meetings = meetings.filter(branch_id=branch_id)
        if period == 'year':
            meetings = meetings.filter(date__year=year)
        elif period == 'quarter':
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            meetings = meetings.filter(date__year=year, date__month__gte=start_month, date__month__lte=end_month)
        elif period == 'month':
            meetings = meetings.filter(date__year=year, date__month=month)

        total_income = meetings.aggregate(total=Sum('payment_amount'))['total'] or 0

        # Filter cash withdrawals (expenses) based on the selected period and branch
        withdrawals = CashWithdrawal.objects.filter(clinic=clinic)
        if branch_id and branch_id != 'all-filial':
            withdrawals = withdrawals.filter(branch_id=branch_id)
        if period == 'year':
            withdrawals = withdrawals.filter(created_at__year=year)
        elif period == 'quarter':
            withdrawals = withdrawals.filter(created_at__month__gte=start_month, created_at__month__lte=end_month)
        elif period == 'month':
            withdrawals = withdrawals.filter(created_at__month=month)

        total_expenses = withdrawals.aggregate(total=Sum('amount'))['total'] or 0

        # Calculate net profit and profitability
        net_profit = total_income - total_expenses
        profitability = (net_profit / total_income * 100) if total_income > 0 else 0

        # Generate detailed statistics
        detailed_stats = []
        if period == 'month':
            first_day_of_month = datetime(year, month, 1)
            last_day_of_month = (first_day_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            # Haftalar bo'yicha hisoblash
            current_date = first_day_of_month
            while current_date <= last_day_of_month:
                week_start = current_date
                week_end = min(week_start + timedelta(days=6), last_day_of_month)  # Haftaning oxirgi kuni yoki oy oxiri

                week_income = meetings.filter(date__date__range=(week_start, week_end)).aggregate(total=Sum('payment_amount'))['total'] or 0
                week_expenses = withdrawals.filter(created_at__date__range=(week_start, week_end)).aggregate(total=Sum('amount'))['total'] or 0

                detailed_stats.append({
                    'label': f"{week_start.strftime('%d-%b')} - {week_end.strftime('%d-%b')}",
                    'income': week_income,
                    'expenses': week_expenses
                })

                # Keyingi haftaga o'tish
                current_date = week_end + timedelta(days=1)
        elif period == 'quarter':
            for month_offset in range(3):
                current_month = start_month + month_offset
                month_income = meetings.filter(date__month=current_month).aggregate(total=Sum('payment_amount'))['total'] or 0
                month_expenses = withdrawals.filter(created_at__month=current_month).aggregate(total=Sum('amount'))['total'] or 0
                detailed_stats.append({
                    'label': f"{current_month}-oy",
                    'income': month_income,
                    'expenses': month_expenses
                })
        elif period == 'year':
            for quarter in range(1, 5):
                quarter_start_month = (quarter - 1) * 3 + 1
                quarter_end_month = quarter_start_month + 2
                quarter_income = meetings.filter(date__month__gte=quarter_start_month, date__month__lte=quarter_end_month).aggregate(total=Sum('payment_amount'))['total'] or 0
                quarter_expenses = withdrawals.filter(created_at__month__gte=quarter_start_month, created_at__month__lte=quarter_end_month).aggregate(total=Sum('amount'))['total'] or 0
                detailed_stats.append({
                    'label': f"{quarter}-chorak",
                    'income': quarter_income,
                    'expenses': quarter_expenses
                })

        data = {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'profitability': round(profitability, 2),
            'detailed_stats': detailed_stats
        }

        return Response(data)

class CashWithdrawalViewSet(viewsets.ModelViewSet):
    queryset = CashWithdrawal.objects.all()
    serializer_class = CashWithdrawalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:  # Handle unauthenticated users
            return CashWithdrawal.objects.none()
        branch_id = self.kwargs.get('branch_id')
        queryset = CashWithdrawal.objects.filter(clinic=user.clinic)
        if branch_id and branch_id != 'all-filial':
            queryset = queryset.filter(branch_id=branch_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(clinic=user.clinic)

class PatientStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Get the time period from query parameters
        period = request.query_params.get('period', 'year')  # Default to 'year'
        year = int(request.query_params.get('year', datetime.now().year))
        quarter = int(request.query_params.get('quarter', 1))
        month = int(request.query_params.get('month', datetime.now().month))

        # Filter customers based on the selected period and branch
        customers = Customer.objects.filter(branch__clinic=clinic)
        if branch_id and branch_id != 'all-filial':
            customers = customers.filter(branch_id=branch_id)
        if period == 'year':
            customers = customers.filter(created_at__year=year)
        elif period == 'quarter':
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            customers = customers.filter(created_at__year=year, created_at__month__gte=start_month, created_at__month__lte=end_month)
        elif period == 'month':
            customers = customers.filter(created_at__year=year, created_at__month=month)

        total_patients = customers.count()

        # Generate detailed statistics
        detailed_stats = []
        if period == 'month':
            for week in range(1, 5):
                week_start = datetime(year, month, (week - 1) * 7 + 1)
                week_end = datetime(year, month, min(week * 7, 28))
                week_patients = customers.filter(created_at__range=(week_start, week_end)).count()
                detailed_stats.append({
                    'label': f"{week}-hafta",
                    'patients': week_patients
                })
        elif period == 'quarter':
            for month_offset in range(3):
                current_month = start_month + month_offset
                month_patients = customers.filter(created_at__month=current_month).count()
                detailed_stats.append({
                    'label': f"{current_month}-oy",
                    'patients': month_patients
                })
        elif period == 'year':
            for quarter in range(1, 5):
                quarter_start_month = (quarter - 1) * 3 + 1
                quarter_end_month = quarter_start_month + 2
                quarter_patients = customers.filter(created_at__month__gte=quarter_start_month, created_at__month__lte=quarter_end_month).count()
                detailed_stats.append({
                    'label': f"{quarter}-chorak",
                    'patients': quarter_patients
                })

        # Calculate average weekly or monthly patients and growth rate
        avg_weekly_patients = total_patients // 4 if period == 'month' else None
        avg_monthly_patients = total_patients // 3 if period == 'quarter' else None
        growth_rate = ((detailed_stats[-1]['patients'] - detailed_stats[0]['patients']) / detailed_stats[0]['patients'] * 100) if len(detailed_stats) > 1 and detailed_stats[0]['patients'] > 0 else 0

        data = {
            'total_patients': total_patients,
            'avg_weekly_patients': avg_weekly_patients,
            'avg_monthly_patients': avg_monthly_patients,
            'growth_rate': round(growth_rate, 2),
            'detailed_stats': detailed_stats
        }

        return Response(data)


class DoctorStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Get the time period from query parameters
        period = request.query_params.get('period', 'year')  # Default to 'year'
        year = int(request.query_params.get('year', datetime.now().year))
        quarter = int(request.query_params.get('quarter', 1))
        month = int(request.query_params.get('month', datetime.now().month))

        # Filter doctors and their meetings based on the selected period and branch
        doctors = User.objects.filter(clinic=clinic, role='doctor')
        if branch_id and branch_id != 'all-filial':
            doctors = doctors.filter(branch_id=branch_id)

        doctor_stats = []
        for doctor in doctors:
            meetings = Meeting.objects.filter(doctor=doctor)
            if period == 'year':
                meetings = meetings.filter(date__year=year)
            elif period == 'quarter':
                start_month = (quarter - 1) * 3 + 1
                end_month = start_month + 2
                meetings = meetings.filter(date__year=year, date__month__gte=start_month, date__month__lte=end_month)
            elif period == 'month':
                meetings = meetings.filter(date__year=year, date__month=month)

            total_patients = meetings.count()
            total_income = meetings.aggregate(total=Sum('payment_amount'))['total'] or 0

            doctor_stats.append({
                'doctor_name': doctor.get_full_name(),
                'total_patients': total_patients,
                'total_income': total_income
            })

        # Find the most effective doctor
        most_effective_doctor = max(doctor_stats, key=lambda x: x['total_patients'], default=None)

        data = {
            'doctor_stats': doctor_stats,
            'most_effective_doctor': most_effective_doctor
        }

        return Response(data)

class FinancialMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all-filial':
            meetings = Meeting.objects.filter(branch__clinic=clinic)
            withdrawals = CashWithdrawal.objects.filter(clinic=clinic)
        else:
            meetings = Meeting.objects.filter(branch_id=branch_id, branch__clinic=clinic)
            withdrawals = CashWithdrawal.objects.filter(branch_id=branch_id, clinic=clinic)

        # Aggregate income and expenses by month
        income_data = meetings.annotate(
            month=ExtractMonth('date')
        ).values('month').annotate(
            total_income=Sum('payment_amount')
        ).order_by('month')

        expense_data = withdrawals.annotate(
            month=ExtractMonth('created_at')
        ).values('month').annotate(
            total_expenses=Sum('amount')
        ).order_by('month')

        # Combine income and expense data into a single structure
        monthly_data = []
        months = {1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
                  7: "Iyul", 8: "Avgust", 9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"}

        for month in range(1, 13):
            income = next((item['total_income'] for item in income_data if item['month'] == month), 0)
            expenses = next((item['total_expenses'] for item in expense_data if item['month'] == month), 0)
            monthly_data.append({
                'month': months[month],
                'income': income,
                'expenses': expenses
            })

        return Response({
            'monthly_data': monthly_data
        })


class DoctorEfficiencyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request,branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all-filial':
            doctors = clinic.users.filter(role='doctor')  # related_name='users' ishlatilmoqda
        else:
            doctors = clinic.users.filter(role='doctor', branch_id=branch_id)

        # Count patients per doctor and calculate average patients
        doctor_data = doctors.annotate(
            patient_count=Count('meeting__customer')
        ).values('id', 'first_name', 'last_name', 'patient_count')

        total_patients = sum(d['patient_count'] for d in doctor_data)
        avg_patients_per_doctor = total_patients / len(doctor_data) if doctor_data else 0

        return Response({
            'total_patients': total_patients,
            'avg_patients_per_doctor': round(avg_patients_per_doctor, 2),
            'doctor_data': list(doctor_data)
        })


class CustomersByDepartmentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all-filial':
            customers = Customer.objects.filter(branch__clinic=clinic)
        else:
            customers = Customer.objects.filter(branch_id=branch_id, clinic=clinic)
            

        # Count customers by specialization
        department_data = customers.values(
            'doctor__specialization'
        ).annotate(customer_count=Count('id'))

        # total_customers = sum(d['customer_count'] for d in department_data)
        total_customers = customers.count()

        return Response({
            'total_customers': total_customers,
            'department_data': list(department_data)
        })


class MonthlyCustomerDynamicsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all-filial':
            meetings = Meeting.objects.filter(branch__clinic=clinic)
        else:
            meetings = Meeting.objects.filter(branch_id=branch_id, branch__clinic=clinic)

        # Count customers by month
        monthly_data = meetings.values('date__month').annotate(
            customer_count=Count('customer')
        )

        # Calculate growth rate
        customer_counts = [d['customer_count'] for d in monthly_data]
        growth_rate = ((customer_counts[-1] - customer_counts[0]) / customer_counts[0] * 100) if len(customer_counts) > 1 and customer_counts[0] > 0 else 0

        return Response({
            'monthly_data': list(monthly_data),
            'growth_rate': round(growth_rate, 2)
        })


class DepartmentEfficiencyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all-filial':
            departments = Branch.objects.filter(clinic=clinic)
        else:
            departments = Branch.objects.filter(id=branch_id, clinic=clinic)

        # Count customers and calculate satisfaction per department
        department_data = departments.annotate(
            customer_count=Count('customer'),
            avg_satisfaction=Avg('customer__status')  # Example satisfaction metric
        ).values('id', 'name', 'customer_count', 'avg_satisfaction')

        return Response({
            'department_data': list(department_data)
        })


class TodaysAppointmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Get today's appointments
        today = date.today()


        if branch_id == 'all-filial':
            appointments = Meeting.objects.filter(branch__clinic=clinic, date__date=today)
        else:
            appointments = Meeting.objects.filter(branch_id=branch_id, branch__clinic=clinic, date__date=today)
        
        appointments = appointments.values(
            'customer__full_name', 'date', 'doctor__first_name', 'doctor__last_name', 'branch__name', 'status'
        )

        total_appointments = appointments.count()

        return Response({
            'total_appointments': total_appointments,
            'appointments': list(appointments)
        })


class NewStaffView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Get recently added staff using date_joined
        recent_staff = User.objects.filter(clinic=clinic).order_by('-date_joined')[:5].values(
            'first_name', 'last_name', 'role', 'branch__name', 'date_joined'
        )

        return Response({
            'recent_staff': list(recent_staff)
        })

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'priority', 'assignee']
    search_fields = ['title', 'description']

    def get_queryset(self):
        user = self.request.user
        branch_id = self.request.query_params.get('branch')  # Query parametrlardan branch ID

        # Agar foydalanuvchi director yoki admin bo'lsa, barcha vazifalarni ko'radi
        if user.role in ['director', 'admin']:
            queryset = Task.objects.filter(created_by__clinic=user.clinic)
            if branch_id:  # Agar branch ID berilgan bo'lsa, filtr qo'llanadi
                queryset = queryset.filter(assignee__branch_id=branch_id)
            return queryset

        # Agar foydalanuvchi assignee bo'lsa, faqat o'z vazifalarini ko'radi
        queryset = Task.objects.filter(assignee=user, created_by__clinic=user.clinic)
        if branch_id:  # Agar branch ID berilgan bo'lsa, filtr qo'llanadi
            queryset = queryset.filter(assignee__branch_id=branch_id)
        return queryset

        # Default bo'sh queryset qaytaradi
        # return Task.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def daily_tasks(self, request):
        # Get the date from query parameters, default to today's date
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            filter_date = date.today()

        # Filter tasks based on the provided date
        tasks = self.get_queryset().filter(
            start_date__lte=filter_date,
            end_date__gte=filter_date
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def weekly_tasks(self, request):
        # Get the date from query parameters, default to today's date
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            filter_date = date.today()

        # Calculate the start and end of the week
        start_of_week = filter_date - timedelta(days=filter_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        # Filter tasks within the week range
        tasks = self.get_queryset().filter(
            start_date__lte=end_of_week,
            end_date__gte=start_of_week
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def monthly_tasks(self, request):
        # Get the date from query parameters, default to today's date
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            filter_date = date.today()

        # Calculate the start and end of the month
        start_of_month = filter_date.replace(day=1)
        next_month = (start_of_month.month % 12) + 1
        end_of_month = (start_of_month.replace(month=next_month, day=1) - timedelta(days=1)) if next_month != 1 else start_of_month.replace(year=start_of_month.year + 1, month=1, day=1) - timedelta(days=1)

        # Filter tasks within the month range
        tasks = self.get_queryset().filter(
            start_date__lte=end_of_month,
            end_date__gte=start_of_month
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def yearly_tasks(self, request):
        # Get the date from query parameters, default to today's date
        date_param = request.query_params.get('date', None)
        if date_param:
            try:
                filter_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            filter_date = date.today()

        # Calculate the start and end of the year
        start_of_year = filter_date.replace(month=1, day=1)
        end_of_year = filter_date.replace(month=12, day=31)

        # Filter tasks within the year range
        tasks = self.get_queryset().filter(
            start_date__lte=end_of_year,
            end_date__gte=start_of_year
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

class ClinicLogoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.clinic:
            return Response({"error": "You are not associated with any clinic."}, status=status.HTTP_403_FORBIDDEN)

        clinic = user.clinic
        serializer = ClinicLogoSerializer(clinic)
        return Response(serializer.data)


class RoomHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Xonani tekshirish
        room = Room.objects.filter(id=room_id, branch__clinic=clinic).first()
        if not room:
            return Response({"error": "Room not found or you don't have access to it."}, status=404)

        # Xonadagi tarixiy ma'lumotlarni olish
        history = RoomHistory.objects.filter(room=room).values(
            'customer__full_name', 'admission_date', 'discharge_date', 
            'diagnosis', 'total_payment', 'doctor__first_name', 'doctor__last_name'
        )

        return Response({
            "room_number": room.id,
            "history": list(history)
        })