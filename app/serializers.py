from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *

class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ('id', 'name', 'address', 'phone_number', 'license_number', 'is_active')




class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    specialization_name = serializers.CharField(source='specialization.name', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 
                 'email', 'role', 'role_name', 'phone_number', 'specialization',
                 'specialization_name', 'status', 'clinic', 'clinic_name')
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        # read_only_fields = ('sent_by',)

class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = "__all__"


class CabinetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cabinet
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'