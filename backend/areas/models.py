from django.db import models


class Area(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'areas'

    def __str__(self):
        return self.nombre


class Proceso(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'procesos'

    def __str__(self):
        return self.nombre


class ProcesoZona(models.Model):
    proceso = models.ForeignKey(
        Proceso,
        on_delete=models.CASCADE,
        related_name='zonas',
    )
    zona = models.CharField(max_length=120)

    class Meta:
        db_table = 'procesos_zona'
        constraints = [
            models.UniqueConstraint(
                fields=['proceso', 'zona'],
                name='uq_proceso_zona',
            ),
        ]

    def __str__(self):
        return f'{self.proceso} - {self.zona}'


class Subproceso(models.Model):
    proceso_zona = models.ForeignKey(
        ProcesoZona,
        on_delete=models.CASCADE,
        related_name='subprocesos',
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'subprocesos'
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_zona', 'nombre'],
                name='uq_subproceso_proceso_zona_nombre',
            ),
        ]

    def __str__(self):
        return self.nombre


class AreaProcesoZona(models.Model):
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name='procesos_zona',
    )
    proceso_zona = models.ForeignKey(
        ProcesoZona,
        on_delete=models.CASCADE,
        related_name='areas',
    )

    class Meta:
        db_table = 'areas_procesos_zona'
        constraints = [
            models.UniqueConstraint(
                fields=['area', 'proceso_zona'],
                name='uq_area_proceso_zona',
            ),
        ]

    def __str__(self):
        return f'{self.area} - {self.proceso_zona}'
