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

# Create your views here.

class ClinicViewSet(viewsets.ModelViewSet):
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [IsAuthenticated]

class RoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Role.objects.filter(clinic=self.request.user.clinic)

class SpecializationViewSet(viewsets.ModelViewSet):
    serializer_class = SpecializationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Specialization.objects.filter(clinic=self.request.user.clinic)

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Faqat o'z klinikasidagi foydalanuvchilarni ko'rsatish
        return User.objects.filter(clinic=self.request.user.clinic)
    
    def perform_create(self, serializer):
        # Yangi foydalanuvchi yaratishda klinikani avtomatik qo'shish
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
