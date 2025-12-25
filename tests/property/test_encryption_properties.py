"""Property-based tests for data encryption."""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import HealthCheck

from src.utils.encryption import DataEncryption, FieldEncryption


# Feature: aws-pricing-assistant, Property 35: Data encryption
# For any sensitive customer configuration data stored, it should be encrypted


@given(
    data=st.text(min_size=1, max_size=1000)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_encryption_round_trip(data):
    """
    Property 35: Data encryption
    
    For any sensitive data, encrypting then decrypting should return the original data.
    This validates that encryption is working correctly and data can be recovered.
    """
    # Generate a test encryption key
    encryption_key = DataEncryption.generate_key()
    encryption = DataEncryption(encryption_key)
    
    # Encrypt the data
    encrypted = encryption.encrypt(data)
    
    # Verify encrypted data is different from original
    assert encrypted != data, "Encrypted data should differ from original"
    
    # Decrypt the data
    decrypted = encryption.decrypt(encrypted)
    
    # Verify decrypted data matches original
    assert decrypted == data, "Decrypted data should match original"


@given(
    field_data=st.dictionaries(
        keys=st.sampled_from(['username', 'email', 'password', 'api_key', 'token', 'config']),
        values=st.text(min_size=1, max_size=100),
        min_size=1,
        max_size=10
    ),
    sensitive_fields=st.lists(
        st.sampled_from(['password', 'api_key', 'token']),
        min_size=1,
        max_size=3,
        unique=True
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_field_encryption_selective(field_data, sensitive_fields):
    """
    Property 35: Data encryption (selective field encryption)
    
    For any dictionary with sensitive fields, only the specified fields should be encrypted,
    and decryption should restore the original data.
    """
    # Generate a test encryption key
    encryption_key = DataEncryption.generate_key()
    encryption = DataEncryption(encryption_key)
    field_encryption = FieldEncryption(encryption)
    
    # Store original data
    original_data = field_data.copy()
    
    # Encrypt specified fields
    encrypted_data = field_encryption.encrypt_fields(field_data, sensitive_fields)
    
    # Verify sensitive fields are encrypted
    for field in sensitive_fields:
        if field in original_data:
            assert encrypted_data[field] != original_data[field], f"Field {field} should be encrypted"
            assert encrypted_data.get(f"__{field}_encrypted") == True, f"Field {field} should be marked as encrypted"
    
    # Verify non-sensitive fields are unchanged
    for field in field_data:
        if field not in sensitive_fields:
            assert encrypted_data[field] == original_data[field], f"Non-sensitive field {field} should be unchanged"
    
    # Decrypt fields
    decrypted_data = field_encryption.decrypt_fields(encrypted_data, sensitive_fields)
    
    # Verify all fields match original
    for field in original_data:
        assert decrypted_data[field] == original_data[field], f"Decrypted field {field} should match original"
    
    # Verify encryption markers are removed
    for field in sensitive_fields:
        if field in original_data:
            assert f"__{field}_encrypted" not in decrypted_data, f"Encryption marker for {field} should be removed"


@given(
    data=st.text(min_size=1, max_size=1000)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_encryption_different_keys_produce_different_ciphertext(data):
    """
    Property 35: Data encryption (key uniqueness)
    
    For any data, encrypting with different keys should produce different ciphertext.
    This ensures that encryption keys are properly used.
    """
    # Generate two different encryption keys
    key1 = DataEncryption.generate_key()
    key2 = DataEncryption.generate_key()
    
    encryption1 = DataEncryption(key1)
    encryption2 = DataEncryption(key2)
    
    # Encrypt with both keys
    encrypted1 = encryption1.encrypt(data)
    encrypted2 = encryption2.encrypt(data)
    
    # Verify ciphertexts are different
    assert encrypted1 != encrypted2, "Different keys should produce different ciphertext"
    
    # Verify each can decrypt its own ciphertext
    assert encryption1.decrypt(encrypted1) == data
    assert encryption2.decrypt(encrypted2) == data


@given(
    data=st.text(min_size=1, max_size=1000)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_encryption_same_data_different_ciphertext(data):
    """
    Property 35: Data encryption (non-deterministic)
    
    For any data, encrypting the same data multiple times should produce different ciphertext.
    This ensures that encryption includes randomness (IV/nonce) for security.
    """
    # Generate encryption key
    encryption_key = DataEncryption.generate_key()
    encryption = DataEncryption(encryption_key)
    
    # Encrypt the same data twice
    encrypted1 = encryption.encrypt(data)
    encrypted2 = encryption.encrypt(data)
    
    # Verify ciphertexts are different (due to random IV)
    assert encrypted1 != encrypted2, "Same data encrypted twice should produce different ciphertext"
    
    # Verify both decrypt to the same original data
    assert encryption.decrypt(encrypted1) == data
    assert encryption.decrypt(encrypted2) == data


@given(
    password=st.text(min_size=8, max_size=100)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_key_derivation_from_password(password):
    """
    Property 35: Data encryption (key derivation)
    
    For any password, deriving a key should be deterministic with the same salt,
    but different with different salts.
    """
    # Derive key with first salt
    key1, salt1 = DataEncryption.derive_key_from_password(password)
    
    # Derive key with same salt
    key2, salt2 = DataEncryption.derive_key_from_password(password, salt=None)
    
    # Keys should be different (different salts)
    assert key1 != key2, "Different salts should produce different keys"
    
    # Derive key with explicit salt
    import base64
    salt_bytes = base64.urlsafe_b64decode(salt1.encode())
    key3, salt3 = DataEncryption.derive_key_from_password(password, salt=salt_bytes)
    
    # Key should be the same with same salt
    assert key1 == key3, "Same password and salt should produce same key"
    assert salt1 == salt3, "Salt should be preserved"
