from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

def api_root(request):
    return JsonResponse({
        'service': 'Agente CFE API',
        'status': 'ok',
        'endpoints': ['/api/areas/', '/api/dispositivos/', '/api/sims/'],
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-root'),
    path('api/', include('usuarios.urls')),
    path('api/', include('areas.urls')),
    path('api/', include('trabajadores.urls')),
    path('api/', include('dispositivos.urls')),
    path('api/', include('sims.urls')),
    path('api/', include('consumos.urls')),
    path('api/', include('redes.urls')),
    path('api/', include('reportes.urls')),
    path('api/', include('bateria.urls')),
    path('api/', include('ram.urls')),
    path('api/', include('almacenamiento.urls')),
]
