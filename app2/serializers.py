import datetime
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from app.models import *
from app2.models import *
from django.utils.timezone import localtime, make_aware
import pytz


class VitalSignSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSign
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    vital_signs = VitalSignSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = '__all__'


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = '__all__'


class MedicineScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineSchedule
        fields = '__all__'


class MedicineHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineHistory
        fields = '__all__'


class NurseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurseSchedule
        fields = ['id', 'user', 'day', 'start_time', 'end_time', 'is_working']

class HospitalizationSerializer(serializers.ModelSerializer):
    vital_signs = VitalSignSerializer(many=True, read_only=True)
    medicine_schedules = MedicineScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Hospitalization
        fields = '__all__'

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'specialization']

class BusyTimeSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Meeting
        fields = ['time']

    def get_time(self, obj):
        return localtime(obj.date).strftime('%H:%M')



class FAQImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQImages
        fields = ['id', 'image']  # Rasm ID va fayl yo'li

class FAQSerializer(serializers.ModelSerializer):
    images = FAQImageSerializer(many=True, read_only=True)  # Rasmlarni o'qish uchun
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )  # Rasmlarni yuklash uchun

    class Meta:
        model = FAQ
        fields = ['id', 'question', 'branch', 'images', 'uploaded_images']




class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email bilan foydalanuvchi topilmadi.")
        return value

class PasswordResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

class PasswordResetChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)


class NotificationReadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationReadStatus
        fields = ['id', 'user', 'notification', 'is_read', 'read_at']


class ClinicNotificationReadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicNotificationReadStatus
        fields = ['id', 'user', 'clinic_notification', 'is_read', 'read_at']


class ContactRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactRequest
        fields = ['id', 'name', 'email', 'phone_number', 'clinic_name', 'created_at', 'status', 'description']