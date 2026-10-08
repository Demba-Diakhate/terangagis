"""Exécution d'un workflow sur un projet QGIS (S08).

Enchaîne les étapes d'un plan, charge chaque sortie dans le projet sous le nom
dérivé de son fichier (pour que les étapes suivantes puissent la référencer),
puis s'arrête à la première erreur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .definitions import Workflow, layer_name_from_path


@dataclass
class WorkflowStepResult:
    tool: str
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowReport:
    workflow: str
    steps: List[WorkflowStepResult] = field(default_factory=list)
    stopped_on_error: bool = False

    @property
    def ok(self) -> bool:
        return bool(self.steps) and all(s.ok for s in self.steps)

    @property
    def outputs(self) -> List[str]:
        paths = []
        for step in self.steps:
            data = step.data or {}
            produced = data.get('output') or data.get('path')
            if produced:
                paths.append(produced)
        return paths


def _default_run_tool(name: str, params: Dict[str, Any]):
    from ..geofunc.catalog import run_tool
    return run_tool(name, params)


def _load_layer_into_project(name: str, path: str) -> None:
    from qgis.core import QgsProject, QgsVectorLayer
    project = QgsProject.instance()
    if project.mapLayersByName(name):
        return
    import os
    if not path or not os.path.exists(path):
        return
    layer = QgsVectorLayer(path, name, 'ogr')
    if layer.isValid():
        project.addMapLayer(layer)


def execute_workflow(
    workflow: Workflow,
    layers: Dict[str, str],
    out_dir: str,
    *,
    run_tool: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
    load_layer: Optional[Callable[[str, str], None]] = None,
    stop_on_error: bool = True,
) -> WorkflowReport:
    plan = workflow.build(layers, out_dir)
    run = run_tool or _default_run_tool
    loader = load_layer if load_layer is not None else _load_layer_into_project

    report = WorkflowReport(workflow=workflow.key)
    for step in plan.steps:
        try:
            result = run(step.tool, step.params)
        except Exception as e:  # noqa: BLE001
            report.steps.append(WorkflowStepResult(
                step.tool, False, error={'code': 'tool_exception', 'message': str(e)},
            ))
            report.stopped_on_error = True
            break

        ok = bool(getattr(result, 'ok', False))
        data = getattr(result, 'data', None)
        error = getattr(result, 'error', None)
        report.steps.append(WorkflowStepResult(step.tool, ok, data, error))

        if ok and data:
            produced = data.get('output') or data.get('path')
            if produced:
                loader(layer_name_from_path(produced), produced)

        if not ok and stop_on_error:
            report.stopped_on_error = True
            break

    return report