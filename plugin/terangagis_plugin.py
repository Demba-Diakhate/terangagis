"""Plugin TerangaGIS.

Fournit une action de menu/toolbar, un panneau latéral et démarre le bridge
HTTP local utilisé par l'agent (S06 ajoutera l'interface de dialogue).
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QLabel, QVBoxLayout, QWidget

PLUGIN_NAME = "TerangaGIS"


class TerangaGISPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock = None
        self.bridge = None
        self.status_label = None

    def initGui(self):
        self.action = QAction(PLUGIN_NAME, self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle_panel)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(PLUGIN_NAME, self.action)
        self._create_dock()
        self.dock.hide()
        self._start_bridge()

    def _start_bridge(self):
        try:
            from plugin.bridge.bridge import BridgeServer
        except Exception as e:  # noqa: BLE001
            self._set_status(f"Bridge indisponible : {e}")
            return
        try:
            self.bridge = BridgeServer()
            info = self.bridge.start()
            self._set_status(
                f"Connecteur prêt sur 127.0.0.1:{info['port']}.\n"
                "Le dialogue en langage naturel arrive au Sprint 6."
            )
        except Exception as e:  # noqa: BLE001
            self.bridge = None
            self._set_status(f"Échec du démarrage du bridge : {e}")

    def _create_dock(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        self.status_label = QLabel(
            "TerangaGIS\n\nInitialisation du connecteur…"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.dock = QDockWidget(PLUGIN_NAME, self.iface.mainWindow())
        self.dock.setObjectName("TerangaGISPanel")
        self.dock.setWidget(container)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

    def bridge_info(self):
        if self.bridge is None:
            return None
        return {'base_url': self.bridge.base_url, 'token': self.bridge.access_token}

    def toggle_panel(self, checked=False):
        if self.dock is None:
            return
        if self.dock.isVisible() and checked:
            self.dock.hide()
        else:
            self.dock.show()
            self.dock.raise_()
        if self.action is not None:
            self.action.setChecked(self.dock.isVisible())

    def unload(self):
        if self.bridge is not None:
            try:
                self.bridge.stop()
            except Exception:  # noqa: BLE001
                pass
            self.bridge = None
        if self.action is not None:
            self.iface.removePluginMenu(PLUGIN_NAME, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.dock is not None:
            self.dock.close()
            self.iface.mainWindow().removeDockWidget(self.dock)
            self.dock = None

    def _set_status(self, message):
        if self.status_label is not None:
            self.status_label.setText(f"{PLUGIN_NAME}\n\n{message}")