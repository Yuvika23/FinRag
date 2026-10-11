"""
FinRAG — Tests for the financial analysis service.
Tests SQL calculations without requiring a live database (using mocks where practical).
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.financial_analysis.analysis_service import (
    FinancialAnalysisService,
    SUPPORTED_METRICS,
)
from app.services.generation.rag_orchestrator import classify_query, _detect_metric


class TestMetricNormalization:
    def test_revenue_aliases(self):
        svc = FinancialAnalysisService()
        assert svc._normalize_metric_name("total_revenue") == "revenue"
        assert svc._normalize_metric_name("net_revenue") == "revenue"
        assert svc._normalize_metric_name("revenue") == "revenue"

    def test_net_income_aliases(self):
        svc = FinancialAnalysisService()
        assert svc._normalize_metric_name("net_earnings") == "net_income"

    def test_cogs_aliases(self):
        svc = FinancialAnalysisService()
        assert svc._normalize_metric_name("cogs") == "cost_of_revenue"
        assert svc._normalize_metric_name("cost_of_goods_sold") == "cost_of_revenue"

    def test_case_insensitive(self):
        svc = FinancialAnalysisService()
        assert svc._normalize_metric_name("Revenue") == "revenue"
        assert svc._normalize_metric_name("NET INCOME") == "net_income"


class TestMarginCalculation:
    def test_gross_margin(self):
        assert FinancialAnalysisService._safe_pct(720.0, 1000.0) == 72.0

    def test_net_margin(self):
        assert FinancialAnalysisService._safe_pct(150.0, 1000.0) == 15.0

    def test_zero_denominator_returns_none(self):
        assert FinancialAnalysisService._safe_pct(100.0, 0.0) is None

    def test_none_numerator_returns_none(self):
        assert FinancialAnalysisService._safe_pct(None, 1000.0) is None

    def test_none_denominator_returns_none(self):
        assert FinancialAnalysisService._safe_pct(100.0, None) is None


class TestYoYCalculation:
    def test_positive_growth(self):
        """Test calculation of positive YoY growth."""
        svc = FinancialAnalysisService()
        # Mock the get_metric_values call
        from app.services.financial_analysis.analysis_service import MetricValue
        mock_db = MagicMock()
        
        mock_values = [
            MetricValue("revenue", "FY2023", 3750.0, "USD", "millions", False, None, None),
            MetricValue("revenue", "FY2024", 4250.0, "USD", "millions", False, None, None),
        ]

        with patch.object(svc, "get_metric_values", return_value=mock_values):
            with patch.object(svc, "_find_company", return_value=MagicMock(name="Test Corp")):
                yoy = svc.calculate_yoy_change(mock_db, "Test Corp", "revenue", "FY2023", "FY2024")

        assert yoy.absolute_change == pytest.approx(500.0, rel=1e-3)
        assert yoy.percentage_change == pytest.approx(13.333, rel=1e-2)
        assert yoy.warning is None

    def test_missing_data_generates_warning(self):
        svc = FinancialAnalysisService()
        mock_db = MagicMock()

        with patch.object(svc, "get_metric_values", return_value=[]):
            with patch.object(svc, "_find_company", return_value=MagicMock(name="Test Corp")):
                yoy = svc.calculate_yoy_change(mock_db, "Test Corp", "revenue", "FY2023", "FY2024")

        assert yoy.absolute_change is None
        assert yoy.percentage_change is None
        assert yoy.warning is not None

    def test_zero_base_year(self):
        """Test that zero base year is handled gracefully."""
        svc = FinancialAnalysisService()
        from app.services.financial_analysis.analysis_service import MetricValue
        mock_db = MagicMock()

        mock_values = [
            MetricValue("revenue", "FY2023", 0.0, "USD", "millions", False, None, None),
            MetricValue("revenue", "FY2024", 100.0, "USD", "millions", False, None, None),
        ]

        with patch.object(svc, "get_metric_values", return_value=mock_values):
            with patch.object(svc, "_find_company", return_value=MagicMock(name="Test Corp")):
                yoy = svc.calculate_yoy_change(mock_db, "Test Corp", "revenue", "FY2023", "FY2024")

        # Should not crash; percentage_change should be None or have warning
        assert yoy.warning is not None or yoy.percentage_change is None


class TestQueryClassification:
    def test_numerical_query(self):
        assert classify_query("What was the revenue in FY2024?") == "numerical"

    def test_qualitative_query(self):
        assert classify_query("What are the main risk factors and strategies disclosed?") == "qualitative"

    def test_combined_query(self):
        q = "Compare revenue growth FY2023 to FY2024 and explain the factors behind it"
        result = classify_query(q)
        assert result in ("combined", "numerical")  # Both keywords present

    def test_generic_query(self):
        # Generic question with no financial keywords
        result = classify_query("Tell me about the company.")
        assert result in ("qualitative", "numerical", "combined")  # Should not crash


class TestMetricDetection:
    def test_detects_revenue(self):
        assert _detect_metric("What was the revenue?") == "revenue"

    def test_detects_net_income(self):
        assert _detect_metric("Show me net income for FY2024") == "net_income"

    def test_detects_gross_profit(self):
        assert _detect_metric("What was the gross profit?") == "gross_profit"

    def test_returns_none_for_unknown(self):
        assert _detect_metric("Tell me about management strategy") is None
