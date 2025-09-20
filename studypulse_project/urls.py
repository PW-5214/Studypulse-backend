from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('', lambda request: HttpResponse("✅ StudyPulse Backend is running!")),
    path('health/', health_check, name="health"),   # Health check endpoint
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
