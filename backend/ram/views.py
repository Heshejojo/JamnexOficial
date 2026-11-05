from rest_framework import generics

from usuarios.permissions import RolePermission

from .models import RegistroRam
from .serializers import RegistroRamSerializer


class RegistroRamListAPIView(generics.ListCreateAPIView):
    queryset = RegistroRam.objects.select_related('dispositivo').all().order_by('-fecha_hora')
    serializer_class = RegistroRamSerializer
    permission_classes = [RolePermission]


class RegistroRamDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RegistroRam.objects.all()
    serializer_class = RegistroRamSerializer
    permission_classes = [RolePermission]
