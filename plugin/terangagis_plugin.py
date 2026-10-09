"""Plugin TerangaGIS.

Fournit une action de menu/toolbar, un panneau de dialogue relié à l'agent et
démarre le bridge HTTP local utilisé pour l'exécution des outils SIG.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction, QDockWidget

PLUGIN_NAME = "TerangaGIS"


class TerangaGISPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock = None
        self.bridge = None
        self.bridge_info_cache = None
        self.agent = None
        self.orchestrator = None
        self.journal = None
        self.panel = None

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
            self.bridge_info_cache = info
            self._wire_agent()
            self._set_status(f"Connecteur prêt (127.0.0.1:{info['port']}).")
        except Exception as e:  # noqa: BLE001
            self.bridge = None
            self._set_status(f"Échec du démarrage du bridge : {e}")

    def _wire_agent(self):
        try:
            from common.config import load_settings
            from mcp.bridge_client import BridgeClient
            from plugin.agent.agent import GeoAgent
            from plugin.agent.journal import Journal
            from plugin.agent.orchestrator import Orchestrator
            client = BridgeClient(self.bridge.base_url, self.bridge.access_token)
            settings = load_settings()
            self.journal = Journal()
            self.agent = GeoAgent(journal=self.journal, parse_retries=1)
            self.orchestrator = Orchestrator(
                client,
                journal=self.journal,
            )
            self.orchestrator_defaults = {
                'max_retries': settings.step_max_retries,
                'backoff_base': settings.llm_backoff,
            }
            if self.panel is not None:
                self.panel.agent = self.agent
                self.panel.orchestrator = self.orchestrator
                self.panel.orchestrator_defaults = self.orchestrator_defaults
            self._set_status("Prêt. Saisissez une instruction en français.")
        except Exception as e:  # noqa: BLE001
            self.agent = None
            self.orchestrator = None
            self._set_status(f"Agent indisponible : {e}")

    def _create_dock(self):
        from plugin.ui.chat_panel import ChatPanel
        self.panel = ChatPanel(self.agent, self.orchestrator)
        self.panel._layer_crs_provider = self._layer_crs_map
        self.panel.context_provider = self._project_context

        self.dock = QDockWidget(PLUGIN_NAME, self.iface.mainWindow())
        self.dock.setObjectName("TerangaGISPanel")
        self.dock.setWidget(self.panel)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

    def _project_context(self) -> str:
        from plugin.agent.sanitization import sanitize_text
        layers = self._layer_crs_map()
        if not layers:
            return 'Aucune couche chargée dans le projet.'
        lines = [f'- {name} (CRS: {crs or "inconnu"})' for name, crs in list(layers.items())[:30]]
        return sanitize_text('Couches du projet :\n' + '\n'.join(lines), max_length=4000)

    def _layer_crs_map(self):
        try:
            from qgis.core import QgsProject
        except Exception:  # noqa: BLE001
            return {}
        mapping = {}
        for layer in QgsProject.instance().mapLayers().values():
            try:
                crs = layer.crs()
                if crs.isValid():
                    mapping[layer.name()] = crs.authid()
            except Exception:  # noqa: BLE001
                continue
        return mapping

    def _set_status(self, message):
        if self.panel is not None:
            self.panel.status.setText(message)

    def bridge_info(self):
        return self.bridge_info_cache

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
        if self.journal is not None:
            try:
                self.journal.close()
            except Exception:  # noqa: BLE001
                pass
            self.journal = None