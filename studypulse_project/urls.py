from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse

def health_check(request):
    return JsonResponse({"status": "ok"})  # Railway health check

urlpatterns = [
    path('', lambda request: HttpResponse("✅ StudyPulse Backend is running!")),  # root
    path('health/', health_check, name="health"),  # health check
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
