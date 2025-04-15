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