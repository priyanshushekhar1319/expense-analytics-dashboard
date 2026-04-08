const API_BASE_URL = 'http://localhost:8000/api';

// Format currency to Indian Rupees (INR)
const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);
};

// Format large numbers
const formatNumber = (num) => {
    return new Intl.NumberFormat('en-IN').format(num);
};

// Fetch Summary Data
async function loadSummary() {
    try {
        const response = await fetch(`${API_BASE_URL}/summary`);
        const data = await response.json();
        
        document.getElementById('total-expenses').textContent = formatCurrency(data.total_expenses);
        document.getElementById('total-transactions').textContent = formatNumber(data.total_transactions);
    } catch (error) {
        console.error('Error fetching summary:', error);
    }
}

// Fetch Insights Data
async function loadInsights() {
    try {
        const response = await fetch(`${API_BASE_URL}/insights`);
        const data = await response.json();
        
        const container = document.getElementById('ai-insights-container');
        if(!container) return;
        container.innerHTML = '';
        
        data.insights.forEach(insight => {
            const div = document.createElement('div');
            div.className = 'glass';
            div.style.padding = '0.8rem 1.5rem';
            div.style.fontSize = '0.9rem';
            div.style.color = 'var(--text-primary)';
            div.style.borderLeft = '4px solid var(--accent)';
            div.textContent = insight;
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Error fetching insights:', error);
    }
}

// Fetch and Render Category Chart
async function loadCategoryData() {
    try {
        const response = await fetch(`${API_BASE_URL}/expenses/category`);
        const data = await response.json();
        
        if (data.length > 0) {
            document.getElementById('top-category').textContent = data[0].category;
        }

        const labels = data.map(item => item.category);
        const values = data.map(item => item.total);

        const ctx = document.getElementById('categoryChart').getContext('2d');
        new Chart(ctx, {
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
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#94a3b8' }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error fetching categories:', error);
    }
}

// Fetch and Render Trend Chart
async function loadTrendData() {
    try {
        const response = await fetch(`${API_BASE_URL}/expenses/trend`);
        const data = await response.json();

        const labels = data.map(item => item.month);
        const values = data.map(item => item.total);

        const ctx = document.getElementById('trendChart').getContext('2d');
        
        // Create gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.5)');
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monthly Spending',
                    data: values,
                    borderColor: '#6366f1',
                    backgroundColor: gradient,
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#10b981',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    } catch (error) {
        console.error('Error fetching trend:', error);
    }
}

// Fetch and Populate Transactions Tables
async function loadTransactions() {
    try {
        // Fetch 15 for dashboard, 100 for all transactions
        const response15 = await fetch(`${API_BASE_URL}/transactions?limit=15`);
        const data15 = await response15.json();
        
        const response100 = await fetch(`${API_BASE_URL}/transactions?limit=100`);
        const data100 = await response100.json();
        
        const recentTbody = document.getElementById('recent-transactions-body');
        const allTbody = document.getElementById('all-transactions-body');
        
        recentTbody.innerHTML = '';
        allTbody.innerHTML = '';
        
        const createRow = (txn) => {
            const tr = document.createElement('tr');
            const statusClass = `status-${txn.status.toLowerCase()}`;
            tr.innerHTML = `
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
            return tr;
        };

        data15.forEach(txn => {
            recentTbody.appendChild(createRow(txn));
        });

        data100.forEach(txn => {
            allTbody.appendChild(createRow(txn));
        });
        
        // Add delete event listeners
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if(confirm('Are you sure you want to delete this transaction completely?')) {
                    try {
                        const delRes = await fetch(`${API_BASE_URL}/transactions/${id}`, { method: 'DELETE' });
                        if(delRes.ok) {
                            loadSummary();
                            loadCategoryData();
                            loadTrendData();
                            loadTransactions();
                            loadInsights();
                        }
                    } catch(err) {
                        console.error('Failed to delete', err);
                    }
                }
            });
        });

    } catch (error) {
        console.error('Error fetching transactions:', error);
    }
}

// Navigation Logic
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const viewSections = document.querySelectorAll('.view-section');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all nav items
            navItems.forEach(nav => nav.classList.remove('active'));
            
            // Hide all views
            viewSections.forEach(section => section.style.display = 'none');
            
            // Add active class to clicked nav item
            item.classList.add('active');
            
            // Show the target resource
            const targetId = item.getAttribute('data-target');
            document.getElementById(targetId).style.display = 'block';
        });
    });
}

// Add Expense Logic
function setupAddExpense() {
    const form = document.getElementById('add-expense-form');
    if(!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const btn = document.getElementById('add-btn');
        btn.textContent = 'Adding...';
        btn.disabled = true;

        const amount = document.getElementById('expense-amount').value;
        const merchant = document.getElementById('expense-merchant').value;
        const category = document.getElementById('expense-category').value;

        const payload = {
            amount: parseFloat(amount),
            merchant: merchant,
            category: category
        };

        try {
            const response = await fetch(`${API_BASE_URL}/transactions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                document.getElementById('add-msg').style.display = 'block';
                form.reset();
                setTimeout(() => {
                    document.getElementById('add-msg').style.display = 'none';
                }, 3000);
                
                // Refresh data to show the newly added roll!
                loadSummary();
                loadCategoryData();
                loadTrendData();
                loadTransactions();
            }
        } catch (error) {
            console.error('Error adding expense:', error);
        } finally {
            btn.textContent = 'Add Expense';
            btn.disabled = false;
        }
    });
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupAddExpense();
    loadInsights();
    loadSummary();
    loadCategoryData();
    loadTrendData();
    loadTransactions();
});
