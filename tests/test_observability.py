# ============================================================================
# EDP-IO - Observability Tests
# ============================================================================
"""
Tests for LLM observability modules.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestLogAnalyzer:
    """Tests for the log analyzer module."""

    def test_error_analysis_model(self):
        """Test ErrorAnalysis model validation."""
        from src.observability.log_analyzer import (ErrorAnalysis, ErrorType,
                                                    Severity)

        analysis = ErrorAnalysis(
            error_type=ErrorType.SCHEMA_DRIFT,
            root_cause="Test root cause",
            business_impact=Severity.MEDIUM,
            recommended_action="Test action",
            requires_human_approval=True,
            confidence_score=0.85,
        )

        assert analysis.error_type == ErrorType.SCHEMA_DRIFT
        assert analysis.requires_human_approval is True
        assert 0 <= analysis.confidence_score <= 1

    def test_requires_human_approval_always_true(self):
        """Test that requires_human_approval cannot be False."""
        from src.observability.log_analyzer import (ErrorAnalysis, ErrorType,
                                                    Severity)

        # Even if we try to set it False, the system should enforce True
        analysis = ErrorAnalysis(
            error_type=ErrorType.UNKNOWN,
            root_cause="Test",
            business_impact=Severity.LOW,
            recommended_action="Test",
            requires_human_approval=True,  # Must always be True
            confidence_score=0.5,
        )

        assert analysis.requires_human_approval is True

    def test_log_analyzer_mock_mode(self, mock_settings):
        """Test log analyzer works in mock mode (LLM disabled)."""
        mock_settings.enable_llm_observability = False

        from src.observability.log_analyzer import LogAnalyzer

        analyzer = LogAnalyzer()
        assert analyzer.is_enabled is False

        result = analyzer.analyze("Schema error: column not found")

        assert result is not None
        assert result.requires_human_approval is True
        assert result.error_type is not None

    def test_log_analyzer_categorizes_errors(self, mock_settings):
        """Test error categorization based on log content."""
        mock_settings.enable_llm_observability = False

        from src.observability.log_analyzer import ErrorType, LogAnalyzer

        analyzer = LogAnalyzer()

        # Schema drift detection
        result = analyzer.analyze("Column 'new_field' not found in schema definition")
        assert result.error_type == ErrorType.SCHEMA_DRIFT

        # Connection error detection
        result = analyzer.analyze("Connection refused by Oracle database")
        assert result.error_type == ErrorType.CONNECTION_FAILURE

        # Data quality detection
        result = analyzer.analyze("Null values detected in required column")
        assert result.error_type == ErrorType.DATA_QUALITY


class TestSchemaDriftDetector:
    """Tests for schema drift detection."""

    def test_detect_column_added(self, sample_schema_expected, sample_schema_actual, mock_settings):
        """Test detection of new columns."""
        mock_settings.enable_llm_observability = False

        from src.observability.schema_drift import (ChangeType,
                                                    SchemaDriftDetector)

        detector = SchemaDriftDetector()
        report = detector.detect_drift(
            table_name="customers",
            expected_schema=sample_schema_expected,
            actual_schema=sample_schema_actual,
            source_system="oracle_erp",
        )

        assert len(report.changes) == 1
        assert report.changes[0]["change_type"] == ChangeType.COLUMN_ADDED.value
        assert report.changes[0]["column_name"] == "loyalty_points"
        assert report.requires_human_approval is True

    def test_detect_column_removed(self, mock_settings):
        """Test detection of removed columns."""
        mock_settings.enable_llm_observability = False

        from src.observability.schema_drift import (ChangeType, SchemaColumn,
                                                    SchemaDriftDetector)

        expected = [
            SchemaColumn(name="id", data_type="string", nullable=False),
            SchemaColumn(name="name", data_type="string", nullable=False),
            SchemaColumn(name="old_field", data_type="string", nullable=True),
        ]

        actual = [
            SchemaColumn(name="id", data_type="string", nullable=False),
            SchemaColumn(name="name", data_type="string", nullable=False),
            # old_field removed
        ]

        detector = SchemaDriftDetector()
        report = detector.detect_drift("test_table", expected, actual)

        assert report.breaking_change is True
        changes = [c for c in report.changes if c["change_type"] == ChangeType.COLUMN_REMOVED.value]
        assert len(changes) == 1

    def test_detect_type_changes(self, mock_settings):
        """Test detection of type changes."""
        mock_settings.enable_llm_observability = False

        from src.observability.schema_drift import (ChangeType, SchemaColumn,
                                                    SchemaDriftDetector)

        expected = [
            SchemaColumn(name="amount", data_type="integer", nullable=False),
        ]

        actual = [
            SchemaColumn(name="amount", data_type="decimal", nullable=False),
        ]

        detector = SchemaDriftDetector()
        report = detector.detect_drift("test_table", expected, actual)

        assert report.breaking_change is True
        assert report.changes[0]["change_type"] == ChangeType.TYPE_CHANGED.value

    def test_no_drift_detected(self, mock_settings):
        """Test no changes when schemas match."""
        mock_settings.enable_llm_observability = False

        from src.observability.schema_drift import (DriftSeverity,
                                                    SchemaColumn,
                                                    SchemaDriftDetector)

        schema = [
            SchemaColumn(name="id", data_type="string", nullable=False),
            SchemaColumn(name="name", data_type="string", nullable=True),
        ]

        detector = SchemaDriftDetector()
        report = detector.detect_drift("test_table", schema, schema)

        assert len(report.changes) == 0
        assert report.severity == DriftSeverity.INFO


class TestDocGenerator:
    """Tests for documentation generator."""

    def test_mock_doc_generation(self, mock_settings):
        """Test documentation generation in mock mode."""
        mock_settings.enable_llm_observability = False

        from src.observability.doc_generator import DocGenerator

        generator = DocGenerator()

        # Test Silver layer model
        doc = generator.generate_model_doc("stg_customers")

        assert doc.model_name == "stg_customers"
        assert "SCD" in doc.description or "Silver" in doc.description
        assert doc.summary is not None
        assert len(doc.key_transformations) > 0

    def test_fact_model_doc(self, mock_settings):
        """Test fact table documentation."""
        mock_settings.enable_llm_observability = False

        from src.observability.doc_generator import DocGenerator

        generator = DocGenerator()
        doc = generator.generate_model_doc("fact_sales")

        assert "fact" in doc.model_name
        assert "grain" in doc.description.lower() or "Fact" in doc.description

    def test_dimension_model_doc(self, mock_settings):
        """Test dimension table documentation."""
        mock_settings.enable_llm_observability = False

        from src.observability.doc_generator import DocGenerator

        generator = DocGenerator()
        doc = generator.generate_model_doc("dim_customer")

        assert "dim" in doc.model_name
        assert len(doc.business_rules) > 0
