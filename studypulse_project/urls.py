from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse, HttpResponse

def health_check(request):
    return JsonResponse({"status": "ok"})  # Simple 200 OK response

urlpatterns = [
    # Root endpoint with a message
    path('', lambda request: HttpResponse("✅ StudyPulse Backend is running!"), name="root"),
    
    # Health check endpoint
    path('health/', health_check, name="health"),
    
    # Admin and API routes
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
