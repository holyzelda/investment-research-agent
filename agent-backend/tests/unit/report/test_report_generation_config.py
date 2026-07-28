import pytest
from pydantic import ValidationError

from app.core.config.settings import MiddlePlatformConfig


def test_report_model_concurrency_defaults_to_five():
    assert MiddlePlatformConfig().report_model_concurrency == 5


def test_report_model_concurrency_must_be_positive():
    with pytest.raises(ValidationError):
        MiddlePlatformConfig(report_model_concurrency=0)
