from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

required = [
    ROOT / 'backend',
    ROOT / 'backend' / 'config',
    ROOT / 'backend' / 'usuarios',
    ROOT / 'backend' / 'trabajadores',
    ROOT / 'backend' / 'dispositivos',
    ROOT / 'backend' / 'sims',
    ROOT / 'backend' / 'consumos',
    ROOT / 'backend' / 'redes',
    ROOT / 'backend' / 'reportes',
    ROOT / 'frontend',
    ROOT / 'frontend' / 'src',
    ROOT / 'mobile',
    ROOT / 'mobile' / 'lib',
    ROOT / 'docs',
]

missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit(f'Faltan carpetas requeridas: {missing}')

print('Estructura base verificada correctamente.')
