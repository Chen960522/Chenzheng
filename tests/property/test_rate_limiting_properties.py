"""Property-based tests for rate limiting."""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, MagicMock, patch
import time
from datetime import datetime

from src.api.middleware import RateLimitMiddleware
from src.models.user import User


# Strategies
@st.composite
def user_strategy(draw):
    """Generate a random user."""
    return User(
        user_id=draw(st.uuids()).hex,
        username=draw(st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        email=f"{draw(st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=('Ll',))))}@example.com",
        password_hash="hashed_password",
        role=draw(st.sampled_from(['admin', 'sales'])),
        full_name=draw(st.text(min_size=3, max_size=50)),
        created_at=datetime.now(),
        last_login=None,
        is_active=True
    )


@st.composite
def request_count_strategy(draw):
    """Generate a number of requests to make."""
    return draw(st.integers(min_value=1, max_value=150))


# Property 39: Rate limiting
# **Validates: Requirements 10.5**

@pytest.mark.property
@pytest.mark.asyncio
@given(
    user=user_strategy(),
    request_count=request_count_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_rate_limiting(user, request_count):
    """
    Property 39: Rate limiting
    
    For any user making N requests within a time window,
    if N > 100, then requests after the 100th should be rate limited (429 status).
    
    **Feature: aws-pricing-assistant, Property 39: Rate limiting**
    **Validates: Requirements 10.5**
    """
    # Create middleware instance
    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, max_requests=100, window_seconds=60)
    
    # Mock request and response
    async def mock_call_next(request):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        return response
    
    # Track results
    success_count = 0
    rate_limited_count = 0
    
    # Make requests
    for i in range(request_count):
        request = MagicMock()
        request.url.path = "/api/quotes/create"
        request.state.user = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role
        }
        
        response = await middleware.dispatch(request, mock_call_next)
        
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            rate_limited_count += 1
    
    # Property: If request_count > 100, some requests should be rate limited
    if request_count > 100:
        assert rate_limited_count > 0, \
            f"Expected rate limiting after 100 requests, but all {request_count} succeeded"
        assert success_count <= 100, \
            f"Expected at most 100 successful requests, but got {success_count}"
    else:
        # If request_count <= 100, all should succeed
        assert success_count == request_count, \
            f"Expected all {request_count} requests to succeed, but only {success_count} did"
        assert rate_limited_count == 0, \
            f"Expected no rate limiting for {request_count} requests, but {rate_limited_count} were limited"


@pytest.mark.property
@pytest.mark.asyncio
@given(
    user1=user_strategy(),
    user2=user_strategy(),
    requests_per_user=st.integers(min_value=50, max_value=120)
)
@settings(max_examples=100, deadline=None)
async def test_property_rate_limiting_per_user(user1, user2, requests_per_user):
    """
    Property: Rate limiting is enforced per user
    
    For any two different users, each making N requests,
    rate limiting should be applied independently to each user.
    
    **Feature: aws-pricing-assistant, Property 39: Rate limiting per user**
    **Validates: Requirements 10.5**
    """
    # Ensure users are different
    assume(user1.user_id != user2.user_id)
    
    # Create middleware instance
    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, max_requests=100, window_seconds=60)
    
    # Mock call_next
    async def mock_call_next(request):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        return response
    
    # Make requests for user1
    user1_success = 0
    user1_limited = 0
    
    for i in range(requests_per_user):
        request = MagicMock()
        request.url.path = "/api/quotes/create"
        request.state.user = {
            "user_id": user1.user_id,
            "username": user1.username,
            "role": user1.role
        }
        
        response = await middleware.dispatch(request, mock_call_next)
        
        if response.status_code == 200:
            user1_success += 1
        elif response.status_code == 429:
            user1_limited += 1
    
    # Make requests for user2
    user2_success = 0
    user2_limited = 0
    
    for i in range(requests_per_user):
        request = MagicMock()
        request.url.path = "/api/quotes/create"
        request.state.user = {
            "user_id": user2.user_id,
            "username": user2.username,
            "role": user2.role
        }
        
        response = await middleware.dispatch(request, mock_call_next)
        
        if response.status_code == 200:
            user2_success += 1
        elif response.status_code == 429:
            user2_limited += 1
    
    # Property: Each user should be rate limited independently
    if requests_per_user > 100:
        # Both users should hit rate limit
        assert user1_limited > 0, \
            f"User1 should be rate limited after {requests_per_user} requests"
        assert user2_limited > 0, \
            f"User2 should be rate limited after {requests_per_user} requests"
    else:
        # Neither user should hit rate limit
        assert user1_success == requests_per_user, \
            f"User1 should have all {requests_per_user} requests succeed"
        assert user2_success == requests_per_user, \
            f"User2 should have all {requests_per_user} requests succeed"


@pytest.mark.property
@pytest.mark.asyncio
@given(
    user=user_strategy()
)
@settings(max_examples=50, deadline=None)
async def test_property_rate_limit_headers(user):
    """
    Property: Rate limit headers are present
    
    For any authenticated request, the response should include
    rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset).
    
    **Feature: aws-pricing-assistant, Property 39: Rate limit headers**
    **Validates: Requirements 10.5**
    """
    # Create middleware instance
    app_mock = MagicMock()
    middleware = RateLimitMiddleware(app_mock, max_requests=100, window_seconds=60)
    
    # Mock call_next
    async def mock_call_next(request):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        return response
    
    # Make request
    request = MagicMock()
    request.url.path = "/api/quotes/create"
    request.state.user = {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role
    }
    
    response = await middleware.dispatch(request, mock_call_next)
    
    # Property: Rate limit headers should be present
    assert "X-RateLimit-Limit" in response.headers, \
        "Response should include X-RateLimit-Limit header"
    assert "X-RateLimit-Remaining" in response.headers, \
        "Response should include X-RateLimit-Remaining header"
    assert "X-RateLimit-Reset" in response.headers, \
        "Response should include X-RateLimit-Reset header"
    
    # Validate header values
    limit = int(response.headers["X-RateLimit-Limit"])
    remaining = int(response.headers["X-RateLimit-Remaining"])
    reset = int(response.headers["X-RateLimit-Reset"])
    
    assert limit == 100, \
        f"Rate limit should be 100, but got {limit}"
    assert 0 <= remaining <= limit, \
        f"Remaining requests should be between 0 and {limit}, but got {remaining}"
    assert reset > time.time(), \
        f"Reset timestamp should be in the future"
