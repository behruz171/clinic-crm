import datetime
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from app.models import *
from app2.models import *

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
    date = serializers.SerializerMethodField(read_only=True)  # Faqat sana
    time = serializers.SerializerMethodField(read_only=True)  # Faqat vaqt
    class Meta:
        model = Meeting
        fields = ['date', 'time']
    
    def get_date(self, obj):
        """
        Returns only the date part of the datetime.
        """
        date_value = obj.get('date') if isinstance(obj, dict) else getattr(obj, 'date', None)
        if isinstance(date_value, datetime.datetime):
            return date_value.date().isoformat()
        if isinstance(date_value, str):
            return date_value.split('T')[0]
        return None

    def get_time(self, obj):
        """
        Returns only the time part of the datetime in HH:MM format.
        """
        date_value = obj.get('date') if isinstance(obj, dict) else getattr(obj, 'date', None)
        if isinstance(date_value, datetime.datetime):
            return date_value.time().strftime('%H:%M')  # Faqat HH:MM formatda qaytarish
        if isinstance(date_value, str):
            return date_value.split('T')[1].split('Z')[0].split('+')[0][:5]  # Faqat HH:MM qismini olish
        return None


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