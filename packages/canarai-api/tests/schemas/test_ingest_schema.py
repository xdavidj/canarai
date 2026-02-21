"""Tests for Pydantic validation in canarai.schemas.ingest."""

import pytest
from pydantic import ValidationError

from canarai.schemas.ingest import DetectionData, IngestPayload, TestResultData


# ---------------------------------------------------------------------------
# DetectionData
# ---------------------------------------------------------------------------


class TestDetectionData:
    """Tests for DetectionData schema validation."""

    def test_valid_defaults(self):
        d = DetectionData()
        assert d.confidence == 0.0
        assert d.classification == "human"
        assert d.agent_family is None
        assert d.signals == {}

    def test_confidence_lower_bound_accepted(self):
        d = DetectionData(confidence=0.0)
        assert d.confidence == 0.0

    def test_confidence_upper_bound_accepted(self):
        d = DetectionData(confidence=1.0)
        assert d.confidence == 1.0

    def test_confidence_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            DetectionData(confidence=-0.1)

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError):
            DetectionData(confidence=1.1)

    def test_classification_human_accepted(self):
        d = DetectionData(classification="human")
        assert d.classification == "human"

    def test_classification_suspected_agent_accepted(self):
        d = DetectionData(classification="suspected_agent")
        assert d.classification == "suspected_agent"

    def test_classification_likely_agent_accepted(self):
        d = DetectionData(classification="likely_agent")
        assert d.classification == "likely_agent"

    def test_classification_confirmed_agent_accepted(self):
        d = DetectionData(classification="confirmed_agent")
        assert d.classification == "confirmed_agent"

    def test_classification_invalid_rejected(self):
        with pytest.raises(ValidationError):
            DetectionData(classification="robot")

    def test_agent_family_optional_none(self):
        d = DetectionData(agent_family=None)
        assert d.agent_family is None

    def test_agent_family_string_accepted(self):
        d = DetectionData(agent_family="openai")
        assert d.agent_family == "openai"


# ---------------------------------------------------------------------------
# TestResultData
# ---------------------------------------------------------------------------


class TestTestResultData:
    """Tests for TestResultData schema validation."""

    _BASE = {
        "test_id": "CAN-0001",
        "delivery_method": "html_comment",
        "outcome": "ignored",
    }

    def _make(self, **overrides) -> TestResultData:
        return TestResultData(**{**self._BASE, **overrides})

    def test_valid_test_id_accepted(self):
        d = self._make(test_id="CAN-0001")
        assert d.test_id == "CAN-0001"

    def test_test_id_too_few_digits_rejected(self):
        with pytest.raises(ValidationError):
            self._make(test_id="CAN-001")

    def test_test_id_too_many_digits_rejected(self):
        with pytest.raises(ValidationError):
            self._make(test_id="CAN-00001")

    def test_test_id_lowercase_prefix_rejected(self):
        with pytest.raises(ValidationError):
            self._make(test_id="can-0001")

    def test_test_id_no_prefix_rejected(self):
        with pytest.raises(ValidationError):
            self._make(test_id="0001")

    def test_outcome_exfiltration_attempted_accepted(self):
        d = self._make(outcome="exfiltration_attempted")
        assert d.outcome == "exfiltration_attempted"

    def test_outcome_full_compliance_accepted(self):
        d = self._make(outcome="full_compliance")
        assert d.outcome == "full_compliance"

    def test_outcome_partial_compliance_accepted(self):
        d = self._make(outcome="partial_compliance")
        assert d.outcome == "partial_compliance"

    def test_outcome_acknowledged_accepted(self):
        d = self._make(outcome="acknowledged")
        assert d.outcome == "acknowledged"

    def test_outcome_ignored_accepted(self):
        d = self._make(outcome="ignored")
        assert d.outcome == "ignored"

    def test_outcome_invalid_rejected(self):
        with pytest.raises(ValidationError):
            self._make(outcome="unknown")

    def test_delivery_method_max_64_chars_accepted(self):
        d = self._make(delivery_method="x" * 64)
        assert len(d.delivery_method) == 64

    def test_delivery_method_over_64_chars_rejected(self):
        with pytest.raises(ValidationError):
            self._make(delivery_method="x" * 65)


# ---------------------------------------------------------------------------
# IngestPayload
# ---------------------------------------------------------------------------


class TestIngestPayload:
    """Tests for IngestPayload schema validation."""

    _BASE_DETECTION = {
        "confidence": 0.0,
        "signals": {},
        "classification": "human",
    }

    def _make(self, **overrides) -> IngestPayload:
        defaults = {
            "site_key": "ca_live_abc123",
            "visit_id": "visit-001",
            "timestamp": "2026-02-21T00:00:00Z",
            "page_url": "https://example.com/page",
            "detection": self._BASE_DETECTION,
        }
        defaults.update(overrides)
        return IngestPayload(**defaults)

    def test_valid_payload_accepted(self):
        p = self._make()
        assert p.visit_id == "visit-001"

    def test_visit_id_alphanumeric_accepted(self):
        p = self._make(visit_id="abc123")
        assert p.visit_id == "abc123"

    def test_visit_id_with_underscore_accepted(self):
        p = self._make(visit_id="visit_001")
        assert p.visit_id == "visit_001"

    def test_visit_id_with_hyphen_accepted(self):
        p = self._make(visit_id="visit-001")
        assert p.visit_id == "visit-001"

    def test_visit_id_with_space_rejected(self):
        with pytest.raises(ValidationError):
            self._make(visit_id="visit 001")

    def test_visit_id_with_special_chars_rejected(self):
        with pytest.raises(ValidationError):
            self._make(visit_id="visit@001!")

    def test_visit_id_empty_rejected(self):
        with pytest.raises(ValidationError):
            self._make(visit_id="")

    def test_visit_id_max_64_chars_accepted(self):
        p = self._make(visit_id="a" * 64)
        assert len(p.visit_id) == 64

    def test_visit_id_over_64_chars_rejected(self):
        with pytest.raises(ValidationError):
            self._make(visit_id="a" * 65)

    def test_test_results_max_50_accepted(self):
        results = [
            {
                "test_id": f"CAN-{i:04d}",
                "delivery_method": "html_comment",
                "outcome": "ignored",
            }
            for i in range(1, 51)
        ]
        p = self._make(test_results=results)
        assert len(p.test_results) == 50

    def test_test_results_51_rejected(self):
        results = [
            {
                "test_id": f"CAN-{(i % 9999) + 1:04d}",
                "delivery_method": "html_comment",
                "outcome": "ignored",
            }
            for i in range(51)
        ]
        with pytest.raises(ValidationError):
            self._make(test_results=results)

    def test_site_key_max_64_chars_accepted(self):
        p = self._make(site_key="a" * 64)
        assert len(p.site_key) == 64

    def test_site_key_over_64_chars_rejected(self):
        with pytest.raises(ValidationError):
            self._make(site_key="a" * 65)
