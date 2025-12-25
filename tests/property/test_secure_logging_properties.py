"""Property-based tests for secure logging."""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import HealthCheck
import re

from src.utils.secure_logger import (
    SensitiveDataFilter,
    sanitize_for_logging,
    SENSITIVE_PATTERNS,
    SENSITIVE_FIELDS
)


# Feature: aws-pricing-assistant, Property 37: Secure logging
# For any logged user interaction, sensitive customer information should not be included in the logs


@given(
    password=st.text(min_size=8, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',)))
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_password_redaction_in_text(password):
    """
    Property 37: Secure logging (password redaction)
    
    For any text containing a password, the password value should be redacted in logs.
    """
    filter = SensitiveDataFilter()
    
    # Test various password formats
    test_cases = [
        f"password: {password}",
        f"password={password}",
        f'"password": "{password}"',
        f"'password': '{password}'",
        f"Password: {password}",
        f"pwd={password}",
    ]
    
    for text in test_cases:
        sanitized = filter.sanitize_text(text)
        
        # Verify password is redacted
        assert password not in sanitized, f"Password should be redacted in: {text}"
        assert "[REDACTED]" in sanitized, f"Should contain redaction marker in: {text}"


@given(
    token=st.text(min_size=20, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N')))
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_token_redaction_in_text(token):
    """
    Property 37: Secure logging (token redaction)
    
    For any text containing an authentication token, the token should be redacted in logs.
    """
    filter = SensitiveDataFilter()
    
    # Test various token formats
    test_cases = [
        f"token: {token}",
        f"token={token}",
        f"bearer {token}",
        f"Bearer: {token}",
        f"jwt={token}",
    ]
    
    for text in test_cases:
        sanitized = filter.sanitize_text(text)
        
        # Verify token is redacted
        assert token not in sanitized, f"Token should be redacted in: {text}"
        assert "[REDACTED]" in sanitized, f"Should contain redaction marker in: {text}"


@given(
    api_key=st.text(min_size=20, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N')))
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_api_key_redaction_in_text(api_key):
    """
    Property 37: Secure logging (API key redaction)
    
    For any text containing an API key, the key should be redacted in logs.
    """
    filter = SensitiveDataFilter()
    
    # Test various API key formats
    test_cases = [
        f"api_key: {api_key}",
        f"api-key={api_key}",
        f"apikey: {api_key}",
        f'"api_key": "{api_key}"',
    ]
    
    for text in test_cases:
        sanitized = filter.sanitize_text(text)
        
        # Verify API key is redacted
        assert api_key not in sanitized, f"API key should be redacted in: {text}"
        assert "[REDACTED]" in sanitized, f"Should contain redaction marker in: {text}"


@given(
    data=st.dictionaries(
        keys=st.sampled_from(['username', 'email', 'password', 'token', 'api_key', 'config']),
        values=st.text(min_size=1, max_size=100),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_sensitive_fields_redaction_in_dict(data):
    """
    Property 37: Secure logging (dictionary field redaction)
    
    For any dictionary containing sensitive fields, those fields should be redacted in logs.
    """
    filter = SensitiveDataFilter()
    
    # Sanitize the dictionary
    sanitized = filter.sanitize_dict(data)
    
    # Verify sensitive fields are redacted
    for key, value in data.items():
        if key.lower() in SENSITIVE_FIELDS:
            assert sanitized[key] == "[REDACTED]", f"Sensitive field {key} should be redacted"
            assert sanitized[key] != value, f"Sensitive field {key} should not contain original value"
        else:
            # Non-sensitive fields should be unchanged
            assert sanitized[key] == value, f"Non-sensitive field {key} should be unchanged"


@given(
    email=st.emails()
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_email_redaction_in_text(email):
    """
    Property 37: Secure logging (email redaction)
    
    For any text containing an email address, the email should be redacted in logs.
    """
    filter = SensitiveDataFilter()
    
    text = f"User email is {email}"
    sanitized = filter.sanitize_text(text)
    
    # Verify email is redacted
    assert email not in sanitized, "Email should be redacted"
    assert "[REDACTED]" in sanitized, "Should contain redaction marker"


@given(
    nested_data=st.dictionaries(
        keys=st.sampled_from(['user', 'auth', 'config']),
        values=st.dictionaries(
            keys=st.sampled_from(['username', 'password', 'token', 'email']),
            values=st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=5
        ),
        min_size=1,
        max_size=3
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_nested_dict_redaction(nested_data):
    """
    Property 37: Secure logging (nested dictionary redaction)
    
    For any nested dictionary containing sensitive fields, those fields should be redacted
    at all levels of nesting.
    """
    filter = SensitiveDataFilter()
    
    # Sanitize the nested dictionary
    sanitized = filter.sanitize_dict(nested_data)
    
    # Verify sensitive fields are redacted at all levels
    for outer_key, inner_dict in nested_data.items():
        for inner_key, value in inner_dict.items():
            if inner_key.lower() in SENSITIVE_FIELDS:
                assert sanitized[outer_key][inner_key] == "[REDACTED]", \
                    f"Nested sensitive field {outer_key}.{inner_key} should be redacted"
            else:
                assert sanitized[outer_key][inner_key] == value, \
                    f"Nested non-sensitive field {outer_key}.{inner_key} should be unchanged"


@given(
    text=st.text(min_size=10, max_size=200)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_sanitize_for_logging_preserves_non_sensitive_data(text):
    """
    Property 37: Secure logging (non-sensitive data preservation)
    
    For any text that doesn't contain sensitive patterns, sanitization should preserve
    the original text.
    """
    # Only test text that doesn't match sensitive patterns
    has_sensitive = any(pattern.search(text) for pattern in SENSITIVE_PATTERNS.values())
    
    if not has_sensitive:
        sanitized = sanitize_for_logging(text)
        assert sanitized == text, "Non-sensitive text should be preserved"


@given(
    data=st.lists(
        st.dictionaries(
            keys=st.sampled_from(['id', 'name', 'password', 'value']),
            values=st.text(min_size=1, max_size=50),
            min_size=1,
            max_size=5
        ),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_list_of_dicts_redaction(data):
    """
    Property 37: Secure logging (list of dictionaries redaction)
    
    For any list of dictionaries containing sensitive fields, those fields should be
    redacted in all list items.
    """
    sanitized = sanitize_for_logging(data)
    
    # Verify it's still a list
    assert isinstance(sanitized, list), "Should return a list"
    assert len(sanitized) == len(data), "List length should be preserved"
    
    # Verify sensitive fields are redacted in all items
    for i, item in enumerate(data):
        for key, value in item.items():
            if key.lower() in SENSITIVE_FIELDS:
                assert sanitized[i][key] == "[REDACTED]", \
                    f"Sensitive field {key} in item {i} should be redacted"
            else:
                assert sanitized[i][key] == value, \
                    f"Non-sensitive field {key} in item {i} should be unchanged"


@given(
    aws_key=st.text(min_size=20, max_size=20, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.property_test
def test_aws_access_key_redaction(aws_key):
    """
    Property 37: Secure logging (AWS access key redaction)
    
    For any text containing an AWS access key pattern, the key should be redacted.
    """
    filter = SensitiveDataFilter()
    
    # AWS access keys start with AKIA
    aws_access_key = f"AKIA{aws_key}"
    text = f"AWS_ACCESS_KEY_ID={aws_access_key}"
    
    sanitized = filter.sanitize_text(text)
    
    # Verify AWS key is redacted
    assert aws_access_key not in sanitized, "AWS access key should be redacted"
    assert "[REDACTED]" in sanitized, "Should contain redaction marker"
