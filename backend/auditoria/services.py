"""Servicio común para registrar acciones administrativas en la bitácora."""

from .models import Auditoria


def record_action(request, action, module, affected='', description=''):
    """Guarda la acción con el usuario autenticado y la dirección de origen."""
    user = request.user if getattr(request.user, 'is_authenticated', False) else None
    ip = request.META.get('REMOTE_ADDR')
    return Auditoria.objects.create(
        usuario=user,
        accion=action,
        modulo=module,
        registro_afectado=str(affected),
        descripcion=description,
        ip=ip,
    )