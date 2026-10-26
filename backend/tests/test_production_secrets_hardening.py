import pytest
from pydantic import ValidationError
from app.core.config import Settings
from app.services.encryption_service import TokenEncryptionService


def test_development_mode_permits_default_secrets():
    """In development mode, default development secrets must be allowed for zero-config onboarding."""
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET="outreachiq_dev_secret_key_change_in_production_2026_xyz",
        GMAIL_TOKEN_ENCRYPTION_KEY="outreachiq_default_dev_encryption_key_2026_xyz"
    )
    assert settings.ENVIRONMENT == "development"
    assert settings.JWT_SECRET == "outreachiq_dev_secret_key_change_in_production_2026_xyz"
    assert settings.GMAIL_TOKEN_ENCRYPTION_KEY == "outreachiq_default_dev_encryption_key_2026_xyz"


def test_production_mode_rejects_default_jwt_secret():
    """Production mode must immediately fail fast if the default development JWT secret is used."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="outreachiq_dev_secret_key_change_in_production_2026_xyz",
            GMAIL_TOKEN_ENCRYPTION_KEY="a_strong_production_encryption_key_32_characters_long_12345"
        )
    err = str(exc_info.value)
    assert "Production security failure" in err
    assert "JWT_SECRET is set to an insecure development placeholder" in err


def test_production_mode_rejects_empty_or_short_jwt_secret():
    """Production mode must reject blank or short (<32 chars) JWT secrets."""
    # Blank
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="",
            GMAIL_TOKEN_ENCRYPTION_KEY="a_strong_production_encryption_key_32_characters_long_12345"
        )
    assert "JWT_SECRET must be configured and non-empty" in str(exc_info.value)

    # Too short (< 32 chars)
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="short_jwt_secret_12345",
            GMAIL_TOKEN_ENCRYPTION_KEY="a_strong_production_encryption_key_32_characters_long_12345"
        )
    assert "JWT_SECRET must be at least 32 characters long" in str(exc_info.value)


def test_production_mode_rejects_default_gmail_encryption_key():
    """Production mode must reject default dev Gmail token encryption keys."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="a_strong_production_jwt_signing_secret_32_characters_long_12345",
            GMAIL_TOKEN_ENCRYPTION_KEY="outreachiq_default_dev_encryption_key_2026_xyz"
        )
    err = str(exc_info.value)
    assert "Production security failure" in err
    assert "GMAIL_TOKEN_ENCRYPTION_KEY is set to an insecure development placeholder" in err


def test_production_mode_rejects_empty_or_short_encryption_key():
    """Production mode must reject blank or short (<32 chars) Gmail encryption keys."""
    # Blank
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="a_strong_production_jwt_signing_secret_32_characters_long_12345",
            GMAIL_TOKEN_ENCRYPTION_KEY=""
        )
    assert "GMAIL_TOKEN_ENCRYPTION_KEY must be configured and non-empty" in str(exc_info.value)

    # Too short
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="a_strong_production_jwt_signing_secret_32_characters_long_12345",
            GMAIL_TOKEN_ENCRYPTION_KEY="short_key_12345"
        )
    assert "GMAIL_TOKEN_ENCRYPTION_KEY must be at least 32 characters long" in str(exc_info.value)


def test_production_mode_accepts_strong_secrets():
    """Production mode must cleanly initialize when provided with strong, dedicated secrets."""
    valid_jwt = "prod_jwt_signing_secret_abcdef1234567890_secure_key_2026"
    valid_enc = "prod_gmail_encryption_key_fedcba0987654321_secure_key_2026"
    settings = Settings(
        ENVIRONMENT="production",
        JWT_SECRET=valid_jwt,
        GMAIL_TOKEN_ENCRYPTION_KEY=valid_enc
    )
    assert settings.ENVIRONMENT == "production"
    assert settings.JWT_SECRET == valid_jwt
    assert settings.GMAIL_TOKEN_ENCRYPTION_KEY == valid_enc


def test_encryption_roundtrip_with_production_key(monkeypatch):
    """Verifies Fernet token encryption and decryption succeed seamlessly with a production key."""
    test_prod_key = "prod_dedicated_encryption_key_32_chars_long_xyz_98765"
    monkeypatch.setattr("app.services.encryption_service.settings.GMAIL_TOKEN_ENCRYPTION_KEY", test_prod_key)

    raw_token = "ya29.a0AfH6SMB_sample_google_oauth_refresh_token_string"
    encrypted = TokenEncryptionService.encrypt(raw_token)
    assert encrypted != raw_token
    assert len(encrypted) > 30

    decrypted = TokenEncryptionService.decrypt(encrypted)
    assert decrypted == raw_token
