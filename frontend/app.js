const API_BASE_URL = 'http://localhost:8000/api';

// Format currency
const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
};

// Format large numbers
const formatNumber = (num) => {
    return new Intl.NumberFormat('en-US').format(num);
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
                    label: 'Monthly Specifics',
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

// Fetch and Populate Transactions Table
async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE_URL}/transactions?limit=15`);
        const data = await response.json();
        
        const tbody = document.querySelector('#transactions-table tbody');
        tbody.innerHTML = '';
        
        data.forEach(txn => {
            const tr = document.createElement('tr');
            
            const statusClass = `status-${txn.status.toLowerCase()}`;
            
            tr.innerHTML = `
                <td style="font-family: monospace; color: var(--primary);">${txn.transaction_id}</td>
                <td>${txn.date}</td>
                <td><strong>${txn.merchant}</strong></td>
                <td>${txn.category}</td>
                <td>${formatCurrency(txn.amount)}</td>
                <td><span class="status-badge ${statusClass}">${txn.status}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error fetching transactions:', error);
    }
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadSummary();
    loadCategoryData();
    loadTrendData();
    loadTransactions();
});
