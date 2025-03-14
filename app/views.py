from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Clinic, Role, Specialization
from .serializers import (UserSerializer, LoginSerializer, ClinicSerializer, 
                        RoleSerializer, SpecializationSerializer)
from .permissions import IsClinicAdmin
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

class SpecializationViewSet(viewsets.ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [IsAuthenticated]

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Foydalanuvchilar ro'yxatini olish",
        manual_parameters=[token_param],
        responses={
            200: UserSerializer(many=True),
            401: 'Unauthorized'
        }
    )
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
