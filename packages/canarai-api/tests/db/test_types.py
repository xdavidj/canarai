"""Tests for canarai.db.types.JSONType custom SQLAlchemy column type."""

import json

import pytest

from canarai.db.types import JSONType


# The dialect parameter is not used by JSONType, so None is a valid stand-in.
DIALECT = None


class TestJSONTypeBindParam:
    """Tests for JSONType.process_bind_param (Python -> DB)."""

    def setup_method(self):
        self.jtype = JSONType()

    def test_dict_serialised_to_json_string(self):
        value = {"key": "value", "number": 42}
        result = self.jtype.process_bind_param(value, DIALECT)
        assert isinstance(result, str)
        assert json.loads(result) == value

    def test_list_serialised_to_json_string(self):
        value = [1, "two", 3.0, True, None]
        result = self.jtype.process_bind_param(value, DIALECT)
        assert isinstance(result, str)
        assert json.loads(result) == value

    def test_none_returns_none(self):
        assert self.jtype.process_bind_param(None, DIALECT) is None

    def test_nested_structure_serialised(self):
        value = {"outer": {"inner": [1, 2, {"deep": True}]}}
        result = self.jtype.process_bind_param(value, DIALECT)
        assert json.loads(result) == value

    def test_empty_dict_serialised(self):
        result = self.jtype.process_bind_param({}, DIALECT)
        assert result == "{}"

    def test_empty_list_serialised(self):
        result = self.jtype.process_bind_param([], DIALECT)
        assert result == "[]"


class TestJSONTypeResultValue:
    """Tests for JSONType.process_result_value (DB -> Python)."""

    def setup_method(self):
        self.jtype = JSONType()

    def test_json_string_deserialised_to_dict(self):
        raw = '{"key": "value", "number": 42}'
        result = self.jtype.process_result_value(raw, DIALECT)
        assert result == {"key": "value", "number": 42}

    def test_none_returns_none(self):
        assert self.jtype.process_result_value(None, DIALECT) is None

    def test_json_array_string_deserialised_to_list(self):
        raw = '[1, 2, 3]'
        result = self.jtype.process_result_value(raw, DIALECT)
        assert result == [1, 2, 3]


class TestJSONTypeRoundtrip:
    """Tests that bind -> result is a perfect roundtrip."""

    def setup_method(self):
        self.jtype = JSONType()

    def test_dict_roundtrip(self):
        original = {"enabled_tests": ["CAN-0001", "CAN-0002"], "threshold": 0.75}
        bound = self.jtype.process_bind_param(original, DIALECT)
        restored = self.jtype.process_result_value(bound, DIALECT)
        assert restored == original

    def test_nested_roundtrip(self):
        original = {"nested": {"list": [True, False, None], "count": 3}}
        bound = self.jtype.process_bind_param(original, DIALECT)
        restored = self.jtype.process_result_value(bound, DIALECT)
        assert restored == original

    def test_none_roundtrip(self):
        bound = self.jtype.process_bind_param(None, DIALECT)
        restored = self.jtype.process_result_value(bound, DIALECT)
        assert restored is None
