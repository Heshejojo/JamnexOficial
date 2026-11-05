from rest_framework import generics

from usuarios.permissions import RolePermission

from .models import RegistroAlmacenamiento
from .serializers import RegistroAlmacenamientoSerializer


class RegistroAlmacenamientoListAPIView(generics.ListCreateAPIView):
    queryset = RegistroAlmacenamiento.objects.select_related('dispositivo').all().order_by('-fecha_hora')
    serializer_class = RegistroAlmacenamientoSerializer
    permission_classes = [RolePermission]


class RegistroAlmacenamientoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RegistroAlmacenamiento.objects.all()
    serializer_class = RegistroAlmacenamientoSerializer
    permission_classes = [RolePermission]
