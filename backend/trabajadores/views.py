from rest_framework import generics, permissions

from .models import Trabajador
from .serializers import TrabajadorSerializer
from usuarios.permissions import RolePermission
from auditoria.services import record_action


class TrabajadorListCreateAPIView(generics.ListCreateAPIView):
    queryset = Trabajador.objects.select_related('area').all()
    serializer_class = TrabajadorSerializer
    permission_classes = [RolePermission]

    def perform_create(self, serializer):
        worker = serializer.save()
        record_action(self.request, 'CREAR', 'trabajadores', worker.pk, 'Trabajador creado')


class TrabajadorDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Trabajador.objects.select_related('area').all()
    serializer_class = TrabajadorSerializer
    permission_classes = [RolePermission]

    def perform_update(self, serializer):
        worker = serializer.save()
        record_action(self.request, 'MODIFICAR', 'trabajadores', worker.pk, 'Trabajador modificado')

    def perform_destroy(self, instance):
        record_action(self.request, 'ELIMINAR', 'trabajadores', instance.pk, 'Trabajador eliminado')
        instance.delete()
