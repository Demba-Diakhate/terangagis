"""Smoke du plugin TerangaGIS (démarrage/arrêt du bridge) avec une iface factice.

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/plugin_smoke.py
"""


class _FakeIface:
    def __init__(self, main_window):
        self._main = main_window

    def mainWindow(self):
        return self._main

    def addToolBarIcon(self, action):
        return None

    def addPluginToMenu(self, name, action):
        return None

    def addDockWidget(self, area, dock):
        self._main.addDockWidget(area, dock)

    def removePluginMenu(self, name, action):
        return None

    def removeToolBarIcon(self, action):
        return None


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication, QMainWindow
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])
    from plugin.terangagis_plugin import TerangaGISPlugin

    plugin = TerangaGISPlugin(iface=_FakeIface(QMainWindow()))

    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    plugin.initGui()
    check('bridge_demarre', plugin.bridge is not None)
    info = plugin.bridge_info()
    check('bridge_info', bool(info) and info.get('base_url', '').startswith('http://127.0.0.1:') and bool(info.get('token')), info)
    check('dock_cree', plugin.dock is not None)
    check('panneau_chat', plugin.panel is not None and hasattr(plugin.panel, 'input'))
    check('agent_branche', plugin.agent is not None and plugin.orchestrator is not None)

    plugin.unload()
    check('bridge_arrete', plugin.bridge is None)

    app.quit()
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())