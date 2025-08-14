from django.contrib import admin
from .models import *
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'branch', 'get_images')

    def get_images(self, obj):
        return ", ".join([image.image.url for image in obj.images.all()])
    get_images.short_description = "Rasmlar"

@admin.register(FAQImages)
class FAQImagesAdmin(admin.ModelAdmin):
    list_display = ('image',)


admin.site.register(VitalSign)
admin.site.register(Medicine)
admin.site.register(MedicineSchedule)
admin.site.register(MedicineHistory)
admin.site.register(NurseSchedule)  
admin.site.register(Hospitalization)
admin.site.register(NurseNote)
admin.site.register(NotificationReadStatus)
admin.site.register(ClinicNotificationReadStatus)
admin.site.register(CustomerDebt)