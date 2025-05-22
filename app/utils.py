from django.core.mail import send_mail
from django.conf import settings
from email.message import EmailMessage
from email.utils import make_msgid
import smtplib
import ssl

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'starclaudsuport@gmail.com'  # Gmail pochtangiz
EMAIL_HOST_PASSWORD = 'yhvqsewlnwwqvsco'  # Gmail app password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


def send_code_email_(email):
    subject = "Test Title"
    body = "Test uchun"
    em = EmailMessage()
    em["Message-ID"] = make_msgid()
    em["From"] = EMAIL_HOST_USER
    em["To"] = email
    em["Subject"] = subject
    em.set_content(body, subtype="html")
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(EMAIL_HOST, 465, context=context) as smtp:
        smtp.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        smtp.sendmail(EMAIL_HOST_USER, email, em.as_string())



send_code_email_("shamuratov6563@gmail.com")