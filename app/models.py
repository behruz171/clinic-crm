from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Avval clinic va role yaratamiz
        from .models import Clinic, Role
        clinic = Clinic.objects.create(
            name="System Clinic",
            address="System Address",
            phone_number="000",
            license_number="000"
        )
        role = Role.objects.create(
            name="System Admin",
            clinic=clinic
        )
        
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('clinic', clinic)
        extra_fields.setdefault('role', role)
        
        return self._create_user(username, email, password, **extra_fields)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Clinic(BaseModel):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    license_number = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Role(BaseModel):
    name = models.CharField(max_length=100)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='roles')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.clinic.name}"

    class Meta:
        unique_together = ['name', 'clinic']


class Specialization(BaseModel):
    name = models.CharField(max_length=100)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='specializations')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.clinic.name}"

    class Meta:
        unique_together = ['name', 'clinic']


class User(AbstractUser):
    STATUS_CHOICES = (
        ('faol', 'Faol'),
        ('nofaol', 'Nofaol'),
        ("tatilda", "Ta'tilda"),
    )
    
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='users')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='users')
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
        blank=True
    )
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='faol')
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.get_full_name()} - {self.role.name} ({self.clinic.name})"

    def save(self, *args, **kwargs):
        if not self.phone_number:
            self.phone_number = "000"  # default raqam superuser uchun
            
        # Tekshirish: role va specialization shu klinikaga tegishlimi
        if self.role and self.role.clinic_id != self.clinic_id:
            raise ValueError("Role boshqa klinikaga tegishli")
        if self.specialization and self.specialization.clinic_id != self.clinic_id:
            raise ValueError("Specialization boshqa klinikaga tegishli")
        super().save(*args, **kwargs)


class Statistics(models.Model):
    """Bu model faqat admin panelda statistika ko'rsatish uchun"""
    class Meta:
        managed = False  # Jadval yaratilmaydi
        verbose_name = 'Statistika'
        verbose_name_plural = 'Statistika'
        default_permissions = []  # Ruxsatlar yaratilmaydi


class Notification(BaseModel):
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar")
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_notifications', verbose_name="Yuboruvchi")
    
    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title
