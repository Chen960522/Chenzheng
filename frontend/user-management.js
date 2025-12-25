// User Management Page Logic (Admin Only)

let allUsers = [];
let currentUserId = null;
let userToDelete = null;
let userToReset = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Check if user is admin
    if (!isAdmin()) {
        window.location.href = 'dashboard.html';
        return;
    }

    await loadUsers();
    setupEventHandlers();
});

async function loadUsers() {
    const listEl = document.getElementById('usersList');

    try {
        allUsers = await api.getUsers();
        displayUsers(allUsers);
    } catch (error) {
        console.error('Failed to load users:', error);
        listEl.innerHTML = `
            <div class="error-message">Failed to load users: ${error.message}</div>
        `;
    }
}

function displayUsers(users) {
    const listEl = document.getElementById('usersList');

    if (users.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <p data-i18n="users.noUsers">No users found</p>
            </div>
        `;
        updateTranslations();
        return;
    }

    const tableHTML = `
        <table class="users-table">
            <thead>
                <tr>
                    <th data-i18n="users.username">Username</th>
                    <th data-i18n="users.email">Email</th>
                    <th data-i18n="users.fullName">Full Name</th>
                    <th data-i18n="users.role">Role</th>
                    <th data-i18n="users.status">Status</th>
                    <th data-i18n="users.actions">Actions</th>
                </tr>
            </thead>
            <tbody>
                ${users.map(user => createUserRow(user)).join('')}
            </tbody>
        </table>
    `;

    listEl.innerHTML = tableHTML;
    updateTranslations();

    // Add event listeners
    document.querySelectorAll('.edit-user-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const userId = e.target.dataset.userId;
            showEditUserModal(userId);
        });
    });

    document.querySelectorAll('.reset-password-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const userId = e.target.dataset.userId;
            showResetPasswordModal(userId);
        });
    });

    document.querySelectorAll('.delete-user-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const userId = e.target.dataset.userId;
            showDeleteUserModal(userId);
        });
    });
}

function createUserRow(user) {
    const statusBadge = user.is_active 
        ? '<span class="status-badge status-finalized" data-i18n="users.active">Active</span>'
        : '<span class="status-badge status-draft" data-i18n="users.inactive">Inactive</span>';

    return `
        <tr>
            <td>${user.username}</td>
            <td>${user.email}</td>
            <td>${user.full_name}</td>
            <td>${user.role}</td>
            <td>${statusBadge}</td>
            <td>
                <div class="user-actions">
                    <button class="btn btn-secondary edit-user-btn" data-user-id="${user.user_id}" data-i18n="common.edit">Edit</button>
                    <button class="btn btn-secondary reset-password-btn" data-user-id="${user.user_id}" data-i18n="users.resetPassword">Reset Password</button>
                    <button class="btn btn-danger delete-user-btn" data-user-id="${user.user_id}" data-i18n="common.delete">Delete</button>
                </div>
            </td>
        </tr>
    `;
}

function setupEventHandlers() {
    // Create user button
    document.getElementById('createUserBtn').addEventListener('click', showCreateUserModal);

    // User form
    document.getElementById('userForm').addEventListener('submit', handleUserFormSubmit);
    document.getElementById('cancelUserBtn').addEventListener('click', hideUserModal);

    // Reset password modal
    document.getElementById('cancelResetBtn').addEventListener('click', hideResetPasswordModal);
    document.getElementById('confirmResetBtn').addEventListener('click', handleResetPassword);
    document.getElementById('copyPasswordBtn')?.addEventListener('click', copyTempPassword);

    // Delete user modal
    document.getElementById('cancelDeleteUserBtn').addEventListener('click', hideDeleteUserModal);
    document.getElementById('confirmDeleteUserBtn').addEventListener('click', handleDeleteUser);
}

function showCreateUserModal() {
    currentUserId = null;
    document.getElementById('modalTitle').textContent = 'Create User';
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
    document.getElementById('passwordGroup').style.display = 'block';
    document.getElementById('userPassword').required = true;
    document.getElementById('userFormError').style.display = 'none';
    document.getElementById('userModal').style.display = 'flex';
    updateTranslations();
}

function showEditUserModal(userId) {
    const user = allUsers.find(u => u.user_id === userId);
    if (!user) return;

    currentUserId = userId;
    document.getElementById('modalTitle').textContent = 'Edit User';
    document.getElementById('userId').value = user.user_id;
    document.getElementById('userUsername').value = user.username;
    document.getElementById('userEmail').value = user.email;
    document.getElementById('userFullName').value = user.full_name;
    document.getElementById('userRole').value = user.role;
    document.getElementById('userActive').checked = user.is_active;
    document.getElementById('passwordGroup').style.display = 'none';
    document.getElementById('userPassword').required = false;
    document.getElementById('userFormError').style.display = 'none';
    document.getElementById('userModal').style.display = 'flex';
    updateTranslations();
}

function hideUserModal() {
    document.getElementById('userModal').style.display = 'none';
    currentUserId = null;
}

async function handleUserFormSubmit(e) {
    e.preventDefault();

    const errorDiv = document.getElementById('userFormError');
    errorDiv.style.display = 'none';

    const userData = {
        username: document.getElementById('userUsername').value,
        email: document.getElementById('userEmail').value,
        full_name: document.getElementById('userFullName').value,
        role: document.getElementById('userRole').value,
        is_active: document.getElementById('userActive').checked
    };

    // Add password for new users
    if (!currentUserId) {
        userData.password = document.getElementById('userPassword').value;
    }

    try {
        if (currentUserId) {
            await api.updateUser(currentUserId, userData);
        } else {
            await api.createUser(userData);
        }

        hideUserModal();
        await loadUsers();
    } catch (error) {
        console.error('Failed to save user:', error);
        errorDiv.textContent = error.message || 'Failed to save user';
        errorDiv.style.display = 'block';
    }
}

function showResetPasswordModal(userId) {
    userToReset = userId;
    document.getElementById('tempPassword').style.display = 'none';
    document.getElementById('confirmResetBtn').style.display = 'inline-block';
    document.getElementById('resetPasswordModal').style.display = 'flex';
}

function hideResetPasswordModal() {
    userToReset = null;
    document.getElementById('resetPasswordModal').style.display = 'none';
}

async function handleResetPassword() {
    if (!userToReset) return;

    try {
        const response = await api.resetPassword(userToReset);
        
        // Show temporary password
        document.getElementById('tempPasswordValue').textContent = response.temporary_password;
        document.getElementById('tempPassword').style.display = 'block';
        document.getElementById('confirmResetBtn').style.display = 'none';
    } catch (error) {
        console.error('Failed to reset password:', error);
        alert('Failed to reset password: ' + error.message);
        hideResetPasswordModal();
    }
}

function copyTempPassword() {
    const password = document.getElementById('tempPasswordValue').textContent;
    navigator.clipboard.writeText(password).then(() => {
        alert('Password copied to clipboard');
    });
}

function showDeleteUserModal(userId) {
    userToDelete = userId;
    document.getElementById('deleteUserModal').style.display = 'flex';
}

function hideDeleteUserModal() {
    userToDelete = null;
    document.getElementById('deleteUserModal').style.display = 'none';
}

async function handleDeleteUser() {
    if (!userToDelete) return;

    try {
        await api.deleteUser(userToDelete);
        
        // Remove from local array
        allUsers = allUsers.filter(u => u.user_id !== userToDelete);
        
        // Refresh display
        displayUsers(allUsers);
        
        hideDeleteUserModal();
    } catch (error) {
        console.error('Failed to delete user:', error);
        alert('Failed to delete user: ' + error.message);
    }
}
