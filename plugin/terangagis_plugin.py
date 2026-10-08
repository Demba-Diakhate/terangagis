"""Plugin TerangaGIS — squelette minimal (Sprint 0).

Fournit une action de menu/toolbar et un panneau latéral vide.
Le chat, le bridge HTTP et l'agent sont implémentés aux sprints suivants.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QLabel, QVBoxLayout, QWidget

PLUGIN_NAME = "TerangaGIS"


class TerangaGISPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock = None

    def initGui(self):
        self.action = QAction(PLUGIN_NAME, self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle_panel)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(PLUGIN_NAME, self.action)
        self._create_dock()
        self.dock.hide()

    def _create_dock(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        label = QLabel(
            "TerangaGIS\n\n"
            "Sprint 0 : squelette du plugin.\n"
            "Le chat et le plan apparaîtront au Sprint 6."
        )
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.dock = QDockWidget(PLUGIN_NAME, self.iface.mainWindow())
        self.dock.setObjectName("TerangaGISPanel")
        self.dock.setWidget(container)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

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
        if self.action is not None:
            self.iface.removePluginMenu(PLUGIN_NAME, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.dock is not None:
            self.dock.close()
            self.iface.mainWindow().removeDockWidget(self.dock)
            self.dock = None
