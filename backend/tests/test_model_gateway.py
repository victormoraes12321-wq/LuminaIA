from services.ai_service import AUTHORIZED_OPENAI_MODEL, validate_authorized_model


def test_model_gateway_redirects_to_authorized_model():
    assert validate_authorized_model("gpt-4o") == AUTHORIZED_OPENAI_MODEL
    assert validate_authorized_model("gpt-4") == AUTHORIZED_OPENAI_MODEL
    assert validate_authorized_model(AUTHORIZED_OPENAI_MODEL) == AUTHORIZED_OPENAI_MODEL
    assert validate_authorized_model(None) == AUTHORIZED_OPENAI_MODEL
