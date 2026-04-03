const API_BASE = 'http://localhost:5000';

//   Toggle between login and register forms  
function toggleForm(mode) {
    document.getElementById('login-section').style.display    = mode === 'login'    ? 'block' : 'none';
    document.getElementById('register-section').style.display = mode === 'register' ? 'block' : 'none';
    hideError();
}

//   Show / hide error message  
function showError(msg) {
    const el = document.getElementById('error-msg');
    if (!el) return;
    el.textContent = msg;
    el.style.display = 'block';
}

function hideError() {
    const el = document.getElementById('error-msg');
    if (el) el.style.display = 'none';
}

//   Login  
async function handleLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!username || !password) {
        showError('Please enter username and password.');
        return;
    }

    const btn = document.getElementById('btn-login');
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    hideError();

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok && data.token) {
            // Save token 
            localStorage.setItem('wf_token', data.token);
            localStorage.setItem('wf_user', username);
            // Redirect to main dashboard
            window.location.href = 'index.htm';
        } else {
            showError(data.message || 'Invalid username or password.');
        }

    } catch (err) {
        showError('Cannot connect to server. Is Flask running?');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

//   Register  
async function handleRegister() {
    const username = document.getElementById('reg-username').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm  = document.getElementById('reg-confirm').value;

    if (!username || !password) {
        showError('Please fill in all fields.');
        return;
    }

    if (password !== confirm) {
        showError('Passwords do not match.');
        return;
    }

    const btn = document.getElementById('btn-register');
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    hideError();

    try {
        const response = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            // Auto switch to login after successful register
            toggleForm('login');
            showError(''); 
            document.getElementById('login-username').value = username;
            alert('Account created! Please sign in.');
        } else {
            showError(data.message || 'Registration failed.');
        }

    } catch (err) {
        showError('Cannot connect to server. Is Flask running?');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Account';
    }
}

//   Get token for API calls 
function getToken() {
    return localStorage.getItem('wf_token');
}

//   Attach auth header to any fetch 
function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + getToken()
    };
}

//   Logout 
function logout() {
    localStorage.removeItem('wf_token');
    localStorage.removeItem('wf_user');
    window.location.href = 'login.htm';
}

//   redirect to login if no token  
function requireAuth() {
    if (!getToken()) {
        window.location.href = 'login.htm';
    }
}