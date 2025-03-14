from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import User

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:  # Faqat yangi user yaratilganda
        context = {
            'username': instance.username,
            'full_name': instance.get_full_name(),
            'clinic': instance.clinic.name,
            'role': instance.role.name
        }
        
        # HTML formatdagi xabar
        html_message = render_to_string('email/welcome.html', context)
        
        # Oddiy text formatdagi xabar
        plain_message = f"""
        Assalomu alaykum, {instance.get_full_name()}!
        
        Siz muvaffaqiyatli ro'yxatdan o'tdingiz.
        
        Klinika: {instance.clinic.name}
        Lavozim: {instance.role.name}
        Login: {instance.username}
        
        Hurmat bilan,
        {instance.clinic.name} ma'muriyati
        """
        
        # Xabar yuborish
        send_mail(
            subject=f"Xush kelibsiz - {instance.clinic.name}",
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[instance.email],
            html_message=html_message
        ) 