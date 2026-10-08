"""Smoke du packaging (S10) : construction du zip et vérification du contenu.

Vérifie que l'archive contient l'arborescence autonome attendue, puis (sous
QGIS) que le plugin est importable sous le nom `terangagis` (relocalisable).

Usage :
    python tests/packaging_smoke.py
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/packaging_smoke.py
"""
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

REQUIRED = [
    'terangagis/metadata.txt',
    'terangagis/__init__.py',
    'terangagis/terangagis_plugin.py',
    'terangagis/common/config.py',
    'terangagis/mcp/server.py',
    'terangagis/mcp/bridge_client.py',
    'terangagis/agent/agent.py',
    'terangagis/geofunc/catalog.py',
    'terangagis/ui/chat_panel.py',
    'terangagis/workflows/definitions.py',
    'terangagis/icon.png',
]


def main() -> int:
    from scripts.build_plugin import build, read_version

    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = build(dist_dir=tmp)
        check('zip_cree', os.path.exists(zip_path), zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
        for required in REQUIRED:
            check(f'contient_{required}', required in names)
        check('pas_de_pycache', not any('__pycache__' in n for n in names))
        version = read_version(os.path.join(ROOT, 'plugin', 'metadata.txt'))
        check('nom_avec_version', zip_path.endswith(f'terangagis-{version}.zip'), zip_path)

        # Relocalisation : le plugin doit s'importer sous le nom `terangagis`.
        staging = os.path.join(tmp, 'terangagis')
        if os.path.isdir(staging):
            sys.path.insert(0, tmp)
            try:
                import importlib
                module = importlib.import_module('terangagis')
                check('import_terangagis', hasattr(module, 'classFactory'))
            except Exception as e:  # noqa: BLE001
                check('import_terangagis', False, e)

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())