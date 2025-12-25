// Authentication Module

// Check if user is authenticated
function isAuthenticated() {
    return localStorage.getItem('token') !== null;
}

// Get current user
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

// Check if user is admin
function isAdmin() {
    const user = getCurrentUser();
    return user && user.role === 'admin';
}

// Protect page (redirect to login if not authenticated)
function protectPage() {
    if (!isAuthenticated()) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

// Initialize auth state on page load
function initAuth() {
    // If on login page and already authenticated, redirect to dashboard
    if (window.location.pathname.includes('login.html') && isAuthenticated()) {
        window.location.href = 'dashboard.html';
        return;
    }

    // Protect all pages except login
    if (!window.location.pathname.includes('login.html')) {
        if (!protectPage()) {
            return;
        }

        // Load user info
        loadUserInfo();

        // Show/hide admin elements
        if (isAdmin()) {
            document.body.classList.add('admin');
        }

        // Setup logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogout);
        }
    }
}

// Load and display user info
async function loadUserInfo() {
    try {
        const user = await api.getCurrentUser();
        localStorage.setItem('user', JSON.stringify(user));

        const userNameEl = document.getElementById('userName');
        if (userNameEl) {
            userNameEl.textContent = user.full_name || user.username;
        }

        // Update admin state
        if (user.role === 'admin') {
            document.body.classList.add('admin');
        }
    } catch (error) {
        console.error('Failed to load user info:', error);
    }
}

// Handle logout
async function handleLogout() {
    try {
        await api.logout();
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    }
}

// Login form handler
if (window.location.pathname.includes('login.html')) {
    document.addEventListener('DOMContentLoaded', () => {
        const loginForm = document.getElementById('loginForm');
        const errorDiv = document.getElementById('loginError');

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            errorDiv.style.display = 'none';

            try {
                const response = await api.login(username, password);
                
                // Store token and user info
                localStorage.setItem('token', response.access_token);
                localStorage.setItem('user', JSON.stringify(response.user));

                // Redirect to dashboard
                window.location.href = 'dashboard.html';
            } catch (error) {
                errorDiv.textContent = error.message || 'Login failed. Please check your credentials.';
                errorDiv.style.display = 'block';
            }
        });
    });
} else {
    // Initialize auth for protected pages
    document.addEventListener('DOMContentLoaded', initAuth);
}
