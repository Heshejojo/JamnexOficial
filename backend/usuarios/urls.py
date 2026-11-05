from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, LogoutView, RolListAPIView, UserMeView, UsuarioAdminDetailAPIView, UsuarioAdminListCreateAPIView

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('usuarios/me/', UserMeView.as_view(), name='user-me'),
    path('usuarios/', UsuarioAdminListCreateAPIView.as_view(), name='usuarios-list'),
    path('usuarios/<int:pk>/', UsuarioAdminDetailAPIView.as_view(), name='usuarios-detail'),
    path('roles/', RolListAPIView.as_view(), name='roles-list'),
]
