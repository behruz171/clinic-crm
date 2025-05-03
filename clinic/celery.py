from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Django settings faylini o'rnatish
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')

app = Celery('clinic')

# Django sozlamalarini yuklash
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery vazifalarini avtomatik aniqlash
app.autodiscover_tasks()