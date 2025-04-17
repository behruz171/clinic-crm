from django.shortcuts import get_object_or_404
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from app.models import *
from app2.models import *
from .serializers import *
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied


class VitalSignViewSet(viewsets.ModelViewSet):
    """
    Hayotiy ko'rsatkichlar bilan ishlash uchun ViewSet.
    """
    queryset = VitalSign.objects.all()
    serializer_class = VitalSignSerializer

    def perform_create(self, serializer):
        """
        Hayotiy ko'rsatkichlarni yaratishda bemor (Customer) ma'lumotlarini ulash.
        """
        customer_id = self.request.data.get('customer_id')
        if customer_id:
            customer = Customer.objects.get(id=customer_id)
            serializer.save(customer=customer)
        else:
            raise ValueError("Customer ID'si talab qilinadi.")
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Bemorning hayotiy ko'rsatkichlari tarixini ko'rsatish.
        """
        customer = Customer.objects.get(pk=pk)
        vital_signs = customer.vital_signs.all().order_by('-recorded_at')
        serializer = VitalSignSerializer(vital_signs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def chart_data(self, request, pk=None):
        """
        Diagramma uchun bemorning barcha hayotiy ko'rsatkichlarini qaytarish.
        """
        customer = get_object_or_404(Customer, pk=pk)
        vital_signs = customer.vital_signs.all().order_by('recorded_at')  # Vaqt bo'yicha tartiblangan
        data = {
            "temperature": [{"time": vs.recorded_at, "value": vs.temperature} for vs in vital_signs],
            "blood_pressure": [{"time": vs.recorded_at, "value": vs.blood_pressure} for vs in vital_signs],
            "heart_rate": [{"time": vs.recorded_at, "value": vs.heart_rate} for vs in vital_signs],
            "respiratory_rate": [{"time": vs.recorded_at, "value": vs.respiratory_rate} for vs in vital_signs],
            "oxygen_saturation": [{"time": vs.recorded_at, "value": vs.oxygen_saturation} for vs in vital_signs],
        }
        return Response(data)




class MedicineViewSet(viewsets.ModelViewSet):
    """
    Dorilar ro'yxati bilan ishlash uchun ViewSet.
    """
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer

    def perform_create(self, serializer):
        """
        Medicine yaratilganda token orqali foydalanuvchining filialini ulash.
        """
        user = self.request.user
        if not hasattr(user, 'branch'):
            raise PermissionDenied("Foydalanuvchining filial ma'lumoti mavjud emas.")
        serializer.save(branch=user.branch)


class MedicineScheduleViewSet(viewsets.ModelViewSet):
    """
    Dori berish jadvali bilan ishlash uchun ViewSet.
    """
    queryset = MedicineSchedule.objects.all()
    serializer_class = MedicineScheduleSerializer


class MedicineHistoryViewSet(viewsets.ModelViewSet):
    """
    Dori berish tarixi bilan ishlash uchun ViewSet.
    """
    queryset = MedicineHistory.objects.all()
    serializer_class = MedicineHistorySerializer


class NurseScheduleViewSet(viewsets.ModelViewSet):
    queryset = NurseSchedule.objects.all()
    serializer_class = NurseScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter schedules for the logged-in user if they are a nurse
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return NurseSchedule.objects.filter(user_id=user_id)
        return super().get_queryset()

    def perform_create(self, serializer):
        # Ensure a schedule is created for all 7 days if not already present
        user = serializer.validated_data['user']
        day = serializer.validated_data['day']
        if NurseSchedule.objects.filter(user=user, day=day).exists():
            raise serializers.ValidationError(f"Schedule for {day} already exists for this nurse.")
        serializer.save()


class HospitalizationViewSet(viewsets.ModelViewSet):
    queryset = Hospitalization.objects.all()
    serializer_class = HospitalizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            return Hospitalization.objects.filter(patient_id=patient_id)
        return super().get_queryset()


class FAQViewSet(viewsets.ModelViewSet):
    """
    FAQ va rasmlar bilan ishlash uchun ViewSet.
    """
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer

    def create(self, request, *args, **kwargs):
        """
        FAQ yaratish va rasmlarni yuklash.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_images = serializer.validated_data.pop('uploaded_images', [])  # Yuklangan rasmlarni olish
        faq = FAQ.objects.create(**serializer.validated_data)

        # Rasmlarni saqlash va FAQ bilan bog'lash
        for image in uploaded_images:
            faq_image = FAQImages.objects.create(image=image)
            faq.images.add(faq_image)

        faq.save()
        return Response(self.get_serializer(faq).data)