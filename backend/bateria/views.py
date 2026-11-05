from rest_framework import generics

from usuarios.permissions import RolePermission

from .models import RegistroBateria
from .serializers import RegistroBateriaSerializer


class RegistroBateriaListAPIView(generics.ListCreateAPIView):
    queryset = RegistroBateria.objects.select_related('dispositivo').all().order_by('-fecha_hora')
    serializer_class = RegistroBateriaSerializer
    permission_classes = [RolePermission]


class RegistroBateriaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RegistroBateria.objects.all()
    serializer_class = RegistroBateriaSerializer
    permission_classes = [RolePermission]
