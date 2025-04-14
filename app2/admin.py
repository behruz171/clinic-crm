from django.contrib import admin
from .models import *

admin.site.register(VitalSign)
admin.site.register(Medicine)
admin.site.register(MedicineSchedule)
admin.site.register(MedicineHistory)
admin.site.register(NurseSchedule)  