"""Tests de la classification d'erreurs et du backoff (S12). Purs, sans QGIS."""
from __future__ import annotations

from plugin.agent.retry import (
    PERMANENT,
    TRANSIENT,
    UNKNOWN,
    backoff_seconds,
    classify_error,
    is_retryable,
)


def test_classify_transient_codes():
    assert classify_error({'code': 'tool_exception'}) == TRANSIENT
    assert classify_error({'code': 'internal'}) == TRANSIENT
    assert classify_error({'code': 'rate_limited'}) == TRANSIENT
    assert classify_error({'code': 'client_error'}) == TRANSIENT


def test_classify_permanent_codes():
    assert classify_error({'code': 'layer_not_found'}) == PERMANENT
    assert classify_error({'code': 'missing_param'}) == PERMANENT
    assert classify_error({'code': 'unknown_tool'}) == PERMANENT


def test_classify_string_and_object_and_empty():
    assert classify_error('timeout') == TRANSIENT
    assert classify_error('layer_not_found') == PERMANENT
    assert classify_error('autre') == UNKNOWN
    assert classify_error(None) == UNKNOWN
    assert classify_error({}) == UNKNOWN

    class _Err:
        code = 'internal'

    assert classify_error(_Err()) == TRANSIENT


def test_is_retryable():
    assert is_retryable({'code': 'server_error'}) is True
    assert is_retryable({'code': 'bad_distance'}) is False
    assert is_retryable({'code': 'inconnu'}) is False


def test_backoff_is_exponential_and_capped():
    assert backoff_seconds(1, base=0.5) == 0.5
    assert backoff_seconds(2, base=0.5) == 1.0
    assert backoff_seconds(3, base=0.5) == 2.0
    assert backoff_seconds(10, base=0.5, cap=8.0) == 8.0
    assert backoff_seconds(0, base=0.5) == 0.5


def test_backoff_jitter_within_bounds():
    for _ in range(20):
        delay = backoff_seconds(1, base=1.0, jitter=0.5)
        assert 1.0 <= delay <= 1.5
