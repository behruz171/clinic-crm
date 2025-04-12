from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Clinic CRM API",
        default_version='v1',
        description="Clinic CRM tizimi uchun API dokumentatsiya",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@clinic.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    # security_definitions={
    #     'Bearer': {
    #         'type': 'apiKey',
    #         'name': 'Authorization',
    #         'in': 'header',
    #         'description': 'JWT token format: Bearer <token>'
    #     }
    # },
    # security=[{'Bearer': []}],
    
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('app.urls')),
    
    # Swagger URL'lari
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
