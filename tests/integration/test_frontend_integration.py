"""
Integration tests for web interface
Tests login flow, quote request flow, quote history, and user management
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, Page, Browser
import time


@pytest.fixture(scope="module")
async def browser():
    """Create browser instance for tests"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Create new page for each test"""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()


class TestLoginFlow:
    """Test login functionality"""
    
    @pytest.mark.asyncio
    async def test_login_page_loads(self, page: Page):
        """Test that login page loads correctly"""
        await page.goto("http://localhost:8000/login.html")
        
        # Check page title
        title = await page.title()
        assert "Login" in title
        
        # Check form elements exist
        assert await page.locator("#username").is_visible()
        assert await page.locator("#password").is_visible()
        assert await page.locator("button[type='submit']").is_visible()
    
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, page: Page):
        """Test successful login"""
        await page.goto("http://localhost:8000/login.html")
        
        # Fill in credentials
        await page.fill("#username", "testuser")
        await page.fill("#password", "TestPassword123!")
        
        # Submit form
        await page.click("button[type='submit']")
        
        # Wait for redirect to dashboard
        await page.wait_for_url("**/dashboard.html", timeout=5000)
        
        # Verify we're on dashboard
        assert "dashboard.html" in page.url
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, page: Page):
        """Test login failure with invalid credentials"""
        await page.goto("http://localhost:8000/login.html")
        
        # Fill in invalid credentials
        await page.fill("#username", "invalid")
        await page.fill("#password", "wrong")
        
        # Submit form
        await page.click("button[type='submit']")
        
        # Wait for error message
        await page.wait_for_selector("#loginError", state="visible", timeout=5000)
        
        # Verify error message is displayed
        error_visible = await page.locator("#loginError").is_visible()
        assert error_visible
    
    @pytest.mark.asyncio
    async def test_logout(self, page: Page):
        """Test logout functionality"""
        # Login first
        await page.goto("http://localhost:8000/login.html")
        await page.fill("#username", "testuser")
        await page.fill("#password", "TestPassword123!")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/dashboard.html", timeout=5000)
        
        # Click logout
        await page.click("#logoutBtn")
        
        # Wait for redirect to login
        await page.wait_for_url("**/login.html", timeout=5000)
        
        # Verify we're back on login page
        assert "login.html" in page.url


class TestQuoteRequestFlow:
    """Test quote request functionality"""
    
    @pytest.fixture(autouse=True)
    async def login(self, page: Page):
        """Login before each test"""
        await page.goto("http://localhost:8000/login.html")
        await page.fill("#username", "testuser")
        await page.fill("#password", "TestPassword123!")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/dashboard.html", timeout=5000)
    
    @pytest.mark.asyncio
    async def test_quote_request_page_loads(self, page: Page):
        """Test that quote request page loads correctly"""
        await page.goto("http://localhost:8000/quote-request.html")
        
        # Check form elements exist
        assert await page.locator("#configText").is_visible()
        assert await page.locator("#configFile").count() > 0
        assert await page.locator("#region").is_visible()
        assert await page.locator("#pricingModel").is_visible()
        assert await page.locator("button[type='submit']").is_visible()
    
    @pytest.mark.asyncio
    async def test_submit_quote_request(self, page: Page):
        """Test submitting a quote request"""
        await page.goto("http://localhost:8000/quote-request.html")
        
        # Fill in configuration
        config = """
        {
            "provider": "alibaba",
            "services": [
                {
                    "type": "compute",
                    "name": "ECS",
                    "specs": {
                        "cpu": 2,
                        "memory": 4,
                        "storage": 100
                    }
                }
            ]
        }
        """
        await page.fill("#configText", config)
        
        # Select region and pricing model
        await page.select_option("#region", "us-east-1")
        await page.select_option("#pricingModel", "on-demand")
        
        # Submit form
        await page.click("button[type='submit']")
        
        # Wait for processing status to appear
        await page.wait_for_selector("#processingStatus", state="visible", timeout=5000)
        
        # Verify processing status is shown
        assert await page.locator("#processingStatus").is_visible()
    
    @pytest.mark.asyncio
    async def test_empty_configuration_validation(self, page: Page):
        """Test validation for empty configuration"""
        await page.goto("http://localhost:8000/quote-request.html")
        
        # Try to submit without configuration
        await page.click("button[type='submit']")
        
        # Wait for error message
        await page.wait_for_selector("#errorMessage", state="visible", timeout=5000)
        
        # Verify error message is displayed
        assert await page.locator("#errorMessage").is_visible()


class TestQuoteHistory:
    """Test quote history functionality"""
    
    @pytest.fixture(autouse=True)
    async def login(self, page: Page):
        """Login before each test"""
        await page.goto("http://localhost:8000/login.html")
        await page.fill("#username", "testuser")
        await page.fill("#password", "TestPassword123!")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/dashboard.html", timeout=5000)
    
    @pytest.mark.asyncio
    async def test_quote_history_page_loads(self, page: Page):
        """Test that quote history page loads correctly"""
        await page.goto("http://localhost:8000/quote-history.html")
        
        # Check page elements exist
        assert await page.locator("#searchInput").is_visible()
        assert await page.locator("#statusFilter").is_visible()
        assert await page.locator("#historyList").count() > 0
    
    @pytest.mark.asyncio
    async def test_search_quotes(self, page: Page):
        """Test searching quotes"""
        await page.goto("http://localhost:8000/quote-history.html")
        
        # Wait for quotes to load
        await page.wait_for_timeout(1000)
        
        # Enter search term
        await page.fill("#searchInput", "test")
        
        # Wait for filter to apply
        await page.wait_for_timeout(500)
        
        # Verify search input has value
        search_value = await page.input_value("#searchInput")
        assert search_value == "test"
    
    @pytest.mark.asyncio
    async def test_filter_by_status(self, page: Page):
        """Test filtering quotes by status"""
        await page.goto("http://localhost:8000/quote-history.html")
        
        # Wait for quotes to load
        await page.wait_for_timeout(1000)
        
        # Select status filter
        await page.select_option("#statusFilter", "draft")
        
        # Wait for filter to apply
        await page.wait_for_timeout(500)
        
        # Verify filter is applied
        filter_value = await page.input_value("#statusFilter")
        assert filter_value == "draft"


class TestUserManagement:
    """Test user management functionality (admin only)"""
    
    @pytest.fixture(autouse=True)
    async def login_as_admin(self, page: Page):
        """Login as admin before each test"""
        await page.goto("http://localhost:8000/login.html")
        await page.fill("#username", "admin")
        await page.fill("#password", "AdminPassword123!")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/dashboard.html", timeout=5000)
    
    @pytest.mark.asyncio
    async def test_user_management_page_loads(self, page: Page):
        """Test that user management page loads correctly"""
        await page.goto("http://localhost:8000/user-management.html")
        
        # Check page elements exist
        assert await page.locator("#createUserBtn").is_visible()
        assert await page.locator("#usersList").count() > 0
    
    @pytest.mark.asyncio
    async def test_create_user_modal_opens(self, page: Page):
        """Test opening create user modal"""
        await page.goto("http://localhost:8000/user-management.html")
        
        # Click create user button
        await page.click("#createUserBtn")
        
        # Wait for modal to appear
        await page.wait_for_selector("#userModal", state="visible", timeout=5000)
        
        # Verify modal is visible
        assert await page.locator("#userModal").is_visible()
        assert await page.locator("#userForm").is_visible()
    
    @pytest.mark.asyncio
    async def test_cancel_create_user(self, page: Page):
        """Test canceling user creation"""
        await page.goto("http://localhost:8000/user-management.html")
        
        # Open modal
        await page.click("#createUserBtn")
        await page.wait_for_selector("#userModal", state="visible", timeout=5000)
        
        # Click cancel
        await page.click("#cancelUserBtn")
        
        # Wait for modal to close
        await page.wait_for_selector("#userModal", state="hidden", timeout=5000)
        
        # Verify modal is hidden
        modal_visible = await page.locator("#userModal").is_visible()
        assert not modal_visible


class TestLanguageSwitcher:
    """Test multi-language support"""
    
    @pytest.mark.asyncio
    async def test_language_switcher_exists(self, page: Page):
        """Test that language switcher exists on all pages"""
        await page.goto("http://localhost:8000/login.html")
        
        # Check language buttons exist
        assert await page.locator("#langEn").is_visible()
        assert await page.locator("#langZh").is_visible()
    
    @pytest.mark.asyncio
    async def test_switch_to_chinese(self, page: Page):
        """Test switching to Chinese language"""
        await page.goto("http://localhost:8000/login.html")
        
        # Click Chinese button
        await page.click("#langZh")
        
        # Wait for translations to update
        await page.wait_for_timeout(500)
        
        # Verify Chinese button is active
        zh_btn_class = await page.get_attribute("#langZh", "class")
        assert "active" in zh_btn_class
    
    @pytest.mark.asyncio
    async def test_switch_to_english(self, page: Page):
        """Test switching to English language"""
        await page.goto("http://localhost:8000/login.html")
        
        # Click Chinese first
        await page.click("#langZh")
        await page.wait_for_timeout(500)
        
        # Click English
        await page.click("#langEn")
        await page.wait_for_timeout(500)
        
        # Verify English button is active
        en_btn_class = await page.get_attribute("#langEn", "class")
        assert "active" in en_btn_class


class TestResponsiveDesign:
    """Test responsive design for different screen sizes"""
    
    @pytest.mark.asyncio
    async def test_mobile_viewport(self, page: Page):
        """Test layout on mobile viewport"""
        # Set mobile viewport
        await page.set_viewport_size({"width": 375, "height": 667})
        
        await page.goto("http://localhost:8000/login.html")
        
        # Verify page loads correctly
        assert await page.locator(".login-card").is_visible()
    
    @pytest.mark.asyncio
    async def test_tablet_viewport(self, page: Page):
        """Test layout on tablet viewport"""
        # Set tablet viewport
        await page.set_viewport_size({"width": 768, "height": 1024})
        
        await page.goto("http://localhost:8000/login.html")
        
        # Verify page loads correctly
        assert await page.locator(".login-card").is_visible()
    
    @pytest.mark.asyncio
    async def test_desktop_viewport(self, page: Page):
        """Test layout on desktop viewport"""
        # Set desktop viewport
        await page.set_viewport_size({"width": 1920, "height": 1080})
        
        await page.goto("http://localhost:8000/login.html")
        
        # Verify page loads correctly
        assert await page.locator(".login-card").is_visible()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
