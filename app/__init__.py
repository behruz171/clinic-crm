from __future__ import absolute_import, unicode_literals

# Celery ilovasini import qilish
from clinic.celery import app as celery_app

__all__ = ('celery_app',)