from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})  # Simple 200 OK response

urlpatterns = [
    path('', health_check, name="health"),   # root endpoint
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # your API routes
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
