"""Tests for report validator."""
import pytest

from app.ai.validator import ReportValidator, generate_with_retry


class MockProvider:
    """Fake LLM provider returning predefined reports."""

    def __init__(self, reports: list[str]):
        self.reports = reports
        self.call_count = 0

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        report = self.reports[self.call_count]
        self.call_count += 1
        return report


class TestReportValidator:
    """Unit tests for ReportValidator."""

    def test_valid_report_passes(self):
        report = "总交易次数50次，胜率45%，SCALP总盈亏-5000"
        data = {
            "total_trades": 50,
            "win_rate": 45.0,
            "patterns": [
                {"pattern_name": "SCALP", "total_pnl": -5000.0}
            ],
        }
        result = ReportValidator.validate(report, data)
        assert result.is_valid
        assert result.errors == []

    def test_valid_report_no_patterns(self):
        report = "总交易次数10次，胜率60%"
        data = {
            "total_trades": 10,
            "win_rate": 60.0,
            "patterns": [],
        }
        result = ReportValidator.validate(report, data)
        assert result.is_valid

    def test_invalid_trades_count(self):
        report = "总交易次数30次"
        data = {"total_trades": 50}
        result = ReportValidator.validate(report, data)
        assert not result.is_valid
        assert any("交易次数" in err for err in result.errors)

    def test_invalid_win_rate(self):
        report = "胜率30%"
        data = {"win_rate": 45.0}
        result = ReportValidator.validate(report, data)
        assert not result.is_valid
        assert any("胜率" in err for err in result.errors)

    def test_win_rate_within_tolerance_passes(self):
        """Allow 1% tolerance for win rate rounding."""
        report = "胜率44%"
        data = {"win_rate": 44.5}
        result = ReportValidator.validate(report, data)
        assert result.is_valid

    def test_empty_report_does_not_crash(self):
        """Empty report: no numbers found -> checks skipped -> is_valid."""
        data = {"total_trades": 50}
        result = ReportValidator.validate("", data)
        assert result.is_valid

    def test_validate_missing_total_trades_data_is_valid(self):
        """If input_data has no total_trades, skip that check."""
        report = "胜率45%"
        data = {"win_rate": 45.0}
        result = ReportValidator.validate(report, data)
        assert result.is_valid

    def test_missing_pattern_in_report_still_passes(self):
        """If a pattern's PnL can't be found in report, skip that check."""
        report = "总交易次数10次，胜率50%"
        data = {
            "total_trades": 10,
            "win_rate": 50.0,
            "patterns": [
                {"pattern_name": "UNKNOWN_PATTERN", "total_pnl": 999.0}
            ],
        }
        result = ReportValidator.validate(report, data)
        assert result.is_valid  # pattern PnL not found -> skip


@pytest.mark.asyncio
class TestGenerateWithRetry:
    """generate_with_retry should retry on invalid output."""

    async def test_valid_first_attempt_returns_immediately(self):
        provider = MockProvider(["总交易次数50次，胜率45%"])
        report = await generate_with_retry(
            provider, "system", "user", {"total_trades": 50, "win_rate": 45.0}
        )
        assert report == "总交易次数50次，胜率45%"
        assert provider.call_count == 1

    async def test_retries_on_invalid_output(self):
        """Provider returns wrong data first, then correct."""
        provider = MockProvider([
            "总交易次数99次",  # invalid - says 99 but data says 50
            "总交易次数50次，胜率45%",  # valid
        ])
        report = await generate_with_retry(
            provider, "system", "user", {"total_trades": 50, "win_rate": 45.0}
        )
        assert report == "总交易次数50次，胜率45%"
        assert provider.call_count == 2

    async def test_returns_last_attempt_even_if_invalid(self):
        """After max_retries, return the last report even if invalid."""
        provider = MockProvider([
            "总交易次数99次",
            "总交易次数88次",
            "总交易次数77次",
        ])
        report = await generate_with_retry(
            provider,
            "system",
            "user",
            {"total_trades": 50},
            max_retries=3,
        )
        assert report == "总交易次数77次"
        assert provider.call_count == 3
