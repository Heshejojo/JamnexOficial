from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Rol, Usuario
from .serializers import LoginSerializer, RolSerializer, UsuarioAdminSerializer, UsuarioSerializer
from .permissions import RolePermission


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserMeView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UsuarioAdminListCreateAPIView(generics.ListCreateAPIView):
    queryset = Usuario.objects.select_related('rol').all().order_by('id')
    serializer_class = UsuarioAdminSerializer
    permission_classes = [RolePermission]


class UsuarioAdminDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Usuario.objects.select_related('rol').all()
    serializer_class = UsuarioAdminSerializer
    permission_classes = [RolePermission]


class RolListAPIView(generics.ListCreateAPIView):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [RolePermission]


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if refresh:
            RefreshToken(refresh).blacklist()
        return Response({'detail': 'Sesión cerrada.'}, status=status.HTTP_205_RESET_CONTENT)
