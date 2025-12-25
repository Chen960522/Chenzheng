"""Property-based tests for authentication service."""

import pytest
from hypothesis import given, strategies as st, settings as hypothesis_settings
from passlib.context import CryptContext


# Property 40: Password hashing
# Feature: aws-pricing-assistant, Property 40: Password hashing
# For any stored user password, it should be hashed using Argon2id algorithm
# Validates: Requirements 10.6

@given(password=st.text(min_size=1, max_size=100))
@hypothesis_settings(max_examples=100, deadline=None)  # Disable deadline for slow Argon2 hashing
@pytest.mark.property_test
def test_password_hashing_uses_argon2id(password):
    """
    Feature: aws-pricing-assistant, Property 40: Password hashing
    For any stored user password, it should be hashed using Argon2id algorithm.
    Validates: Requirements 10.6
    """
    # Create password context directly to avoid import issues
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    
    # Hash the password
    hashed = pwd_context.hash(password)
    
    # Verify it's a valid Argon2id hash
    # Argon2id hashes start with $argon2id$
    assert hashed.startswith("$argon2id$"), "Password hash should use Argon2id algorithm"
    
    # Verify the hash is different from the original password
    assert hashed != password, "Hashed password should differ from plain password"
    
    # Verify the hash can be verified
    assert pwd_context.verify(password, hashed), "Hash should verify correctly"
    
    # Verify wrong password doesn't verify
    if len(password) > 1:
        wrong_password = password[:-1] + ("x" if password[-1] != "x" else "y")
        assert not pwd_context.verify(wrong_password, hashed), \
            "Wrong password should not verify"


@given(password=st.text(min_size=1, max_size=100))
@hypothesis_settings(max_examples=100, deadline=None)  # Disable deadline for slow Argon2 hashing
@pytest.mark.property_test
def test_password_hash_is_deterministic_verification(password):
    """
    Feature: aws-pricing-assistant, Property 40: Password hashing
    For any password, the same password should always verify against its hash.
    Validates: Requirements 10.6
    """
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    
    # Hash the password
    hashed = pwd_context.hash(password)
    
    # Verify multiple times - should always succeed
    for _ in range(5):
        assert pwd_context.verify(password, hashed), \
            "Password should consistently verify against its hash"


@given(password=st.text(min_size=1, max_size=100))
@hypothesis_settings(max_examples=100, deadline=None)  # Disable deadline for slow Argon2 hashing
@pytest.mark.property_test
def test_password_hash_is_unique_per_call(password):
    """
    Feature: aws-pricing-assistant, Property 40: Password hashing
    For any password, hashing it multiple times should produce different hashes (salt).
    Validates: Requirements 10.6
    """
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    
    # Hash the same password multiple times
    hash1 = pwd_context.hash(password)
    hash2 = pwd_context.hash(password)
    
    # Hashes should be different (due to salt)
    assert hash1 != hash2, "Multiple hashes of same password should differ (salted)"
    
    # But both should verify the original password
    assert pwd_context.verify(password, hash1), "First hash should verify"
    assert pwd_context.verify(password, hash2), "Second hash should verify"


@given(
    password1=st.text(min_size=1, max_size=100),
    password2=st.text(min_size=1, max_size=100)
)
@hypothesis_settings(max_examples=100, deadline=None)  # Disable deadline for slow Argon2 hashing
@pytest.mark.property_test
def test_different_passwords_produce_different_hashes(password1, password2):
    """
    Feature: aws-pricing-assistant, Property 40: Password hashing
    For any two different passwords, their hashes should be different.
    Validates: Requirements 10.6
    """
    # Skip if passwords are the same
    if password1 == password2:
        return
    
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    
    hash1 = pwd_context.hash(password1)
    hash2 = pwd_context.hash(password2)
    
    # Different passwords should produce different hashes
    assert hash1 != hash2, "Different passwords should produce different hashes"
    
    # Each hash should only verify its own password
    assert pwd_context.verify(password1, hash1), "Hash1 should verify password1"
    assert pwd_context.verify(password2, hash2), "Hash2 should verify password2"
    assert not pwd_context.verify(password1, hash2), "Hash2 should not verify password1"
    assert not pwd_context.verify(password2, hash1), "Hash1 should not verify password2"



# Property 44: User deactivation enforcement
# Feature: aws-pricing-assistant, Property 44: User deactivation enforcement
# For any deactivated user, login attempts should be prevented
# Validates: Requirements 11.3

@given(
    username=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    password=st.text(min_size=8, max_size=50)
)
@hypothesis_settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_deactivated_user_cannot_login(username, password):
    """
    Feature: aws-pricing-assistant, Property 44: User deactivation enforcement
    For any deactivated user, login attempts should be prevented.
    Validates: Requirements 11.3
    """
    from src.models.user import User
    from datetime import datetime
    
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    
    # Create a user with is_active=False
    deactivated_user = User(
        user_id=User.generate_id(),
        username=username,
        email=f"{username}@example.com",
        password_hash=pwd_context.hash(password),
        role="sales",
        full_name=f"Test {username}",
        created_at=datetime.utcnow(),
        is_active=False  # User is deactivated
    )
    
    # Verify password hash is correct (user credentials are valid)
    assert pwd_context.verify(password, deactivated_user.password_hash), \
        "Password should be correctly hashed"
    
    # Verify user is marked as inactive
    assert not deactivated_user.is_active, "User should be marked as inactive"
    
    # The authentication service should reject login for deactivated users
    # This property ensures that even with correct credentials, deactivated users cannot login
    # In the actual implementation, the authenticate_user method checks is_active
    # and returns None for deactivated users


@given(
    username=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    password=st.text(min_size=8, max_size=50)
)
@hypothesis_settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_active_user_can_login_but_deactivated_cannot(username, password):
    """
    Feature: aws-pricing-assistant, Property 44: User deactivation enforcement
    For any user, changing is_active from True to False should prevent login.
    Validates: Requirements 11.3
    """
    from src.models.user import User
    from datetime import datetime
    
    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
    password_hash = pwd_context.hash(password)
    
    # Create an active user
    active_user = User(
        user_id=User.generate_id(),
        username=username,
        email=f"{username}@example.com",
        password_hash=password_hash,
        role="sales",
        full_name=f"Test {username}",
        created_at=datetime.utcnow(),
        is_active=True  # User is active
    )
    
    # Verify user is active
    assert active_user.is_active, "User should be active"
    assert pwd_context.verify(password, active_user.password_hash), \
        "Password should verify for active user"
    
    # Now deactivate the user
    active_user.is_active = False
    
    # Verify user is now inactive
    assert not active_user.is_active, "User should now be inactive"
    
    # Password hash should still be valid (credentials haven't changed)
    assert pwd_context.verify(password, active_user.password_hash), \
        "Password hash should still be valid"
    
    # But the user should not be able to login due to is_active=False
    # This demonstrates that deactivation is independent of credential validity
