from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario, Rol


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'descripcion', 'activo']


class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'rol',
            'activo', 'permisos', 'is_superuser', 'ultimo_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'ultimo_login', 'is_superuser']


class UsuarioAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    rol_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password', 'rol_id', 'activo', 'is_staff', 'permisos']

    def validate_permisos(self, value):
        base = {
            'dashboard': False,
            'dispositivos': False,
            'sims': False,
            'usuarios': False,
            'zonas': False,
        }
        if not isinstance(value, dict):
            raise serializers.ValidationError('Permisos inválidos.')
        return {key: bool(value.get(key, False)) for key in base}

    def validate_rol_id(self, value):
        if value is not None and not Rol.objects.filter(
            pk=value, nombre__in=['ADMIN', 'CONSULTA'], activo=True
        ).exists():
            raise serializers.ValidationError('Solo se permite el rol ADMIN o CONSULTA.')
        return value

    def _role(self, role_id):
        role = None
        if role_id is not None:
            role = Rol.objects.filter(
                pk=role_id,
                nombre__in=['ADMIN', 'CONSULTA'],
                activo=True,
            ).first()
        else:
            role = Rol.objects.filter(nombre__iexact='ADMIN', activo=True).first()
        if not role:
            raise serializers.ValidationError({'rol_id': 'No existe un rol ADMIN o CONSULTA activo.'})
        return role

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        role_id = validated_data.pop('rol_id', None)
        user = Usuario(**validated_data, rol=self._role(role_id))
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        role_id = validated_data.pop('rol_id', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.rol = self._role(role_id)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=False, allow_blank=False)
    email = serializers.CharField(required=False, allow_blank=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get('identifier') or attrs.get('email')
        password = attrs.get('password')

        user = None

        if identifier:
            user = Usuario.objects.filter(email__iexact=identifier).first()
            if not user:
                user = Usuario.objects.filter(username__iexact=identifier).first()
            if user and not user.check_password(password):
                user = None

        if not user:
            user = authenticate(username=identifier, password=password)

        if not user:
            user = authenticate(email=identifier, password=password)

        if not user:
            raise serializers.ValidationError('Credenciales inválidas.')

        refresh = RefreshToken.for_user(user)
        return {
            'user': UsuarioSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
