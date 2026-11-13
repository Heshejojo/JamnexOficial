from rest_framework import generics

from dispositivos.models import Dispositivo

from .models import Area, Proceso, Subproceso
from .serializers import AreaSerializer, DispositivoZonaSerializer, ProcesoSerializer, SubprocesoSerializer
from usuarios.permissions import RolePermission


class ProcesoListCreateAPIView(generics.ListCreateAPIView):
    queryset = Proceso.objects.all().order_by('nombre')
    serializer_class = ProcesoSerializer
    permission_classes = [RolePermission]


class ProcesoDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Proceso.objects.all()
    serializer_class = ProcesoSerializer
    permission_classes = [RolePermission]


class SubprocesoListCreateAPIView(generics.ListCreateAPIView):
    queryset = Subproceso.objects.select_related('proceso').all().order_by('nombre')
    serializer_class = SubprocesoSerializer
    permission_classes = [RolePermission]


class SubprocesoDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Subproceso.objects.select_related('proceso').all()
    serializer_class = SubprocesoSerializer
    permission_classes = [RolePermission]


class AreaListAPIView(generics.ListCreateAPIView):
    queryset = Area.objects.select_related('subproceso', 'subproceso__proceso').all().order_by('nombre')
    serializer_class = AreaSerializer
    permission_classes = [RolePermission]


class AreaDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Area.objects.select_related('subproceso', 'subproceso__proceso').all()
    serializer_class = AreaSerializer
    permission_classes = [RolePermission]


class ZonaDispositivoListAPIView(generics.ListAPIView):
    queryset = Dispositivo.objects.select_related('area', 'area__subproceso', 'area__subproceso__proceso').all().order_by('id')
    serializer_class = DispositivoZonaSerializer
    permission_classes = [RolePermission]


class ZonaDispositivoDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Dispositivo.objects.select_related('area', 'area__subproceso', 'area__subproceso__proceso').all()
    serializer_class = DispositivoZonaSerializer
    permission_classes = [RolePermission]
