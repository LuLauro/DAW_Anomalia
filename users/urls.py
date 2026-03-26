from django.urls import path, include
from .views import CustomLoginView, CustomLogoutView, signup_view

app_name = 'users'


urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('signup/', signup_view, name='signup'),

    # Inclui todas as URLs de reset de senha do Django
    path('', include('django.contrib.auth.urls')),
]
