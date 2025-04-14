from django.db import models
from app.models import *




class VitalSign(BaseModel):
    customer = models.ForeignKey(Customer, related_name='vital_signs', on_delete=models.CASCADE)
    temperature = models.FloatField()  # Harorat
    blood_pressure = models.CharField(max_length=20)  # Qon bosimi
    heart_rate = models.IntegerField()  # Yurak urishi
    respiratory_rate = models.IntegerField()  # Nafas olish tezligi
    oxygen_saturation = models.IntegerField()  # Kislorod saturatsiyasi
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.full_name} - {self.recorded_at}"


class Medicine(BaseModel):
    """
    Dorilar ro'yxati.
    """
    name = models.CharField(max_length=255, verbose_name="Dori nomi")
    dosage = models.CharField(max_length=50, verbose_name="Dozasi")
    instructions = models.TextField(verbose_name="Ko'rsatmalar", blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='medicines', verbose_name="Filial")

    def __str__(self):
        return f"{self.name} ({self.dosage})"


class MedicineSchedule(BaseModel):
    """
    Dori berish jadvali.
    """
    patient = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='medicine_schedules')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescribed_medicines')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='medicine_schedules')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='schedules')
    start_date = models.DateField(verbose_name="Boshlash sanasi")
    end_date = models.DateField(verbose_name="Tugatish sanasi")
    times_per_day = models.JSONField(verbose_name="Kunlik vaqtlar (soatlar)")
    instructions = models.TextField(verbose_name="Qo'shimcha ko'rsatmalar", blank=True, null=True)

    def __str__(self):
        return f"{self.patient.full_name} - {self.medicine.name}"


class MedicineHistory(BaseModel):
    """
    Dori berish tarixi.
    """
    schedule = models.ForeignKey(MedicineSchedule, on_delete=models.CASCADE, related_name='history')
    given_at = models.DateTimeField(auto_now_add=True, verbose_name="Berilgan vaqt")
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_medicines', verbose_name="Hamshira")
    notes = models.TextField(verbose_name="Izohlar", blank=True, null=True)

    def __str__(self):
        return f"{self.schedule.medicine.name} - {self.given_at}"


class NurseSchedule(BaseModel):
    DAYS_OF_WEEK = (
        ('monday', 'Dushanba'),
        ('tuesday', 'Seshanba'),
        ('wednesday', 'Chorshanba'),
        ('thursday', 'Payshanba'),
        ('friday', 'Juma'),
        ('saturday', 'Shanba'),
        ('sunday', 'Yakshanba'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules')
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField(default="09:00")
    end_time = models.TimeField(default="18:00")
    is_working = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'day')  # Ensure each nurse has only one schedule per day

    def __str__(self):
        return f"{self.nurse.get_full_name()} - {self.get_day_display()}"