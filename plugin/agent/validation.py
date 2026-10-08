"""Validation / dry-run d'un plan d'outils (RT3, RT6).

Sans dépendance QGIS : s'appuie sur les schémas d'outils et un contexte simple.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Set

from .agent import AgentPlan, AgentStep
from .tools_schema import TOOL_SCHEMAS

GEOGRAPHIC_EPSG = {'4326', '4269', '4258', '4171'}

METRIC_TOOLS = {'buffer', 'distance_analysis'}


@dataclass
class ValidationIssue:
    level: str  # 'error' | 'warning'
    code: str
    message: str
    step_index: int | None = None


@dataclass
class ValidationReport:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == 'error']

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == 'warning']

    @property
    def ok(self) -> bool:
        return not self.errors


def _is_geographic(crs: str | None) -> bool:
    if not crs:
        return False
    code = str(crs).split(':')[-1]
    return code in GEOGRAPHIC_EPSG


def validate_plan(
    plan: AgentPlan,
    layer_crs: Dict[str, str] | None = None,
    protected_sources: Iterable[str] | None = None,
) -> ValidationReport:
    """Valide un plan avant exécution.

    - `layer_crs` : {nom_couche: code_crs} pour les contrôles métriques.
    - `protected_sources` : chemins de sources du projet à ne pas écraser (RT6).
    """
    report = ValidationReport()
    layer_crs = layer_crs or {}
    protected = {str(p).lower() for p in (protected_sources or [])}

    if not plan.steps:
        report.issues.append(ValidationIssue('error', 'empty_plan', 'Le plan ne contient aucune étape.'))
        return report

    for idx, step in enumerate(plan.steps):
        schema = TOOL_SCHEMAS.get(step.tool)
        if schema is None:
            report.issues.append(ValidationIssue('error', 'unknown_tool', f"Outil inconnu : {step.tool}", idx))
            continue

        _validate_required(step, schema, idx, report)
        _validate_types(step, idx, report)
        _validate_output_target(step, protected, idx, report)
        _validate_metric_crs(step, layer_crs, idx, report)

    return report


def _validate_required(step: AgentStep, schema: Dict[str, Any], idx: int, report: ValidationReport) -> None:
    for req in schema.get('required', []):
        value = step.params.get(req)
        if value is None or value == '':
            report.issues.append(
                ValidationIssue('error', 'missing_param', f"Paramètre requis manquant : '{req}' pour {step.tool}.", idx)
            )


def _validate_types(step: AgentStep, idx: int, report: ValidationReport) -> None:
    if step.tool == 'buffer':
        distance = step.params.get('distance')
        try:
            if float(distance) <= 0:
                report.issues.append(
                    ValidationIssue('error', 'bad_distance', 'La distance du tampon doit être > 0.', idx)
                )
        except (TypeError, ValueError):
            report.issues.append(
                ValidationIssue('error', 'invalid_distance', 'La distance du tampon doit être numérique.', idx)
            )


def _validate_output_target(step: AgentStep, protected: Set[str], idx: int, report: ValidationReport) -> None:
    for key in ('output', 'path'):
        value = step.params.get(key)
        if value and str(value).lower() in protected:
            report.issues.append(
                ValidationIssue('error', 'output_overwrites_source',
                                f"La sortie '{value}' écrase une source du projet (RT6).", idx)
            )


def _validate_metric_crs(step: AgentStep, layer_crs: Dict[str, str], idx: int, report: ValidationReport) -> None:
    if step.tool not in METRIC_TOOLS:
        return
    layer = step.params.get('layer') or step.params.get('from')
    crs = layer_crs.get(layer) if layer else None
    if _is_geographic(crs):
        report.issues.append(ValidationIssue(
            'warning', 'geographic_crs',
            f"La couche '{layer}' est en CRS géographique ({crs}) : les distances seront en degrés. "
            f"Reprojeter en UTM est recommandé.",
            idx,
        ))