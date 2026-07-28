from config import settings


def test_oracle_mock_mode_is_enabled_in_test_environment():
    assert settings.is_testing is True
    assert settings.MOCK_ORACLE is True
