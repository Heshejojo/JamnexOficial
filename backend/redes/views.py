from rest_framework import generics, permissions

from .models import RegistroRed
from .serializers import RegistroRedSerializer
from usuarios.permissions import RolePermission


class RegistroRedListAPIView(generics.ListAPIView):
    queryset = RegistroRed.objects.select_related('dispositivo', 'sim', 'operador').all()
    serializer_class = RegistroRedSerializer
    permission_classes = [RolePermission]


class RegistroRedDetailAPIView(generics.RetrieveAPIView):
    queryset = RegistroRed.objects.select_related('dispositivo', 'sim', 'operador').all()
    serializer_class = RegistroRedSerializer
    permission_classes = [RolePermission]
