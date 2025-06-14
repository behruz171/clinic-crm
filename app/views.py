from datetime import datetime  # Fix the import for datetime
from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from .models import *
from .serializers import *
from .permissions import *
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import JsonResponse
from rest_framework.views import APIView
from .models import CustomUserManager
from django.contrib.auth.decorators import login_required
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Count, Sum, Avg, Subquery, OuterRef, Q
import pandas as pd
from django.http import HttpResponse
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image
from datetime import date, timedelta
from django.db.models.functions import ExtractMonth
from django.db import IntegrityError
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.conf import settings
from .pagination import CustomPagination
import calendar
from .tasks import *
from decimal import Decimal
import qrcode
import pyfiglet
import io


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
    

    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        if Clinic.objects.filter(email=email).exists():
            raise ValidationError({"email": "Bu email bilan klinika allaqachon mavjud."})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clinic = serializer.save()
        random_password = get_random_string(length=8)  # Tasodifiy parol yaratish
        director = User.objects.create_user(
            username=email,
            email=email,
            password=random_password,
            clinic=clinic,
            role='director',
            first_name='Director',
            last_name='',
            phone_number='',
            status='faol'
        )
        subject = "Klinika uchun direktor yaratildi"
        message = (
            f"Hurmatli foydalanuvchi,\n\n"
            f"Sizning klinikangiz muvaffaqiyatli yaratildi.\n"
            f"Klinika nomi: {clinic.name}\n"
            f"Username: {email}\n"
            f"Parol: {random_password}\n\n"
            f"Sistemaga kirgach , parolni o'zgartirishingiz mumkin"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )
        except Exception as e:
            return Response({"error": f"Klinika yaratildi, lekin email yuborishda xatolik: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """
        Yaratilgan klinikani saqlash.
        """
        serializer.save()

    # delete clinic
    def destroy(self, request, *args, **kwargs):
        user = request.user
        # only superuser can delete
        if not user.is_superuser:
            return Response({"error": "Sizda klinikani o'chirish huquqi yo'q."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    # permission_classes = [IsAuthenticated]
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
        user_data = serializer.validated_data.copy()
        email = user_data.pop('email')  # Extract email from user_data
        random_password = get_random_string(length=8)  # Generate a random password
        # random_password = "qwerty"

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
        # try:
        gmail = send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )
            # print('ishlayapti', gmail)
        # except Exception as e:
        #     print(f"Failed to send email: {e}")
        # send_user_credentials_email.delay(subject, message, email)


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
                if user.status != 'faol':
                    return Response(
                        {'error': "Foydalanuvchi statusi faol emas."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                if getattr(user, 'role', None) in ['nurse', 'doctor', 'admin', 'receptionist']:
                    now = datetime.now()
                    day_of_week = now.strftime('%A').lower()
                    try:
                        schedule = NurseSchedule.objects.get(user=user, day=day_of_week)
                    except NurseSchedule.DoesNotExist:
                        return Response(
                            {'error': "Bugungi kun uchun ish jadvali topilmadi."},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    if not schedule.is_working:
                        return Response(
                            {'error': "Siz bugun ishlamaysiz."},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    now_time = now.time()
                    if not (schedule.start_time <= now_time <= schedule.end_time):
                        return Response(
                            {'error': "Sizning ish vaqtingiz emas."},
                            status=status.HTTP_403_FORBIDDEN
                        )
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

    def get_serializer_context(self):
        """
        Serializer kontekstiga foydalanuvchini qo'shish.
        """
        return {'request': self.request}


class ClinicNotificationViewSet(viewsets.ModelViewSet):
    """
    ClinicNotification bilan ishlash uchun ViewSet.
    """
    queryset = ClinicNotification.objects.all().order_by('-created_at')
    serializer_class = ClinicNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Foydalanuvchi roliga qarab xabarlarni filtrlash
        if user.role == 'doctor':
            return ClinicNotification.objects.filter(status='doctor', clinic=user.clinic)
        elif user.role == 'admin':
            return ClinicNotification.objects.filter(status__in=['admin', 'admin_director'], clinic=user.clinic)
        elif user.role == 'director':
            return ClinicNotification.objects.filter(status__in=['director', 'admin_director'], clinic=user.clinic)
        else:
            return ClinicNotification.objects.none()

    def get_serializer_context(self):
        """
        Serializer kontekstiga foydalanuvchini qo'shish.
        """
        return {'request': self.request}
    
    # def list(self, request, *args, **kwargs):
    #     user = request.user

    #     # Foydalanuvchiga tegishli barcha bildirishnomalar (filtered by clinic or branch)
    #     all_clinic_notifications = self.get_queryset()

    #     # O'qilmagan bildirishnomalarni aniqlash (read_status mavjud emas yoki is_read=False)
    #     read_status_notifications = ClinicNotificationReadStatus.objects.filter(user=user).values_list('clinic_notification_id', flat=True)
    #     unread_count = all_clinic_notifications.filter(
    #         Q(id__in=read_status_notifications, read_statuses__is_read=False) |
    #         Q(~Q(id__in=read_status_notifications))
    #     ).distinct().count()

    #     # Pagination qo‘llash
    #     page = self.paginate_queryset(all_clinic_notifications)
    #     if page is not None:
    #         all_serializer = self.get_serializer(page, many=True)
    #         return Response({
    #             'count': self.paginator.page.paginator.count,
    #             'next': self.paginator.get_next_link(),
    #             'previous': self.paginator.get_previous_link(),
    #             'all_clinic_notifications': all_serializer.data,
    #             'unread_count': unread_count,
    #         })

    #     # Agar pagination yo‘q bo‘lsa
    #     all_serializer = self.get_serializer(all_clinic_notifications, many=True)
    #     return Response({
    #         'all_clinic_notifications': all_serializer.data,
    #         'unread_count': unread_count
    #     })



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
        return Cabinet.objects.filter(branch__clinic=user.clinic).order_by('-id')

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
    search_fields = ['full_name', 'passport_id', 'phone_number', 'location']
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        branch_id = self.request.query_params.get('branch_id')  # Get branch_id from the URL
        queryset = Customer.objects.filter(branch__clinic=user.clinic).order_by('-id')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save()
    
    def list(self, request, *args, **kwargs):
        """
        Returns simplified customer data for the list view.
        """
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.values(
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
    
    def _draw_customer_info(self, p, customer, y):
        """Yagona mijoz blokini PDF sahifasiga chizish."""
        p.drawString(30, y, f"Ism: {customer.full_name}"); y -= 20
        p.drawString(30, y, f"Yosh: {customer.age}"); y -= 20
        p.drawString(30, y, f"Jins: {customer.get_gender_display()}"); y -= 20
        p.drawString(30, y, f"Telefon: {customer.phone_number}"); y -= 20
        p.drawString(30, y, f"Oxirgi tashrif: {customer.updated_at.strftime('%Y-%m-%d')}"); y -= 20
        if hasattr(customer, 'status'):
            p.drawString(30, y, f"Holat: {customer.get_status_display()}"); y -= 20
        return y - 20

    @action(detail=False, methods=['get'], url_path='export/pdf')
    def export_all_customers_pdf(self, request):
        """📄 Barcha mijozlarni chiroyli PDF faylga eksport qiladi."""
        customers = self.get_queryset()
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 80

        # Sarlavha
        p.setFillColor(colors.darkblue)
        p.setFont("Helvetica-Bold", 20)
        p.drawCentredString(width / 2, y, "📋 Barcha Mijozlar Ro'yxati")
        y -= 40

        for i, customer in enumerate(customers, 1):
            if y < 150:  # yangi sahifa
                p.showPage()
                y = height - 80
                p.setFont("Helvetica-Bold", 20)
                p.setFillColor(colors.darkblue)
                p.drawCentredString(width / 2, y, "📋 Barcha Mijozlar Ro'yxati")
                y -= 40

            # Mijoz bloki foni
            p.setFillColorRGB(0.94, 0.94, 1)  # Yengil ko‘k fon
            p.roundRect(40, y - 90, width - 50, 100, radius=8, fill=True, stroke=0)

            # Mijoz ma'lumotlari
            p.setFillColor(colors.black)
            p.setFont("Helvetica-Bold", 14)
            p.drawString(55, y - 20, f"👤 {i}. {customer.full_name}")

            p.setFont("Helvetica", 12)
            p.drawString(60, y - 40, f"🎂 Yosh: {customer.age}")
            p.drawString(220, y - 40, f"⚧ Jins: {customer.get_gender_display()}")

            p.drawString(60, y - 60, f"📞 Tel: {customer.phone_number}")
            p.drawString(220, y - 60, f"🗓 Oxirgi tashrif: {customer.updated_at.strftime('%Y-%m-%d')}")

            if hasattr(customer, 'status'):
                p.drawString(60, y - 80, f"📌 Holat: {customer.get_status_display()}")

            y -= 110  # keyingi blokga joy tashlash

        p.showPage()
        p.save()
        buffer.seek(0)

        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename="customers_chiroyli.pdf"'
        })

    @action(detail=False, methods=['get'], url_path='export/excel')
    def export_all_customers_excel(self, request):
        """📊 Barcha mijozlarni Excel faylga eksport qilish."""
        customers = self.get_queryset()
        data = [{
            'Ism': c.full_name,
            'Yosh': c.age,
            'Jins': c.get_gender_display(),
            'Telefon': c.phone_number,
            'Oxirgi tashrif': c.updated_at.strftime('%Y-%m-%d'),
            'Holat': c.get_status_display() if hasattr(c, 'status') else ''
        } for c in customers]

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Mijozlar')
            workbook = writer.book
            worksheet = writer.sheets['Mijozlar']
            for idx, col in enumerate(df.columns):
                column_len = df[col].astype(str).map(len).max()
                worksheet.set_column(idx, idx, column_len + 5)

        output.seek(0)
        return HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
            'Content-Disposition': 'attachment; filename="customers.xlsx"'
        })

    @action(detail=True, methods=['get'], url_path='export/pdf')
    def export_single_customer_pdf(self, request, pk=None):
        """📄 Bitta mijozni chiroyli PDF faylga eksport qiladi (kattaroq shrift bilan)."""
        customer = self.get_object()
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        y = height - 80

        # 📋 Sarlavha
        p.setFillColor(colors.darkblue)
        p.setFont("Helvetica-Bold", 24)
        p.drawCentredString(width / 2, y, "👤 Mijoz Ma'lumotlari")
        y -= 60

        # 📦 Kartochka foni
        p.setFillColorRGB(0.94, 0.94, 1)  # Yengil ko‘k fon
        box_height = 170
        p.roundRect(50, y - box_height, width - 100, box_height, radius=10, fill=True, stroke=0)

        # 📝 Ma'lumotlar
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(70, y - 25, f"📛 Ism: {customer.full_name}")

        p.setFont("Helvetica", 14)
        p.drawString(70, y - 55, f"🎂 Yosh: {customer.age}")
        p.drawString(300, y - 55, f"⚧ Jins: {customer.get_gender_display()}")

        p.drawString(70, y - 85, f"📞 Tel: {customer.phone_number}")
        p.drawString(300, y - 85, f"🗓 Oxirgi tashrif: {customer.updated_at.strftime('%Y-%m-%d')}")

        if hasattr(customer, 'status'):
            p.drawString(70, y - 115, f"📌 Holat: {customer.get_status_display()}")

        # Oxiri
        p.showPage()
        p.save()
        buffer.seek(0)

        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': f'attachment; filename="customer_{customer.id}.pdf"'
        })

    @action(detail=True, methods=['get'], url_path='export/excel')
    def export_single_customer_excel(self, request, pk=None):
        """📊 Bitta mijozni Excel faylga eksport qilish."""
        customer = self.get_object()
        df = pd.DataFrame([{
            'Ism': customer.full_name,
            'Yosh': customer.age,
            'Jins': customer.get_gender_display(),
            'Telefon': customer.phone_number,
            'Oxirgi tashrif': customer.updated_at.strftime('%Y-%m-%d'),
            'Holat': customer.get_status_display() if hasattr(customer, 'status') else ''
        }])

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Mijoz')
            worksheet = writer.sheets['Mijoz']
            for idx, col in enumerate(df.columns):
                column_len = df[col].astype(str).map(len).max()
                worksheet.set_column(idx, idx, column_len + 5)

        output.seek(0)
        return HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
            'Content-Disposition': f'attachment; filename="customer_{customer.id}.xlsx"'
        })

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

        queryset = Meeting.objects.filter(branch__clinic=user.clinic).order_by('-id')

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
    
    @action(detail=True, methods=['get'], url_path='talon')
    def talon(self, request, pk=None):
        meeting = self.get_object()
        clinic_id = meeting.branch.clinic.id if meeting.branch and meeting.branch.clinic else ""
        meeting_id = meeting.id

        # Qo'shimcha ma'lumotlar
        clinic_name = meeting.branch.clinic.name if meeting.branch and meeting.branch.clinic else ""
        patient_name = meeting.customer.full_name if meeting.customer else ""
        passport_id = meeting.customer.passport_id if meeting.customer else ""
        room_name = meeting.room.name if meeting.room else ""
        doctor_name = meeting.doctor.get_full_name() if meeting.doctor else ""
        date_str = meeting.date.strftime('%Y-%m-%d') if meeting.date else ""
        time_str = meeting.date.strftime('%H:%M') if meeting.date else ""

        # QR-link
        qr_link = f"https://dentical.uz/meeting/{clinic_id}/{meeting_id}/"

        # QR-code ASCII
        qr = qrcode.QRCode(border=1)
        qr.add_data(qr_link)
        qr.make(fit=True)
        qr_ascii = io.StringIO()
        qr.print_ascii(out=qr_ascii, invert=True)
        qr_ascii_str = qr_ascii.getvalue()

        # Centering helper
        def center(text, width=40):
            return text.center(width)

        # QR ASCII ni o‘rtaga chiqarish
        qr_ascii_centered = "\n".join([center(line, 40) for line in qr_ascii_str.splitlines()])

        # Vaqtni katta fontda (ascii-art) chiqarish
        ascii_time = pyfiglet.figlet_format(time_str, font='big')
        ascii_time_centered = "\n".join([center(line, 40) for line in ascii_time.splitlines()])

        # TXT fayl matni
        txt_content = (
            "\n"
            + center("==== QABUL TALONI ====") + "\n\n"
            + center(f"PASSPORT: {passport_id}") + "\n"
            + center(f"XONA: {room_name}") + "\n"
            + center(f"SANA: {date_str}") + "\n\n"
            + ascii_time_centered + "\n"
            + "-"*40 + "\n"
            + center(f"KLINIKA: {clinic_name}") + "\n"
            + center(f"BEMOR: {patient_name}") + "\n"
            + center(f"SHIFOKOR: {doctor_name}") + "\n"
            + center(f"MEETING ID: {meeting_id}") + "\n"
            + center(f"QR-LINK: {qr_link}") + "\n"
            + "-"*40 + "\n"
            + center("QR-KOD:") + "\n"
            + qr_ascii_centered
            + "\n" + center("Tashrif uchun rahmat!") + "\n"
        )

        response = HttpResponse(txt_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename=talon_{meeting_id}.txt'
        return response
    
    @action(detail=True, methods=['get'], url_path='export/pdf')
    def export_single_pdf(self, request, pk=None):
        import os
        meeting = self.get_object()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="meeting_{meeting.id}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        bold = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12)
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=12)
        header = ParagraphStyle('Header', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, alignment=1, textColor=colors.darkblue)

        # Klinikani logosi (agar mavjud bo‘lsa)
        clinic = meeting.branch.clinic if meeting.branch and meeting.branch.clinic else None
        logo_img = None
        if clinic and getattr(clinic, 'logo', None):
            logo_path = clinic.logo.path if hasattr(clinic.logo, 'path') else None
            if logo_path and os.path.exists(logo_path):
                logo_img = Image(logo_path, width=80, height=80)
                logo_img.hAlign = 'LEFT'

        # Header va logo bitta qatorda chiqishi uchun Table ishlatamiz
        header_row = []
        if logo_img:
            header_row.append(logo_img)
        else:
            header_row.append(Spacer(1, 80))
        header_row.append(Paragraph("🟦🟦 QABUL MA'LUMOTI", header))

        header_table = Table([header_row], colWidths=[90, 350])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 12))

        # Ma’lumotlar
        info_fields = [
            ("Klinika", meeting.branch.clinic.name),
            ("Bemor", meeting.customer.full_name if meeting.customer else ""),
            ("Passport ID", meeting.customer.passport_id if meeting.customer else ""),
            ("Xona", meeting.room.name if meeting.room else ""),
            ("Sana", meeting.date.strftime('%Y-%m-%d') if meeting.date else ""),
            ("Vaqt", meeting.date.strftime('%H:%M') if meeting.date else ""),
            ("Shifokor", meeting.doctor.get_full_name() if meeting.doctor else ""),
            ("Status", f"<font color='darkred'><b>{meeting.get_status_display() if hasattr(meeting, 'get_status_display') else meeting.status}</b></font>"),
            ("Izoh", meeting.comment or "")
        ]

        for label, value in info_fields:
            if label == "Status":
                value_paragraph = Paragraph(value, normal)
            else:
                value_paragraph = Paragraph(f"<b>{value}</b>", normal)
            row = Table([
                [Paragraph(f"<b>{label}:</b>", bold), value_paragraph]
            ], colWidths=[70*mm, 90*mm])
            row.setStyle(TableStyle([
                ('LINEBELOW', (0, 0), (-1, 0), 0.3, colors.black),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ]))
            elements.append(row)

        elements.append(Spacer(1, 25))

        # Dental services table
        dental_services = meeting.dental_services.all()
        total_amount = 0

        if dental_services:
            elements.append(Paragraph("<b>DENTAL XIZMATLAR:</b>", bold))
            elements.append(Spacer(1, 8))

            ds_table_data = [
                [
                    Paragraph("<b>Xizmat nomi</b>", bold),
                    Paragraph("<b>Tavsif</b>", bold),
                    Paragraph("<b>Narx</b>", bold),
                    Paragraph("<b>Tish raqami</b>", bold)
                ]
            ]

            for ds in dental_services:
                ds_table_data.append([
                    ds.name,
                    ds.description,
                    f"{ds.amount:.2f}",
                    str(ds.teeth_number)
                ])
                total_amount += float(ds.amount or 0)

            ds_table = Table(ds_table_data, colWidths=[50*mm, 50*mm, 25*mm, 25*mm])
            ds_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BOX', (0, 0), (-1, -1), 1, colors.grey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(ds_table)

            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"<b>Umumiy summa:</b> {total_amount:.2f} so'm", bold))

        elements.append(Spacer(1, 30))  # Pastdan joy tashlash
        doc.build(elements)
        return response

class MeetingPublicView(APIView):
    permission_classes = []  # Ochiq API

    def get(self, request, clinic_id, meeting_id):
        meeting = get_object_or_404(
            Meeting.objects.select_related(
                'customer', 'doctor', 'branch', 'room', 'branch__clinic'
            ).prefetch_related('dental_services'),
            id=meeting_id,
            branch__clinic_id=clinic_id
        )
        clinic = meeting.branch.clinic
        customer = meeting.customer
        doctor = meeting.doctor
        room = meeting.room

        # Clinic logo url
        logo_url = request.build_absolute_uri(clinic.logo.url) if getattr(clinic, 'logo', None) else None

        # Xona (Cabinet) ma'lumotlari
        room_data = None
        if room:
            room_data = {
                "id": room.id,
                "name": room.name,
                "floor": room.floor,
                "status": room.status,
                "type": room.type,
                "description": room.description,
            }

        data = {
            "meeting": {
                "id": meeting.id,
                "date": meeting.date,
                "status": meeting.status,
                "comment": meeting.comment,
                "room": room_data,
                "branch": meeting.branch.name if meeting.branch else None,
                "dental_services": [
                    {
                        "name": ds.name,
                        "description": ds.description,
                        "amount": ds.amount,
                        "teeth_number": ds.teeth_number
                    } for ds in meeting.dental_services.all()
                ]
            },
            "clinic": {
                "id": clinic.id,
                "name": clinic.name,
                "logo": logo_url,
                "phone": clinic.phone_number if hasattr(clinic, 'phone_number') else None,
                "address": clinic.address if hasattr(clinic, 'address') else None
            },
            "customer": {
                "id": customer.id if customer else None,
                "full_name": customer.full_name if customer else None,
                "passport_id": customer.passport_id if customer else None,
                "phone_number": customer.phone_number if customer else None,
                "gender": customer.get_gender_display() if customer and hasattr(customer, 'get_gender_display') else None,
            },
            "doctor": {
                "id": doctor.id if doctor else None,
                "full_name": doctor.get_full_name() if doctor else None,
                "specialization": doctor.specialization if doctor else None,
                "phone_number": doctor.phone_number if doctor else None,
            }
        }
        return Response(data)
    

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
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        branch_id = request.query_params.get('branch_id')
        role = request.query_params.get('role')
        status = request.query_params.get('status')
        export_format = request.query_params.get('export')

        if branch_id:
            branch = Branch.objects.filter(id=branch_id, clinic=clinic).first()
            if not branch:
                return Response({"error": "Branch not found or does not belong to the clinic."}, status=status.HTTP_404_NOT_FOUND)
            users = User.objects.filter(clinic=clinic, branch=branch)
        else:
            users = User.objects.filter(clinic=clinic)

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

        # KPI va jami to‘lovlarni DentalService orqali hisoblash
        doctor_kpi_stats = []
        for doctor in users.filter(role='doctor'):
            meetings = Meeting.objects.filter(doctor=doctor)
            # Har bir meeting uchun dental_services dagi amount lar yig‘indisi
            total_payment = 0
            for meeting in meetings:
                total_payment += sum(ds.amount for ds in meeting.dental_services.all())
            kpi_percent = doctor.kpi or Decimal(0)
            kpi_amount = total_payment * (kpi_percent / Decimal('100'))
            doctor_kpi_stats.append({
                "doctor_id": doctor.id,
                "doctor_name": doctor.get_full_name(),
                "kpi_percent": float(kpi_percent),
                "total_payment": float(total_payment),
                "kpi_amount": float(kpi_amount),
            })

        data = {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'on_leave_users': on_leave_users,
            'total_salary': total_salary,
            'role_distribution': role_distribution,
            'doctor_kpi_stats': doctor_kpi_stats,
        }

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

        period = request.query_params.get('period', 'year')
        year = int(request.query_params.get('year', datetime.now().year))
        quarter = int(request.query_params.get('quarter', 1))
        month = int(request.query_params.get('month', datetime.now().month))

        meetings = Meeting.objects.filter(branch__clinic=clinic, status='finished')
        if branch_id and branch_id != 'all':
            meetings = meetings.filter(branch_id=branch_id)
        if period == 'year':
            meetings = meetings.filter(date__year=year)
        elif period == 'quarter':
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            meetings = meetings.filter(date__year=year, date__month__gte=start_month, date__month__lte=end_month)
        elif period == 'month':
            meetings = meetings.filter(date__year=year, date__month=month)

        # Jami tushum: barcha meeting uchun dental_services.amount yig'indisi
        total_income = 0
        for meeting in meetings:
            total_income += sum(ds.amount for ds in meeting.dental_services.all())
        print(meetings)
        withdrawals = CashWithdrawal.objects.filter(clinic=clinic)
        if branch_id and branch_id != 'all':
            withdrawals = withdrawals.filter(branch_id=branch_id)
        if period == 'year':
            withdrawals = withdrawals.filter(created_at__year=year)
        elif period == 'quarter':
            withdrawals = withdrawals.filter(created_at__month__gte=start_month, created_at__month__lte=end_month)
        elif period == 'month':
            withdrawals = withdrawals.filter(created_at__month=month)

        total_expenses = withdrawals.aggregate(total=Sum('amount'))['total'] or 0

        net_profit = total_income - total_expenses
        profitability = (net_profit / total_income * 100) if total_income > 0 else 0

        # Generate detailed statistics
        detailed_stats = []
        if period == 'month':
            first_day_of_month = datetime(year, month, 1)
            last_day_of_month = (first_day_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

            current_date = first_day_of_month
            while current_date <= last_day_of_month:
                week_start = current_date
                week_end = min(week_start + timedelta(days=6), last_day_of_month)

                week_meetings = meetings.filter(date__date__range=(week_start, week_end))
                week_income = sum(sum(ds.amount for ds in m.dental_services.all()) for m in week_meetings)
                week_expenses = withdrawals.filter(created_at__date__range=(week_start, week_end)).aggregate(total=Sum('amount'))['total'] or 0

                detailed_stats.append({
                    'label': f"{week_start.strftime('%d-%b')} - {week_end.strftime('%d-%b')}",
                    'income': week_income,
                    'expenses': week_expenses
                })

                current_date = week_end + timedelta(days=1)
        elif period == 'quarter':
            for month_offset in range(3):
                current_month = start_month + month_offset
                month_meetings = meetings.filter(date__month=current_month)
                month_income = sum(sum(ds.amount for ds in m.dental_services.all()) for m in month_meetings)
                month_expenses = withdrawals.filter(created_at__month=current_month).aggregate(total=Sum('amount'))['total'] or 0
                detailed_stats.append({
                    'label': f"{current_month}-oy",
                    'income': month_income,
                    'expenses': month_expenses
                })
        elif period == 'year':
            for q in range(1, 5):
                quarter_start_month = (q - 1) * 3 + 1
                quarter_end_month = quarter_start_month + 2
                quarter_meetings = meetings.filter(date__month__gte=quarter_start_month, date__month__lte=quarter_end_month)
                quarter_income = sum(sum(ds.amount for ds in m.dental_services.all()) for m in quarter_meetings)
                quarter_expenses = withdrawals.filter(created_at__month__gte=quarter_start_month, created_at__month__lte=quarter_end_month).aggregate(total=Sum('amount'))['total'] or 0
                detailed_stats.append({
                    'label': f"{q}-chorak",
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

class FinancialReportExportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id='all', *args, **kwargs):
        user = request.user
        clinic = user.clinic

        period = request.query_params.get('period', 'year')
        year = int(request.query_params.get('year', datetime.now().year))
        quarter = int(request.query_params.get('quarter', 1))
        month = int(request.query_params.get('month', datetime.now().month))

        meetings = Meeting.objects.filter(branch__clinic=clinic, status='accepted')
        withdrawals = CashWithdrawal.objects.filter(clinic=clinic)

        if branch_id != 'all':
            meetings = meetings.filter(branch_id=branch_id)
            withdrawals = withdrawals.filter(branch_id=branch_id)

        if period == 'year':
            meetings = meetings.filter(date__year=year)
            withdrawals = withdrawals.filter(created_at__year=year)
        elif period == 'quarter':
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            meetings = meetings.filter(date__year=year, date__month__gte=start_month, date__month__lte=end_month)
            withdrawals = withdrawals.filter(created_at__month__gte=start_month, created_at__month__lte=end_month)
        elif period == 'month':
            meetings = meetings.filter(date__year=year, date__month=month)
            withdrawals = withdrawals.filter(created_at__month=month)

        total_income = meetings.aggregate(total=Sum('payment_amount'))['total'] or 0
        total_expenses = withdrawals.aggregate(total=Sum('amount'))['total'] or 0
        net_profit = total_income - total_expenses
        profitability = (net_profit / total_income * 100) if total_income > 0 else 0

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 40

        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, y, "Moliyaviy Hisobot (PDF)")
        y -= 30
        p.setFont("Helvetica", 12)
        p.drawString(50, y, f"Branch: {branch_id}")
        y -= 20
        p.drawString(50, y, f"Period: {period}, Year: {year}, Quarter: {quarter if period == 'quarter' else '-'}")
        y -= 20
        p.drawString(50, y, f"Total Income: {total_income}")
        y -= 20
        p.drawString(50, y, f"Total Expenses: {total_expenses}")
        y -= 20
        p.drawString(50, y, f"Net Profit: {net_profit}")
        y -= 20
        p.drawString(50, y, f"Profitability: {round(profitability, 2)}%")
        y -= 40

        p.showPage()
        p.save()
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename=financial_report.pdf'
        })


class PatientStatisticsExportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        period = request.query_params.get('period', 'year')
        year = int(request.query_params.get('year', datetime.now().year))
        quarter = int(request.query_params.get('quarter', 1))
        month = int(request.query_params.get('month', datetime.now().month))

        customers = Customer.objects.filter(branch__clinic=clinic)
        if branch_id != 'all':
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

        # Detailed stats
        detailed_stats = []
        if period == 'month':
            first_day_of_month = datetime(year, month, 1)
            last_day_of_month = (first_day_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            current_date = first_day_of_month
            while current_date <= last_day_of_month:
                week_start = current_date
                week_end = min(week_start + timedelta(days=6), last_day_of_month)
                week_patients = customers.filter(created_at__date__range=(week_start, week_end)).count()
                detailed_stats.append((f"{week_start.strftime('%d-%b')} - {week_end.strftime('%d-%b')}", week_patients))
                current_date = week_end + timedelta(days=1)
        elif period == 'quarter':
            start_month = (quarter - 1) * 3 + 1
            for month_offset in range(3):
                current_month = start_month + month_offset
                month_patients = customers.filter(created_at__month=current_month).count()
                detailed_stats.append((f"{current_month}-oy", month_patients))
        elif period == 'year':
            for q in range(1, 5):
                quarter_start_month = (q - 1) * 3 + 1
                quarter_end_month = quarter_start_month + 2
                quarter_patients = customers.filter(created_at__month__gte=quarter_start_month, created_at__month__lte=quarter_end_month).count()
                detailed_stats.append((f"{q}-chorak", quarter_patients))

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 40

        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, y, "Bemorlar Statistikasi (PDF)")
        y -= 30
        p.setFont("Helvetica", 12)
        p.drawString(50, y, f"Branch: {branch_id}")
        y -= 20
        p.drawString(50, y, f"Period: {period}, Year: {year}, Quarter: {quarter if period == 'quarter' else '-'}")
        y -= 20
        p.drawString(50, y, f"Total Patients: {total_patients}")
        y -= 30

        p.setFont("Helvetica-Bold", 13)
        p.drawString(50, y, "Detailed Stats:")
        y -= 20

        for label, count in detailed_stats:
            p.drawString(60, y, f"{label}: {count}")
            y -= 20

        p.showPage()
        p.save()
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename=patient_statistics.pdf'
        })


class DoctorStatisticsExportPDFView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        period = request.query_params.get('period', 'year')
        year = int(request.query_params.get('year', datetime.now().year))
        quarter = int(request.query_params.get('quarter', 1))
        month = int(request.query_params.get('month', datetime.now().month))

        doctors = User.objects.filter(clinic=clinic, role='doctor')
        if branch_id != 'all':
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

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 40

        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, y, "Shifokorlar Statistikasi (PDF)")
        y -= 30
        p.setFont("Helvetica", 12)
        p.drawString(50, y, f"Branch: {branch_id}")
        y -= 20
        p.drawString(50, y, f"Period: {period}, Year: {year}, Quarter: {quarter if period == 'quarter' else '-'}")
        y -= 20

        for stat in doctor_stats:
            p.drawString(50, y, f"Doctor: {stat['doctor_name']}")
            y -= 20
            p.drawString(70, y, f"Total Patients: {stat['total_patients']}")
            y -= 20
            p.drawString(70, y, f"Total Income: {stat['total_income']}")
            y -= 30

        p.showPage()
        p.save()
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename=doctor_statistics.pdf'
        })

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
        if branch_id and branch_id != 'all':
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
        if branch_id and branch_id != 'all':
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
            # Yangi: jami tushum dental_services.amount yig'indisi orqali
            total_income = 0
            for meeting in meetings:
                total_income += sum(ds.amount for ds in meeting.dental_services.all())

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
    # permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all':
            meetings = Meeting.objects.filter(branch__clinic=clinic)
            withdrawals = CashWithdrawal.objects.filter(clinic=clinic)
        else:
            meetings = Meeting.objects.filter(branch_id=branch_id, branch__clinic=clinic)
            withdrawals = CashWithdrawal.objects.filter(branch_id=branch_id, clinic=clinic)

        months = {1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
                7: "Iyul", 8: "Avgust", 9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"}

        monthly_data = []
        for month in range(1, 13):
            month_meetings = meetings.filter(date__month=month)
            # Har bir meeting uchun dental_services.amount yig'indisi
            income = sum(sum(ds.amount for ds in m.dental_services.all()) for m in month_meetings)
            expenses = withdrawals.filter(created_at__month=month).aggregate(total=Sum('amount'))['total'] or 0
            monthly_data.append({
                'month': months[month],
                'income': income,
                'expenses': expenses
            })

        return Response({
            'monthly_data': monthly_data
        })


class DoctorEfficiencyView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all':
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
    # permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all':
            customers = Customer.objects.filter(branch__clinic=clinic)
        else:
            customers = Customer.objects.filter(branch_id=branch_id, branch__clinic=clinic)

        # Meeting modeli orqali doctor va specialization ma'lumotlarini olish
        department_data = Meeting.objects.filter(customer__in=customers).values(
            'doctor__specialization'
        ).annotate(customer_count=Count('customer'))

        total_customers = customers.count()

        return Response({
            'total_customers': total_customers,
            'department_data': list(department_data)
        })


class MonthlyCustomerDynamicsView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all':
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
    # permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        if branch_id == 'all':
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
    # permission_classes = [IsAuthenticated]

    def get(self, request, branch_id=None, *args, **kwargs):
        user = request.user
        clinic = user.clinic

        # Get today's appointments
        today = date.today()


        if branch_id == 'all':
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
    # permission_classes = [IsAuthenticated]

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
    # permission_classes = [IsAuthenticated]
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

    @action(detail=False, methods=['get'])
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

    @action(detail=False, methods=['get'])
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


    @action(detail=False, methods=['get'])
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

    @action(detail=False, methods=['get'])
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


class DentalServiceViewSet(viewsets.ModelViewSet):
    queryset = DentalService.objects.all()
    serializer_class = DentalServiceSerializer

    # permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'teeth_number']
    def get_queryset(self):
        clinic = self.request.user.clinic
        qs = DentalService.objects.filter(clinic=clinic)
        # Qo'shimcha filterlar uchun query params ishlatiladi
        category = self.request.query_params.get('category')
        teeth_number = self.request.query_params.get('teeth_number')
        if category:
            qs = qs.filter(category=category)
        if teeth_number:
            qs = qs.filter(teeth_number=teeth_number)
        return qs

    def perform_create(self, serializer):
        serializer.save(clinic=self.request.user.clinic)


class DentalServiceCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = DentalServiceCategorySerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        clinic = self.request.user.clinic
        return DentalServiceCategory.objects.filter(clinic=clinic)

    def perform_create(self, serializer):
        serializer.save(clinic=self.request.user.clinic)


class DentalServiceBulkCreateView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DentalServiceBulkCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        services = serializer.save()
        return Response({
            "created": len(services),
            "ids": [s.id for s in services]
        })


class DentalServiceNameSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        clinic = request.user.clinic
        categories = DentalServiceCategory.objects.filter(clinic=clinic)
        data = []
        for category in categories:
            services = DentalService.objects.filter(clinic=clinic, category=category)
            unique_names = services.values_list('name', flat=True).distinct()
            for name in unique_names:
                first_service = services.filter(name=name).order_by('id').first()
                data.append({
                    "category_id": category.id,
                    "category_name": category.name,
                    "name": name,
                    "id": first_service.id if first_service else None,
                    "description": first_service.description if first_service else "",
                    "amount": first_service.amount if first_service else "",
                })

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return paginator.get_paginated_response(page)

class DentalServiceByNameView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id):
        clinic = request.user.clinic
        service = DentalService.objects.filter(clinic=clinic, id=service_id).first()
        if not service:
            return Response({"detail": "Not found."}, status=404)
        # Faqat shu nom va shu category uchun barcha tishlarni olish
        all_services = DentalService.objects.filter(
            clinic=clinic,
            name=service.name,
            category=service.category
        ).order_by('teeth_number')
        from .serializers import DentalServiceSerializer
        serializer = DentalServiceSerializer(all_services, many=True)
        return Response(serializer.data)


class DentalServiceBulkUpdateByNameView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, service_id):
        clinic = request.user.clinic
        service = DentalService.objects.filter(clinic=clinic, id=service_id).first()
        if not service:
            return Response({"detail": "Not found."}, status=404)

        all_services = DentalService.objects.filter(
            clinic=clinic,
            name=service.name,
            category=service.category
        ).order_by('teeth_number')

        update_fields = ['name', 'description', 'amount', 'category']
        data = request.data

        # Agar category id bo‘lsa, instansiyaga aylantirib oling
        category_instance = None
        if 'category' in data:
            try:
                category_instance = DentalServiceCategory.objects.get(id=data['category'], clinic=clinic)
            except DentalServiceCategory.DoesNotExist:
                return Response({"detail": "Category not found."}, status=400)

        for ds in all_services:
            for field in update_fields:
                if field in data:
                    if field == 'category':
                        ds.category = category_instance
                    else:
                        setattr(ds, field, data[field])
            ds.save()

        serializer = DentalServiceSerializer(all_services, many=True)
        return Response(serializer.data)