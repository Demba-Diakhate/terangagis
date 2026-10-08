"""Construit le paquet installable du plugin TerangaGIS (S10).

Assemble une arborescence autonome et la compresse :

    dist/
    ├── terangagis/
    │   ├── metadata.txt
    │   ├── terangagis_plugin.py
    │   ├── ... (bridge, agent, geofunc, ui, workflows, core)
    │   ├── common/   (code partagé, embarqué)
    │   └── mcp/      (serveur MCP + client bridge, embarqués)
    └── terangagis-<version>.zip

Usage :
    python scripts/build_plugin.py [--dist DIR]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, 'plugin')
EXTRA_PACKAGES = ['common', 'mcp']
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '*.pyd')


def read_version(metadata_path: str) -> str:
    with open(metadata_path, 'r', encoding='utf-8') as fh:
        match = re.search(r'^version\s*=\s*(.+)$', fh.read(), re.MULTILINE)
    return match.group(1).strip() if match else '0.0.0'


def _copy_clean(src: str, dst: str) -> None:
    shutil.copytree(src, dst, ignore=IGNORE)


def build(dist_dir: str | None = None) -> str:
    dist_dir = dist_dir or os.path.join(ROOT, 'dist')
    staging_root = os.path.join(dist_dir, 'terangagis')
    version = read_version(os.path.join(PLUGIN_DIR, 'metadata.txt'))

    if os.path.exists(staging_root):
        shutil.rmtree(staging_root)
    os.makedirs(staging_root, exist_ok=True)

    # 1) contenu du plugin
    for entry in os.listdir(PLUGIN_DIR):
        if entry == '__pycache__':
            continue
        src = os.path.join(PLUGIN_DIR, entry)
        dst = os.path.join(staging_root, entry)
        if os.path.isdir(src):
            _copy_clean(src, dst)
        else:
            shutil.copy2(src, dst)

    # 2) paquets embarqués requis par le plugin
    for pkg in EXTRA_PACKAGES:
        _copy_clean(os.path.join(ROOT, pkg), os.path.join(staging_root, pkg))

    # 3) archive (dossier `terangagis/` à la racine du zip)
    zip_path = os.path.join(dist_dir, f'terangagis-{version}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for base, _dirs, files in os.walk(staging_root):
            for name in files:
                abs_path = os.path.join(base, name)
                rel = os.path.relpath(abs_path, staging_root)
                zf.write(abs_path, os.path.join('terangagis', rel))

    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Construire le paquet plugin TerangaGIS')
    parser.add_argument('--dist', default=None, help='répertoire de sortie (défaut: dist/)')
    args = parser.parse_args()
    zip_path = build(args.dist)
    print(f"Paquet créé : {zip_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())