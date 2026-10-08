"""Package plugin QGIS TerangaGIS.

Le plugin est **relocalisable** : il fonctionne aussi bien en développement
(paquet `plugin`) qu'installé dans QGIS sous le nom `terangagis`. Les paquets
`common` et `mcp` sont embarqués dans le dossier du plugin lors du packaging
(voir `scripts/build_plugin.py`).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# Le dossier du plugin (pour `common`/`mcp` embarqués) et son parent.
for _path in (_HERE, os.path.dirname(_HERE)):
    if _path not in sys.path:
        sys.path.append(_path)

# Alias : les imports internes `plugin.*` résolvent vers ce paquet, quel que
# soit le nom d'installation (`plugin` en dev, `terangagis` dans QGIS).
sys.modules.setdefault('plugin', sys.modules[__name__])


def classFactory(iface):
    """Point d'entrée standard du plugin QGIS."""
    from .terangagis_plugin import TerangaGISPlugin

    return TerangaGISPlugin(iface)
