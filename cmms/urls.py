from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('accounts.urls')),
    path('activos/', include('activos.urls')),
    path('personal/', include(('personal.urls', 'personal'), namespace='personal')),
    path('reportes/', include('reportes.urls', namespace='reportes')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
