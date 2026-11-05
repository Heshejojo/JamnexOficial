from rest_framework import generics, permissions

from .models import Area
from .serializers import AreaSerializer
from usuarios.permissions import RolePermission


class AreaListAPIView(generics.ListCreateAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [RolePermission]


class AreaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [RolePermission]
