"""Journal SQLite des interactions et exécutions (RT4)."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Any


class Journal:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(
            os.environ.get('TEMP') or os.getcwd(), 'terangagis_journal.sqlite'
        )
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute(
            'CREATE TABLE IF NOT EXISTS events ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'ts REAL NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)'
        )
        self._conn.commit()

    def _record(self, kind: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                'INSERT INTO events (ts, kind, payload) VALUES (?, ?, ?)',
                (time.time(), kind, json.dumps(payload, ensure_ascii=False)),
            )
            self._conn.commit()

    def record_llm(self, prompt: Any, response: Any) -> None:
        self._record('llm', {'prompt': prompt, 'response': response})

    def record_plan(self, plan: Any) -> None:
        steps = [{'tool': s.tool, 'params': s.params} for s in getattr(plan, 'steps', [])]
        self._record('plan', {'steps': steps})

    def record_execution(
        self,
        tool: str,
        params: dict[str, Any],
        result: Any,
        attempts: int = 1,
        error_class: str = '',
    ) -> None:
        payload: dict[str, Any] = {'tool': tool, 'params': params, 'result': result}
        if attempts != 1:
            payload['attempts'] = attempts
        if error_class:
            payload['error_class'] = error_class
        self._record('execution', payload)

    def record_validation(self, report: Any) -> None:
        issues = [
            {'level': i.level, 'code': i.code, 'message': i.message, 'step': i.step_index}
            for i in getattr(report, 'issues', [])
        ]
        self._record('validation', {'ok': getattr(report, 'ok', None), 'issues': issues})

    def count(self, kind: str | None = None) -> int:
        if kind:
            cur = self._conn.execute('SELECT COUNT(*) FROM events WHERE kind = ?', (kind,))
        else:
            cur = self._conn.execute('SELECT COUNT(*) FROM events')
        return int(cur.fetchone()[0])

    def recent(self, kind: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Retourne les derniers événements (du plus récent au plus ancien)."""
        if kind:
            cur = self._conn.execute(
                'SELECT id, ts, kind, payload FROM events WHERE kind = ? '
                'ORDER BY id DESC LIMIT ?', (kind, limit),
            )
        else:
            cur = self._conn.execute(
                'SELECT id, ts, kind, payload FROM events ORDER BY id DESC LIMIT ?', (limit,),
            )
        events = []
        for row in cur.fetchall():
            events.append({
                'id': row[0], 'ts': row[1], 'kind': row[2],
                'payload': json.loads(row[3]),
            })
        return events

    def export(self, path: str, kind: str | None = None) -> str:
        """Exporte le journal (JSON) vers un fichier et retourne le chemin."""
        events = self.recent(kind=kind, limit=10_000)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(events, fh, ensure_ascii=False, indent=2)
        return path

    def close(self) -> None:
        self._conn.close()