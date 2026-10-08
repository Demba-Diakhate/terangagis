from plugin.agent.sanitization import (
    sanitize_mapping,
    sanitize_text,
    sanitize_value,
)


def test_truncates_long_strings():
    out = sanitize_text('x' * 500, max_length=10)
    assert out == 'x' * 10 + '…'


def test_removes_control_chars():
    assert sanitize_text('a\x00b\x1fc') == 'abc'


def test_neutralizes_secrets():
    assert '[secret]' in sanitize_text('token: abc123def')
    assert '[secret]' in sanitize_text('Bearer abc.def-ghi_123')
    assert '[secret]' in sanitize_text('clé sk-ABCDEFGH1234')


def test_value_preserves_numbers_and_none():
    assert sanitize_value(42) == 42
    assert sanitize_value(3.14) == 3.14
    assert sanitize_value(True) is True
    assert sanitize_value(None) is None


def test_mapping_recurses_and_caps():
    data = {'name': 'a' * 300, 'nested': {'secret': 'token=xyz12345'}}
    out = sanitize_mapping(data)
    assert out['name'].endswith('…')
    assert '[secret]' in out['nested']['secret']


def test_limits_list_items():
    out = sanitize_value([str(i) for i in range(200)])
    assert len(out) == 50