from rest_framework import generics
from rest_framework.exceptions import ValidationError

from dispositivos.models import Dispositivo

from .models import Area, Proceso, Subproceso
from .serializers import AreaSerializer, DispositivoZonaSerializer, ProcesoSerializer, SubprocesoSerializer
from usuarios.permissions import RolePermission


class ProcesoListCreateAPIView(generics.ListCreateAPIView):
    queryset = Proceso.objects.all().order_by('nombre')
    serializer_class = ProcesoSerializer
    permission_classes = [RolePermission]


class ProcesoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Proceso.objects.all()
    serializer_class = ProcesoSerializer
    permission_classes = [RolePermission]

    def perform_destroy(self, instance):
        if instance.divisiones.exists() or instance.zonas.exists():
            raise ValidationError('Primero elimina las divisiones y relaciones de esta distribución.')
        instance.delete()


class SubprocesoListCreateAPIView(generics.ListCreateAPIView):
    queryset = Subproceso.objects.select_related('proceso').all().order_by('nombre')
    serializer_class = SubprocesoSerializer
    permission_classes = [RolePermission]


class SubprocesoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Subproceso.objects.select_related('proceso').all()
    serializer_class = SubprocesoSerializer
    permission_classes = [RolePermission]

    def perform_destroy(self, instance):
        if instance.zonas.exists():
            raise ValidationError('Primero elimina las zonas de esta división.')
        instance.delete()


class AreaListAPIView(generics.ListCreateAPIView):
    queryset = Area.objects.select_related('subproceso', 'subproceso__proceso').all().order_by('nombre')
    serializer_class = AreaSerializer
    permission_classes = [RolePermission]


class AreaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Area.objects.select_related('subproceso', 'subproceso__proceso').all()
    serializer_class = AreaSerializer
    permission_classes = [RolePermission]

    def perform_destroy(self, instance):
        if (
            instance.dispositivos.exists()
            or instance.trabajadores.exists()
            or instance.procesos_zona.exists()
        ):
            raise ValidationError(
                'No se puede eliminar: primero quita las terminales, trabajadores y relaciones asignadas a esta zona.'
            )
        instance.delete()


class ZonaDispositivoListAPIView(generics.ListAPIView):
    queryset = Dispositivo.objects.select_related('area', 'area__subproceso', 'area__subproceso__proceso').all().order_by('id')
    serializer_class = DispositivoZonaSerializer
    permission_classes = [RolePermission]


class ZonaDispositivoDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Dispositivo.objects.select_related('area', 'area__subproceso', 'area__subproceso__proceso').all()
    serializer_class = DispositivoZonaSerializer
    permission_classes = [RolePermission]
