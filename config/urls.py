from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),

    # Redirect root URL '/' to dashboard/
    path('', lambda request: redirect('dashboard/')),

    path('dashboard/', include('dashboard.urls')),
    path('anomalias/', include('anomalias.urls')),
    path('salas/', include('salas.urls')),
    path('computadores/', include('computadores.urls')),
    path('tecnico/', include('tecnico.urls')),
    path('relatorios/', include(('relatorios.urls', 'relatorios'), namespace='relatorios')),
    path('ai/', include('ai_agent.urls')),
    path('', include(('users.management_urls', 'user_management'), namespace='user_management')),

    # Users app handles login/logout/signup/password reset
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('notificacoes/', include('notificacoes.urls', namespace='notificacoes')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
