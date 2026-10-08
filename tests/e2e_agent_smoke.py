"""Test de bout en bout : instruction -> plan LLM (factice) -> validation -> exécution bridge (PyQGIS).

Usage :
    "C:/Program Files/QGIS 3.44.15/bin/python-qgis-ltr.bat" tests/e2e_agent_smoke.py

Le plan et l'orchestrateur tournent dans un thread worker pendant que le
thread principal pompe la boucle Qt (obligatoire pour le marshalling du bridge).
"""

import os
import threading
import time

os.environ.setdefault('TERANGA_OUTPUT_DIR', os.path.join(os.environ.get('TEMP', '.'), 'teranga_e2e'))


def main() -> int:
    try:
        from qgis.PyQt.QtWidgets import QApplication
        from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    except ImportError:
        print("SKIP: qgis non importable (lancer avec python-qgis-ltr.bat)")
        return 0

    app = QApplication.instance() or QApplication([])

    lyr = QgsVectorLayer('Point?crs=EPSG:32628&field=id:integer', 'pts', 'memory')
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(300000, 1600000)))
    feat.setAttributes([1])
    lyr.dataProvider().addFeatures([feat])
    lyr.updateExtents()
    QgsProject.instance().addMapLayer(lyr)

    from common.config import Settings
    from mcp.bridge_client import BridgeClient
    from plugin.agent.agent import GeoAgent
    from plugin.agent.journal import Journal
    from plugin.agent.llm import LLMClient
    from plugin.agent.orchestrator import Orchestrator
    from plugin.bridge.bridge import BridgeServer

    srv = BridgeServer()
    info = srv.start()

    def fake_transport(url, headers, body, timeout):
        return {"choices": [{"message": {
            "role": "assistant",
            "content": "Je crée un tampon de 1000 m.",
            "tool_calls": [{
                "id": "1", "type": "function",
                "function": {"name": "buffer", "arguments": '{"layer": "pts", "distance": 1000}'},
            }],
        }}]}

    settings = Settings(provider='openrouter', base_url='https://x/v1', api_key='test',
                        model='m', max_retries=0, timeout=5)
    from plugin.geofunc.paths import output_dir
    journal_path = os.path.join(output_dir(), f'e2e_{int(time.time() * 1000)}.sqlite')
    journal = Journal(journal_path)
    agent = GeoAgent(llm=LLMClient(settings=settings, transport=fake_transport), journal=journal)
    orchestrator = Orchestrator(BridgeClient(info['base_url'], info['token']), journal=journal)

    result = {}

    def worker():
        try:
            plan = agent.plan("fais un tampon de 1000 m autour de pts")
            result['plan'] = plan
            report, exec_report = orchestrator.run(plan, layer_crs={'pts': 'EPSG:32628'})
            result['report'] = report
            result['exec'] = exec_report
        except Exception as e:  # noqa: BLE001
            result['error'] = repr(e)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    deadline = time.time() + 60
    while t.is_alive() and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)

    srv.stop()
    app.quit()

    failures = []

    def check(name, cond, detail=''):
        print(f"{'PASS' if cond else 'FAIL'} {name}{(' — ' + str(detail)) if detail and not cond else ''}")
        if not cond:
            failures.append(name)

    plan = result.get('plan')
    report = result.get('report')
    exec_report = result.get('exec')
    check('worker_termine', not t.is_alive(), result.get('error'))
    check('plan_une_etape', plan is not None and len(plan.steps) == 1)
    check('plan_outil_buffer', bool(plan and plan.steps and plan.steps[0].tool == 'buffer'))
    check('validation_ok', report is not None and report.ok,
          [f'{i.code}:{i.message}' for i in (report.errors if report else [])])
    step_result = exec_report.steps[0].result if exec_report and exec_report.steps else {}
    check('execution_ok', exec_report is not None and exec_report.ok, step_result if not exec_report or not exec_report.ok else '')
    output = (exec_report.steps[0].result or {}).get('data', {}).get('output') if exec_report and exec_report.steps else None
    check('fichier_sortie', bool(output) and os.path.exists(output), output)
    check('journal_execution', journal.count('execution') == 1)
    journal.close()

    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())