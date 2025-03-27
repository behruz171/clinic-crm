from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Avval clinic va role yaratamiz
        from .models import Clinic
        clinic = Clinic.objects.create(
            name="System Clinic",
            phone_number="000",
            license_number="000"
        )
        
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('clinic', clinic)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('specialization', 'general')
        
        return self._create_user(username, email, password, **extra_fields)

    def create_clinic_and_user(self, clinic_name, clinic_phone, clinic_license, user_email):
        from .models import Clinic, User

        # Create clinic without passing an address
        clinic = Clinic.objects.create(
            name=clinic_name,
            phone_number=clinic_phone,
            license_number=clinic_license,
            email=user_email
        )

        # Generate random password
        password = get_random_string(length=8)

        # Create user
        user = User.objects.create_user(
            username=user_email,
            email=user_email,
            password=password,
            clinic=clinic,
            role='director',
            specialization='director'
        )
        
        # Send email directly from here
        context = {
            'username': user_email,
            'full_name': user.get_full_name(),
            'clinic': clinic_name,
            'role': user.get_role_display(),
            'password': password  # Use plain text password
        }
        
        # HTML formatdagi xabar
        html_message = render_to_string('email/welcome.html', context)
        
        # Oddiy text formatdagi xabar
        plain_message = f"""
        Assalomu alaykum, {user.get_full_name()}!
        
        Siz muvaffaqiyatli ro'yxatdan o'tdingiz.
        
        Klinika: {clinic_name}
        Lavozim: {user.get_role_display()}
        Login: {user_email}
        Parol: {password}
        
        Hurmat bilan,
        {clinic_name} ma'muriyati
        """
        
        # Xabar yuborish
        try:
            send_mail(
                subject=f"Xush kelibsiz - {clinic_name}",
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user_email],
                html_message=html_message  # Ensure html_message is included
            )
            print(f"Email sent to {user_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")

        return clinic, user


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Clinic(BaseModel):
    full_name = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    license_number = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=255, unique=True)  # Add unique constraint back
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)
    email = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.clinic.name})"


class User(AbstractUser):
    STATUS_CHOICES = (
        ('faol', 'Faol'),
        ('nofaol', 'Nofaol'),
        ("tatilda", "Ta'tilda"),
    )
    
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('receptionist', 'Receptionist'),
        ('director', 'Director'),
    )

    SPECIALIZATION_CHOICES = (
        ('general', 'General'),
        ('cardiology', 'Cardiology'),
        ('dermatology', 'Dermatology'),
        ('pediatrics', 'Pediatrics'),
        ('neurology', 'Neurology'),
        ('director', 'Director'),
    )
    
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='users')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='doctor')
    specialization = models.CharField(
        max_length=20,
        choices=SPECIALIZATION_CHOICES,
        default='general',
        null=True,
        blank=True
    )
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='faol')
    salary = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.get_full_name()} - {self.get_role_display()} ({self.clinic.name})"

    def save(self, *args, **kwargs):
        if not self.phone_number:
            self.phone_number = "000"  # default raqam superuser uchun
            
        super().save(*args, **kwargs)

class Cabinet(BaseModel):

    STATUS_CHOICES = (
        ('available', 'Available'),
        ('creating', 'Creating'),
        ("repair", "Repair"),
    )

    TYPE_CHOICES = (
        ('jarrohlik', "Jarrohlik"),
        ('laboratoriya', 'Laboratoriya'),
        ('tezyordam', 'Tezyordam'),
        ('stomatalogiya', "Stomatalogiya"),
    )

    FLOOR_CHOICES = (
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
    )

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='branches')
    user = models.ManyToManyField(User, related_name='users')
    name = models.CharField(max_length=100)
    floor = models.CharField(max_length=100, choices=FLOOR_CHOICES)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES)
    type = models.CharField(max_length=100, choices=TYPE_CHOICES)
    description = models.TextField()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the cabinet instance first
        if self.user.exists():
            for user in self.user.all():
                if user.branch != self.branch:
                    raise ValueError("User's branch must match the cabinet's branch.")
        super().save(*args, **kwargs)  # Save again to ensure all changes are persisted

class Customer(BaseModel):
    GENDER_CHOICES = (
        ('male',"Male"),
        ('female', "Female")
    )

    STATUS_CHOICES = (
        ('faol', 'Faol'),
        ('nofaol', 'Nofaol'),
    )

    full_name = models.CharField(max_length=100)
    age = models.IntegerField(default=0)
    gender = models.CharField(max_length=100, choices=GENDER_CHOICES)
    phone_number = models.CharField(max_length=19)
    email = models.EmailField(max_length=100)
    location = models.CharField(max_length=100)
    diagnosis = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'doctor'})

    def save(self, *args, **kwargs):
        if self.doctor.branch != self.branch:
            raise ValueError("Customer's branch must match the doctor's branch.")
        super().save(*args, **kwargs)

class Meeting(BaseModel):
    STATUS_CHOICES = (
        ('expected', 'Kutilyapti'),
        ('accepted', 'Tasdiqlandi'),
        ("finished", "Yakunlandi"),
        ('cancelled', "Bekor qilindi")
    )

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'doctor'}) 
    date = models.DateTimeField()
    status = models.CharField(max_length=100, choices=STATUS_CHOICES)
    comment = models.TextField()
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # New field for payment

    def save(self, *args, **kwargs):
        if self.customer.branch != self.branch:
            raise ValueError("Meeting's branch must match the customer's branch.")
        if self.doctor.branch != self.branch:
            raise ValueError("Meeting's branch must match the doctor's branch.")
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
    
    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ClinicNotification(BaseModel):
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar")
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='notifications', verbose_name="Klinika")
    
    class Meta:
        verbose_name = "Klinika Xabarnoma"
        verbose_name_plural = "Klinika Xabarnomalar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class UserNotification(BaseModel):
    sender = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE, verbose_name="Yuboruvchi")
    recipient = models.ForeignKey(User, related_name='received_notifications', on_delete=models.CASCADE, verbose_name="Qabul qiluvchi")
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    message = models.TextField(verbose_name="Xabar")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Xabarnoma"
        verbose_name_plural = "User Xabarnomalar"
        ordering = ['-timestamp']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        channel_layer = get_channel_layer()
        notification_data = {
            "type": "notification_message",
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }
        async_to_sync(channel_layer.group_send)(
            f"notifications_{self.recipient.id}", notification_data
        )

class Room(BaseModel):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
    )

    TYPE_CHOICES = (
        ('standard', 'Standard Room'),
        ('deluxe', 'Deluxe Room'),
        ('vip', 'VIP Room'),
    )

    FLOOR_CHOICES = (
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
    )

    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='standard')
    floor = models.CharField(max_length=10, choices=FLOOR_CHOICES, default='1')
    capacity = models.PositiveIntegerField(default=1)
    daily_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    description = models.TextField()
    customers = models.ManyToManyField(Customer, related_name='rooms', blank=True)

    def save(self, *args, **kwargs):
        if self.pk:  # Check if the room already exists
            if self.customers.count() > self.capacity:
                raise ValueError("The number of customers exceeds the room's capacity.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_type_display()} - Floor {self.floor} - {self.get_status_display()}"

class CashWithdrawal(BaseModel):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='cash_withdrawals')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='cash_withdrawals', null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Withdrawal: {self.amount} - {self.reason}"

