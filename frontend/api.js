// API Client for AWS Pricing Assistant

const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : window.location.origin;

class APIClient {
    constructor() {
        this.baseURL = API_BASE_URL;
    }

    async request(endpoint, options = {}) {
        const token = localStorage.getItem('token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, config);
            
            if (response.status === 401) {
                // Token expired or invalid
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                window.location.href = 'login.html';
                return;
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Authentication
    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${this.baseURL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        return data;
    }

    async logout() {
        return this.request('/api/auth/logout', { method: 'POST' });
    }

    async getCurrentUser() {
        return this.request('/api/auth/me');
    }

    // Quotes
    async createQuote(quoteData) {
        return this.request('/api/quotes/create', {
            method: 'POST',
            body: JSON.stringify(quoteData)
        });
    }

    async getQuote(quoteId) {
        return this.request(`/api/quotes/${quoteId}`);
    }

    async getQuoteHistory(limit = 50, offset = 0) {
        return this.request(`/api/quotes/history?limit=${limit}&offset=${offset}`);
    }

    async updateQuote(quoteId, updates) {
        return this.request(`/api/quotes/${quoteId}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
    }

    async deleteQuote(quoteId) {
        return this.request(`/api/quotes/${quoteId}`, {
            method: 'DELETE'
        });
    }

    async downloadQuote(quoteId, format) {
        const token = localStorage.getItem('token');
        const url = `${this.baseURL}/api/quotes/${quoteId}/download?format=${format}`;
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Download failed');
        }

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `quote-${quoteId}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(downloadUrl);
        document.body.removeChild(a);
    }

    // Users (Admin only)
    async getUsers() {
        return this.request('/api/users/list');
    }

    async createUser(userData) {
        return this.request('/api/users/create', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    async updateUser(userId, updates) {
        return this.request(`/api/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
    }

    async deleteUser(userId) {
        return this.request(`/api/users/${userId}`, {
            method: 'DELETE'
        });
    }

    async resetPassword(userId) {
        return this.request(`/api/users/${userId}/reset-password`, {
            method: 'POST'
        });
    }
}

const api = new APIClient();
