from django.core.mail import send_mail
from django.conf import settings

subject = "Your Account Credentials"
message = f"Dear Test,\n\nYour account has been created successfully.\n\nUsername\n\nPlease log in and change your password as soon as possible."
# try:
gmail = send_mail(
    subject=subject,
    message=message,
    from_email=settings.EMAIL_HOST_USER,
    recipient_list=['shamuratov6563@gmail.com'],
)