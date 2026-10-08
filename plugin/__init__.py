"""Package plugin QGIS TerangaGIS."""


def classFactory(iface):
    """Point d'entrée standard du plugin QGIS."""
    from .terangagis_plugin import TerangaGISPlugin

    return TerangaGISPlugin(iface)
