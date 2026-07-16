from config import settings


def test_oracle_mock_mode_is_disabled_by_default():
    assert settings.MOCK_ORACLE is False
