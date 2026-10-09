"""Tests workflows réutilisables (S20)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from plugin.workflows_io import Workflow, WorkflowIO


def test_workflow_save_load():
    wf = Workflow(name="test", description="demo", instructions=["buffer routes", "clip villages"])
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "wf.json"
        WorkflowIO.save(wf, p)
        assert p.exists()
        loaded = WorkflowIO.load(p)
        assert loaded.name == "test"
        assert loaded.description == "demo"
        assert loaded.instructions == ["buffer routes", "clip villages"]


def test_workflow_load_defaults():
    data = {"name": "x", "instructions": []}
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "wf.json"
        with p.open('w', encoding='utf-8') as f:
            json.dump(data, f)
        loaded = WorkflowIO.load(p)
        assert loaded.name == "x"
        assert loaded.instructions == []
