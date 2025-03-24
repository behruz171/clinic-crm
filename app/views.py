from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from .models import User, Clinic, Notification, UserNotification, Cabinet, Customer, Meeting, Branch
from .serializers import (UserSerializer, LoginSerializer, ClinicSerializer, NotificationSerializer, UserNotificationSerializer, CabinetSerializer, CustomerSerializer, MeetingSerializer, BranchSerializer)
from .permissions import IsClinicAdmin
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import serializers
from .models import CustomUserManager
from django.contrib.auth.decorators import login_required
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

token_param = openapi.Parameter(
    'Authorization',
    openapi.IN_HEADER,
    description="JWT Token: Bearer <token>",
    type=openapi.TYPE_STRING
)

# Create your views here.

class ClinicViewSet(viewsets.ModelViewSet):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [IsAuthenticated]


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['specialization', 'role', 'branch', 'status']
    search_fields = ['first_name', 'last_name']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        return User.objects.filter(clinic=user.clinic)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    
    def perform_create(self, serializer):
        serializer.save(clinic=self.request.user.clinic)
    
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
                    'user': UserSerializer(user).data
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
                'clinic_address': openapi.Schema(type=openapi.TYPE_STRING, description='Klinika manzili'),
                'clinic_phone': openapi.Schema(type=openapi.TYPE_STRING, description='Klinika telefoni'),
                'clinic_license': openapi.Schema(type=openapi.TYPE_STRING, description='Klinika litsenziyasi'),
                'user_email': openapi.Schema(type=openapi.TYPE_STRING, description='Foydalanuvchi emaili'),
            },
            required=['clinic_name', 'clinic_address', 'clinic_phone', 'clinic_license', 'user_email']
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
        clinic_address = request.data.get('clinic_address')
        clinic_phone = request.data.get('clinic_phone')
        clinic_license = request.data.get('clinic_license')
        user_email = request.data.get('user_email')

        user_manager = CustomUserManager()
        clinic, user = user_manager.create_clinic_and_user(
            clinic_name, clinic_address, clinic_phone, clinic_license, user_email
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
    filterset_fields = ['gender', 'status', 'branch', 'doctor']
    search_fields = ['full_name', 'email', 'phone_number', 'location', 'diagnosis']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Customer.objects.none()
        return Customer.objects.filter(branch__clinic=user.clinic)

    def perform_create(self, serializer):
        customer = serializer.save()
        if customer.doctor.branch != customer.branch:
            return Response({"error": "Customer's branch must match the doctor's branch."}, status=status.HTTP_400_BAD_REQUEST)
        customer.save()

class MeetingViewSet(viewsets.ModelViewSet):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'branch', 'doctor', 'customer']
    search_fields = ['comment']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Meeting.objects.none()
        return Meeting.objects.filter(branch__clinic=user.clinic)

    def perform_create(self, serializer):
        meeting = serializer.save()
        if meeting.customer.branch != meeting.branch:
            return Response({"error": "Meeting's branch must match the customer's branch."}, status=status.HTTP_400_BAD_REQUEST)
        if meeting.doctor.branch != meeting.branch:
            return Response({"error": "Meeting's branch must match the doctor's branch."}, status=status.HTTP_400_BAD_REQUEST)
        meeting.save()

class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['clinic']
    search_fields = ['name', 'address', 'phone_number', 'email']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Branch.objects.none()
        return Branch.objects.filter(clinic=user.clinic)

    def perform_create(self, serializer):
        branch = serializer.save()
        if branch.clinic != self.request.user.clinic:
            return Response({"error": "Branch's clinic must match the user's clinic."}, status=status.HTTP_400_BAD_REQUEST)
        branch.save()

@login_required
def get_notifications(request):
    notifications = UserNotification.objects.filter(recipient=request.user).order_by('-timestamp')[:5]
    data = [{"title": n.title, "message": n.message, "timestamp": n.timestamp.strftime("%Y-%m-%d %H:%M:%S")} for n in notifications]
    return JsonResponse(data, safe=False)

def notifications_view(request):
    return render(request, 'index.html')
