import json

from app.env_validator import validate_environment


def test_redacted_validation_does_not_return_environment_values():
    secrets = {
        "PORT": "70000",
        "API_TOKEN": "live-production-secret-value",
        "PUBLIC_LABEL": "customer-private-label",
    }

    result = validate_environment(secrets, redact_values=True)
    serialized = json.dumps(result)

    assert result["sanitized_variables"] == {
        "PORT": "********",
        "API_TOKEN": "********",
        "PUBLIC_LABEL": "********",
    }
    for value in secrets.values():
        assert value not in serialized
