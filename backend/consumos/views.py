from rest_framework import generics, permissions

from .models import Consumo
from .serializers import ConsumoSerializer
from usuarios.permissions import RolePermission


class ConsumoListAPIView(generics.ListAPIView):
    queryset = Consumo.objects.select_related('dispositivo', 'sim').all()
    serializer_class = ConsumoSerializer
    permission_classes = [RolePermission]


class ConsumoDetailAPIView(generics.RetrieveAPIView):
    queryset = Consumo.objects.select_related('dispositivo', 'sim').all()
    serializer_class = ConsumoSerializer
    permission_classes = [RolePermission]
