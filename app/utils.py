from django.core.mail import send_mail
from django.conf import settings
from email.message import EmailMessage
from email.utils import make_msgid
import smtplib
import ssl

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 2525
EMAIL_HOST_USER = 'starclaudsuport@gmail.com'  # Gmail pochtangiz
EMAIL_HOST_PASSWORD = 'yhvqsewlnwwqvsco'  # Gmail app password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


def send_code_email_(email):
    print("Email:", email)
    subject = "Test Title"
    body = "Test uchun"
    em = EmailMessage()
    print(222, )
    em["Message-ID"] = make_msgid()
    em["From"] = EMAIL_HOST_USER
    em["To"] = email
    em["Subject"] = subject
    print(333, )
    em.set_content(body, subtype="html")
    # context = ssl.create_default_context()
    print(444, )
    # Send the email
    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as smtp:
        print(555, )
        smtp.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        print(666, )
        smtp.sendmail(EMAIL_HOST_USER, email, em.as_string())
        print(777, )



send_code_email_("behruzzo662@gmail.com")