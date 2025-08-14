from django.db import models
from app.models import *


class Hospitalization(BaseModel):
    """
    Bemorning kasalxonaga yotqizilishi.
    """
    patient = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='hospitalizations')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hospitalizations')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='hospitalizations')
    start_date = models.DateField(verbose_name="Boshlash sanasi")
    end_date = models.DateField(verbose_name="Tugatish sanasi", null=True, blank=True)
    diagnosis = models.CharField(max_length=255, verbose_name="Tashxis")
    notes = models.TextField(verbose_name="Izohlar", null=True, blank=True)

    def __str__(self):
        return f"{self.patient.full_name} - {self.diagnosis} ({self.start_date} - {self.end_date or 'Hozirgi'})"


class VitalSign(BaseModel):
    customer = models.ForeignKey(Customer, related_name='vital_signs', on_delete=models.CASCADE)
    hospitalization = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name='vital_signs', null=True, blank=True)
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
    hospitalization = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name='medicine_schedules', null=True, blank=True)
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
        return f"{self.user.get_full_name()} - {self.get_day_display()}"

class NurseNote(BaseModel):
    """
    Hamshira yozuvlari.
    """
    hospitalization = models.ForeignKey(Hospitalization, on_delete=models.CASCADE, related_name='nurse_notes')
    nurse = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes', limit_choices_to={'role': 'nurse'})
    note = models.TextField(verbose_name="Yozuv")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hospitalization.patient.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
class FAQImages(BaseModel):
    image = models.ImageField(upload_to='faq_images/', verbose_name="Rasm")

class FAQ(BaseModel):
    """
    Tez-tez so'raladigan savollar.
    """
    question = models.CharField(max_length=255, verbose_name="Savol")
    images = models.ManyToManyField(FAQImages, related_name='faq_images', verbose_name="Rasmlar", null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='faqs', verbose_name="Filial")

    def __str__(self):
        return self.question


class NotificationReadStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_read_statuses')
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='read_statuses')
    is_read = models.BooleanField(default=False)  # O'qilgan yoki o'qilmaganligini belgilaydi
    read_at = models.DateTimeField(null=True, blank=True)  # O'qilgan vaqt

    class Meta:
        unique_together = ('user', 'notification')  # Har bir foydalanuvchi uchun noyob yozuv
        verbose_name = "Notification Read Status"
        verbose_name_plural = "Notification Read Statuses"

    def __str__(self):
        return f"{self.user} - {self.notification.title} - {'Read' if self.is_read else 'Unread'}"


class ClinicNotificationReadStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clinic_notification_read_statuses')
    clinic_notification = models.ForeignKey(ClinicNotification, on_delete=models.CASCADE, related_name='read_statuses')
    is_read = models.BooleanField(default=False)  # O'qilgan yoki o'qilmaganligini belgilaydi
    read_at = models.DateTimeField(null=True, blank=True)  # O'qilgan vaqt

    class Meta:
        unique_together = ('user', 'clinic_notification')  # Har bir foydalanuvchi uchun noyob yozuv
        verbose_name = "Clinic Notification Read Status"
        verbose_name_plural = "Clinic Notification Read Statuses"

    def __str__(self):
        return f"{self.user} - {self.clinic_notification.title} - {'Read' if self.is_read else 'Unread'}"


class ContactRequest(models.Model):
    STATUS_CHOICES = (
        ('new', 'Yangi'),
        ('connected', 'Bog‘lanilgan'),
    )

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    clinic_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')  # Yangi status maydoni
    description = models.TextField(null=True, blank=True)  # Qo'shimcha izoh

    def __str__(self):
        return f"{self.name} - {self.clinic_name}"



class CustomerDebt(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='debts')
    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name='debts')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Mijoz to‘lagan summa
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)     # Chegirma miqdori
    discount_procent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Chegirma foizi
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.customer} - Berilgan summa: {self.amount_paid} so'm"