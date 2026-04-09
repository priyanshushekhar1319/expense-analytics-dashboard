const API_BASE_URL = window.location.protocol.startsWith('http') ? window.location.origin + '/api' : 'http://localhost:8000/api';

let categoryChartInstance = null;
let trendChartInstance = null;
let healthChartInstance = null;

// Currency & Number Formatting
const formatCurrency = (amt) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amt);
const formatNumber = (num) => new Intl.NumberFormat('en-IN').format(num);

// Global Filter States
let g_startDate = '';
let g_endDate = '';
let g_catFilter = '';
let g_trendGroup = 'month';

// -----------------------------------------
// AUTHENTICATION ENGINE
// -----------------------------------------
let authToken = localStorage.getItem('token');
let userRole = localStorage.getItem('role');

async function apiFetch(endpoint, options = {}) {
    if (!options.headers) options.headers = {};
    if (authToken) {
        options.headers['Authorization'] = `Bearer ${authToken}`;
    }
    const res = await fetch(`${API_BASE_URL}${endpoint}`, options);
    // If token expired or invalid, auto logout
    if (res.status === 401 && endpoint !== '/login') {
        processLogout();
    }
    return res;
}

function processLogout() {
    authToken = null;
    userRole = null;
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('dashboard-container').style.display = 'none';
}

function processLoginSuccess(token, role) {
    authToken = token;
    userRole = role;
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('dashboard-container').style.display = 'flex';
    
    if (role === 'admin') {
        document.getElementById('nav-admin').style.display = 'block';
        loadAdminStats();
    } else {
        document.getElementById('nav-admin').style.display = 'none';
    }
    
    refreshAllData();
}

function setupAuth() {
    const authForm = document.getElementById('auth-form');
    let isLoginMode = true;
    
    document.getElementById('auth-toggle-link').addEventListener('click', (e) => {
        e.preventDefault();
        isLoginMode = !isLoginMode;
        document.getElementById('auth-action-btn').textContent = isLoginMode ? 'Login' : 'Sign Up';
        document.getElementById('auth-toggle-text').textContent = isLoginMode ? "Don't have an account?" : "Already have an account?";
        document.getElementById('auth-toggle-link').textContent = isLoginMode ? "Register" : "Login";
        
        // Show/Hide Full Name
        const nameInput = document.getElementById('auth-fullname');
        if (isLoginMode) {
            nameInput.style.display = 'none';
            nameInput.removeAttribute('required');
        } else {
            nameInput.style.display = 'block';
            nameInput.setAttribute('required', 'true');
        }
    });
    
    document.getElementById('nav-logout').addEventListener('click', (e) => {
        e.preventDefault();
        processLogout();
    });
    
    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const u = document.getElementById('auth-username').value;
        const p = document.getElementById('auth-password').value;
        const msg = document.getElementById('auth-message');
        msg.textContent = "Processing...";
        
        try {
            if (isLoginMode) {
                const res = await fetch(`${API_BASE_URL}/login`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p})
                });
                const data = await res.json();
                if (res.ok) {
                    msg.textContent = "";
                    processLoginSuccess(data.access_token, data.role);
                } else {
                    msg.textContent = data.detail || "Login failed.";
                }
            } else {
                const fn = document.getElementById('auth-fullname').value;
                const res = await fetch(`${API_BASE_URL}/register`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p, full_name: fn})
                });
                const data = await res.json();
                if (res.ok) {
                    msg.style.color = "var(--primary)";
                    msg.textContent = "Registration successful! You can now log in.";
                    isLoginMode = true;
                    document.getElementById('auth-action-btn').textContent = 'Login';
                    document.getElementById('auth-fullname').style.display = 'none';
                } else {
                    msg.style.color = "var(--danger)";
                    msg.textContent = data.detail || "Registration failed.";
                }
            }
        } catch(err) {
            msg.textContent = "Network error connecting to API.";
        }
    });
}

// -----------------------------------------
// Theme Toggle
// -----------------------------------------
function setupTheme() {
    const btn = document.getElementById('theme-btn');
    btn.addEventListener('click', () => {
        const body = document.body;
        if(body.getAttribute('data-theme') === 'light') {
            body.removeAttribute('data-theme');
            btn.textContent = '🌓 Toggle Light Mode';
        } else {
            body.setAttribute('data-theme', 'light');
            btn.textContent = '🌓 Toggle Dark Mode';
        }
        if(categoryChartInstance) categoryChartInstance.update();
        if(trendChartInstance) trendChartInstance.update();
    });
}

// -----------------------------------------
// Global Fetch Wrappers handling date params
// -----------------------------------------
function objToQueryStr(obj) {
    const str = [];
    for (var p in obj)
        if (obj.hasOwnProperty(p) && obj[p]) {
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(obj[p]));
        }
    return str.join("&");
}

async function loadSummary() {
    try {
        const query = objToQueryStr({ start_date: g_startDate, end_date: g_endDate });
        const res = await apiFetch(`/summary?${query}`);
        const data = await res.json();
        document.getElementById('total-expenses').textContent = formatCurrency(data.total_expenses);
    } catch (e) { console.error('Error fetching summary:', e); }
}

async function loadPrediction() {
    try {
        const res = await apiFetch(`/prediction`);
        const data = await res.json();
        const el = document.getElementById('prediction-val');
        const msg = document.getElementById('prediction-msg');
        if(data.status === 'success') {
            el.textContent = formatCurrency(data.predicted_next_month);
            msg.textContent = data.trend_slope > 0 ? 'Trending Up 📈' : 'Trending Down 📉';
            msg.className = data.trend_slope > 0 ? 'trend danger' : 'trend positive';
        } else {
            el.textContent = 'N/A';
        }
    } catch(e) { console.error('Error fetching prediction', e); }
}

async function loadHealth() {
    try {
        const res = await apiFetch(`/health`);
        const data = await res.json();
        renderSpeedometer(data.score, data.message);
    } catch(e) { console.error('Error fetching health', e); }
}

async function loadBudgets() {
    try {
        const query = objToQueryStr({ start_date: g_startDate, end_date: g_endDate });
        const res = await apiFetch(`/budgets?${query}`);
        const data = await res.json();
        
        const container = document.getElementById('budgets-container');
        container.innerHTML = '';
        
        data.forEach(item => {
            let colorCls = 'bg-safe';
            let colorText = 'var(--accent)';
            if(item.status === 'warning') { colorCls = 'bg-warning'; colorText = 'var(--warning)'; }
            if(item.status === 'danger') { colorCls = 'bg-danger'; colorText = 'var(--danger)'; }
            
            const div = document.createElement('div');
            div.className = 'budget-item';
            div.innerHTML = `
                <div class="budget-header">
                    <strong>${item.category}</strong>
                    <span style="color: ${colorText}">${formatCurrency(item.spent)} / ${formatCurrency(item.limit)}</span>
                </div>
                <div class="budget-bar-bg">
                    <div class="budget-bar-fill ${colorCls}" style="width: ${item.percent}%"></div>
                </div>
            `;
            container.appendChild(div);
        });
    } catch(e) { console.error('Error fetching budgets', e); }
}

async function loadCategoryData() {
    try {
        const query = objToQueryStr({ start_date: g_startDate, end_date: g_endDate });
        const res = await apiFetch(`/expenses/category?${query}`);
        const data = await res.json();
        
        const labels = data.map(item => item.category);
        const values = data.map(item => item.total);

        const ctx = document.getElementById('categoryChart').getContext('2d');
        if (categoryChartInstance) categoryChartInstance.destroy();

        categoryChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: [
                        '#6366f1', '#10b981', '#f59e0b', '#ef4444', 
                        '#8b5cf6', '#3b82f6', '#ec4899', '#14b8a6', '#f97316'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: {color: '#94a3b8'} } },
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const clickedIndex = elements[0].index;
                        const cat = categoryChartInstance.data.labels[clickedIndex];
                        g_catFilter = cat;
                        document.getElementById('txn-cat-filter').textContent = `(Filtered: ${cat})`;
                        document.getElementById('txn-cat-filter').style.color = '#f59e0b';
                        loadTransactions();
                    } else {
                        g_catFilter = '';
                        document.getElementById('txn-cat-filter').textContent = '';
                        loadTransactions();
                    }
                }
            }
        });
    } catch (e) { console.error('Error fetching categories:', e); }
}

async function loadTrendData() {
    try {
        const query = objToQueryStr({ group_by: g_trendGroup });
        const res = await apiFetch(`/expenses/trend?${query}`);
        const data = await res.json();

        const labels = data.map(item => item.time);
        const values = data.map(item => item.total);

        const ctx = document.getElementById('trendChart').getContext('2d');
        if (trendChartInstance) trendChartInstance.destroy();
        
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.5)');
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Spending', data: values,
                    borderColor: '#6366f1', backgroundColor: gradient,
                    borderWidth: 2, tension: 0.4, fill: true,
                    pointBackgroundColor: '#10b981', pointBorderColor: '#fff'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(150, 150, 150, 0.1)' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    } catch (e) { console.error('Error fetching trend:', e); }
}

const createRowHtml = (txn) => {
    const statusClass = `status-${txn.status.toLowerCase()}`;
    return `
        <td style="font-family: monospace; color: var(--primary);">${txn.transaction_id}</td>
        <td>${txn.date}</td>
        <td><strong>${txn.merchant}</strong></td>
        <td>${txn.category}</td>
        <td>${formatCurrency(txn.amount)}</td>
        <td><span class="status-badge ${statusClass}">${txn.status}</span></td>
        <td>
            <button class="delete-btn" data-id="${txn.transaction_id}" style="background:none; border:none; color:#ef4444; cursor:pointer;" title="Delete Record">
                <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
        </td>
    `;
};

async function loadTransactions() {
    try {
        const query15 = objToQueryStr({ start_date: g_startDate, end_date: g_endDate, category: g_catFilter, limit: 15 });
        const query100 = objToQueryStr({ start_date: g_startDate, end_date: g_endDate, category: '', limit: 100 });
        
        const res15 = await apiFetch(`/transactions?${query15}`);
        const data15 = await res15.json();
        
        const res100 = await apiFetch(`/transactions?${query100}`);
        const data100 = await res100.json();
        
        const recentTbody = document.getElementById('recent-transactions-body');
        const allTbody = document.getElementById('all-transactions-body');
        
        recentTbody.innerHTML = '';
        allTbody.innerHTML = '';
        
        data15.forEach(txn => {
            const tr = document.createElement('tr'); tr.innerHTML = createRowHtml(txn); recentTbody.appendChild(tr);
        });
        data100.forEach(txn => {
            const tr = document.createElement('tr'); tr.innerHTML = createRowHtml(txn); allTbody.appendChild(tr);
        });
        
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if(confirm('Delete transaction permanently?')) {
                    const delRes = await apiFetch(`/transactions/${id}`, { method: 'DELETE' });
                    if(delRes.ok) refreshAllData();
                }
            });
        });
    } catch (e) { console.error('Error fetching txns:', e); }
}

async function loadAdminStats() {
    try {
        const res = await apiFetch(`/admin/stats`);
        if(!res.ok) return;
        const data = await res.json();
        
        document.getElementById('admin-total-users').textContent = data.aggregate.total_users;
        document.getElementById('admin-total-txns').textContent = data.aggregate.total_transactions;
        
        const tbody = document.getElementById('admin-users-body');
        tbody.innerHTML = '';
        
        data.users.forEach(u => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="color:var(--accent); font-family:monospace;">USR-${u.id}</td>
                <td><strong>${u.username}</strong></td>
                <td>${u.role}</td>
                <td>${u.created_at}</td>
                <td>${formatNumber(u.txn_count || 0)}</td>
                <td style="color:var(--primary); font-weight:bold;">${formatCurrency(u.total_spend || 0)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) { console.error('Error fetching admin data', e); }
}

// -----------------------------------------
// Special Charts (Speedometer)
// -----------------------------------------
function renderSpeedometer(score, message) {
    const ctx = document.getElementById('healthChart').getContext('2d');
    if (healthChartInstance) healthChartInstance.destroy();
    
    let color = '#ef4444';
    if(score > 50) color = '#f59e0b';
    if(score > 80) color = '#10b981';
    
    document.getElementById('health-msg').textContent = message;
    document.getElementById('health-msg').style.color = color;

    healthChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [score, 100 - score],
                backgroundColor: [color, 'rgba(150,150,150,0.2)'],
                borderWidth: 0,
                circumference: 180,
                rotation: 270
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            cutout: '75%',
            plugins: { legend: { display: false }, tooltip: { enabled: false } }
        },
        plugins: [{
            id: 'textInside',
            beforeDraw: function(chart) {
                var width = chart.width, height = chart.height, ctx = chart.ctx;
                ctx.restore();
                ctx.font = "bold 1.5em Inter";
                ctx.fillStyle = '#94a3b8';
                ctx.textBaseline = "middle";
                var text = score.toString(),
                    textX = Math.round((width - ctx.measureText(text).width) / 2),
                    textY = height / 1.5;
                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });
}

// -----------------------------------------
// Setup Logic (Chat, Uploads, Navigation, Form)
// -----------------------------------------
function setupChat() {
    const btn = document.getElementById('ai-chat-btn');
    const input = document.getElementById('ai-chat-input');
    const box = document.getElementById('ai-response');
    
    btn.addEventListener('click', async () => {
        const text = input.value.trim();
        if(!text) return;
        
        box.textContent = "AI is thinking...";
        box.style.opacity = 0.5;
        try {
            const res = await apiFetch(`/chat`, {
                method: 'POST', headers: { 'Content-Type':'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            box.textContent = data.reply;
        } catch(e) {
            box.textContent = "Error communicating with optimization engine.";
        }
        box.style.opacity = 1;
        input.value = "";
    });
}

function setupBulkUpload() {
    const form = document.getElementById('upload-csv-form');
    if(!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = document.getElementById('csv-file').files[0];
        const msg = document.getElementById('upload-msg');
        
        msg.textContent = "Processing ETL pipeline...";
        const formData = new FormData();
        formData.append("file", file);
        
        try {
            // Note: Don't set Content-Type header manually when sending FormData, 
            // browser boundary will be missing if forced.
            let h = {};
            if(authToken) h['Authorization'] = `Bearer ${authToken}`;
            
            const res = await fetch(`${API_BASE_URL}/upload`, { 
                method: 'POST', body: formData, headers: h
            });
            const data = await res.json();
            if(res.ok) {
                msg.textContent = `Success! Parsed and inserted ${data.rows_inserted} rows safely.`;
                setTimeout(() => { msg.textContent=''; form.reset(); }, 4000);
                refreshAllData();
            } else {
                msg.textContent = `Upload failed. File format unrecognised.`;
            }
        } catch(e) { msg.textContent = "Fatal CSV Error."; }
    });
    
    // Auth wrap Export Button
    const expObj = document.getElementById('export-btn-ui');
    if(expObj) {
        expObj.addEventListener('click', async(e) => {
            e.preventDefault();
            const res = await apiFetch('/export');
            if(res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'cleaned_expenses.csv';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            }
        });
    }
}

function setupDateFilter() {
    const btn = document.getElementById('apply-dates');
    const clr = document.getElementById('clear-dates');
    if(!btn) return;
    
    btn.addEventListener('click', () => {
        g_startDate = document.getElementById('start-date').value;
        g_endDate = document.getElementById('end-date').value;
        refreshAllData();
    });
    
    clr.addEventListener('click', () => {
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        g_startDate = ''; g_endDate = '';
        refreshAllData();
    });
    
    document.getElementById('trend-time-toggle').addEventListener('change', (e) => {
        g_trendGroup = e.target.value;
        loadTrendData();
    });
}

function refreshAllData() {
    if(!authToken) return; // Do not fetch if not logged in
    loadSummary();
    loadCategoryData();
    loadTrendData();
    loadTransactions();
    loadPrediction();
    loadHealth();
    loadBudgets();
}

function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const viewSections = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        if(item.id === 'nav-logout') return; // Skip logout item handling inside tab logic
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navItems.forEach(nav => nav.classList.remove('active'));
            viewSections.forEach(section => section.style.display = 'none');
            item.classList.add('active');
            document.getElementById(item.getAttribute('data-target')).style.display = 'block';
        });
    });
}

function setupAddExpense() {
    const form = document.getElementById('add-expense-form');
    if(!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('add-btn');
        btn.textContent = 'Adding...'; btn.disabled = true;

        const payload = {
            amount: parseFloat(document.getElementById('expense-amount').value),
            merchant: document.getElementById('expense-merchant').value,
            category: document.getElementById('expense-category').value
        };

        try {
            const res = await apiFetch(`/transactions`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            if (res.ok) {
                document.getElementById('add-msg').style.display = 'block';
                form.reset();
                setTimeout(() => document.getElementById('add-msg').style.display = 'none', 3000);
                refreshAllData();
            }
        } catch (e) {
            console.error(e);
        } finally {
            btn.textContent = 'Add Expense'; btn.disabled = false;
        }
    });
}

// -----------------------------------------
// Initialization
// -----------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    setupAuth();
    setupTheme();
    setupNavigation();
    setupAddExpense();
    setupChat();
    setupBulkUpload();
    setupDateFilter();
    
    // Auth state check on load
    if (authToken) {
        processLoginSuccess(authToken, userRole);
    } else {
        processLogout();
    }
});
