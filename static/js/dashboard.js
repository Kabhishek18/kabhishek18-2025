// static/js/dashboard.js
class DashboardManager {
    constructor() {
        this.refreshInterval = null;
        this.chart = null;
        this.isAutoRefresh = false;
        this.websocket = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupAutoRefresh();
        this.setupKeyboardShortcuts();
        this.loadUserPreferences();
        this.initializeChart();
        this.setupNotifications();
    }

    setupEventListeners() {
        // Refresh button
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="refresh"]')) {
                e.preventDefault();
                this.refreshDashboard();
            }
        });

        // Export button
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="export"]')) {
                e.preventDefault();
                this.exportData();
            }
        });

        // Auto-refresh toggle
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-toggle="auto-refresh"]')) {
                this.toggleAutoRefresh(e.target.checked);
            }
        });

        // Dark mode toggle
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-toggle="dark-mode"]')) {
                this.toggleDarkMode();
            }
        });

        // Metric card interactions
        document.addEventListener('click', (e) => {
            const metricCard = e.target.closest('.metric-card');
            if (metricCard) {
                this.animateMetricCard(metricCard);
            }
        });

        // Filter controls
        document.addEventListener('change', (e) => {
            if (e.target.matches('[data-filter]')) {
                this.applyFilter(e.target.dataset.filter, e.target.value);
            }
        });

        // Search functionality
        document.addEventListener('input', (e) => {
            if (e.target.matches('[data-search]')) {
                this.handleSearch(e.target.value);
            }
        });

        // Real-time updates via WebSocket (if available)
        if (typeof WebSocket !== 'undefined') {
            this.setupWebSocket();
        }

        // Window resize handler for chart responsiveness
        window.addEventListener('resize', this.debounce(() => {
            if (this.chart) {
                this.chart.resize();
            }
        }, 250));

        // Visibility change handler (pause updates when tab is hidden)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAutoRefresh();
            } else {
                this.resumeAutoRefresh();
            }
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'r':
                        e.preventDefault();
                        this.refreshDashboard();
                        break;
                    case 'e':
                        e.preventDefault();
                        this.exportData();
                        break;
                    case 'd':
                        e.preventDefault();
                        this.toggleDarkMode();
                        break;
                    case 'f':
                        e.preventDefault();
                        this.focusSearch();
                        break;
                    case 'h':
                        e.preventDefault();
                        this.showKeyboardShortcuts();
                        break;
                }
            }
            
            // Escape key actions
            if (e.key === 'Escape') {
                this.closeModals();
            }
        });
    }

    async refreshDashboard() {
        const refreshButton = document.querySelector('[data-action="refresh"]');
        if (refreshButton) {
            refreshButton.innerHTML = '<span class="material-symbols-outlined animate-spin">refresh</span>';
            refreshButton.disabled = true;
        }

        try {
            const response = await fetch('/core/dashboard/api/', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.updateDashboard(data.data);
            this.showNotification('Dashboard refreshed successfully', 'success');
            this.retryCount = 0; // Reset retry count on success
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            this.handleRefreshError(error);
        } finally {
            if (refreshButton) {
                refreshButton.innerHTML = '<span class="material-symbols-outlined">refresh</span>';
                refreshButton.disabled = false;
            }
        }
    }

    handleRefreshError(error) {
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            this.showNotification(`Refresh failed. Retrying... (${this.retryCount}/${this.maxRetries})`, 'warning');
            setTimeout(() => this.refreshDashboard(), 2000 * this.retryCount);
        } else {
            this.showNotification('Failed to refresh dashboard. Please try again later.', 'error');
            this.retryCount = 0;
        }
    }

    updateDashboard(data) {
        // Update metrics
        this.updateMetrics(data.metrics);
        
        // Update chart
        this.updateChart(data.chart_data);
        
        // Update recent posts
        this.updateRecentPosts(data.recent_posts);
        
        // Update timestamp
        this.updateTimestamp(data.last_updated);
        
        // Trigger update event
        this.dispatchEvent('dashboard:updated', { data });
    }

    updateMetrics(metrics) {
        metrics.forEach((metric, index) => {
            const card = document.querySelector(`[data-metric="${index}"]`);
            if (card) {
                const valueElement = card.querySelector('.metric-value');
                const changeElement = card.querySelector('.metric-change');
                
                if (valueElement) {
                    this.animateNumber(valueElement, metric.value);
                }
                
                if (changeElement && metric.change !== undefined) {
                    changeElement.textContent = `${metric.change > 0 ? '+' : ''}${metric.change}%`;
                    changeElement.className = `metric-change ${metric.change > 0 ? 'positive' : 'negative'}`;
                }
            }
        });
    }

    updateChart(chartData) {
        if (this.chart) {
            this.chart.data.labels = chartData.labels;
            this.chart.data.datasets[0].data = chartData.values;
            this.chart.update('active');
        }
    }

    updateRecentPosts(posts) {
        const container = document.querySelector('.recent-posts-container');
        if (!container) return;

        const postsHTML = posts.map(post => `
            <div class="post-item p-3 rounded-lg" data-post-id="${post.id}">
                <div class="flex items-start space-x-3">
                    <div class="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 text-white">
                        <span class="material-symbols-outlined text-lg">${post.status === 'published' ? 'visibility' : 'edit'}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between mb-1">
                            <a href="${post.url}" class="text-sm font-semibold text-gray-900 dark:text-gray-100 hover:text-primary-600 dark:hover:text-primary-400 transition-colors line-clamp-1">
                                ${post.title}
                            </a>
                            <span class="status-badge status-${post.status}">
                                ${post.status}
                            </span>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400">
                            Updated ${new Date(post.updated_at).toLocaleDateString()}
                        </p>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = postsHTML;
    }

    updateTimestamp(timestamp) {
        const element = document.querySelector('[data-timestamp]');
        if (element) {
            element.textContent = `Last updated: ${new Date(timestamp).toLocaleString()}`;
        }
    }

    animateNumber(element, targetValue) {
        const currentValue = parseInt(element.textContent.replace(/,/g, '')) || 0;
        const increment = Math.ceil((targetValue - currentValue) / 20);
        
        let current = currentValue;
        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= targetValue) || (increment < 0 && current <= targetValue)) {
                current = targetValue;
                clearInterval(timer);
            }
            element.textContent = current.toLocaleString();
        }, 50);
    }

    animateMetricCard(card) {
        card.style.transform = 'scale(0.98)';
        setTimeout(() => {
            card.style.transform = 'scale(1)';
        }, 150);
    }

    toggleAutoRefresh(enabled) {
        this.isAutoRefresh = enabled;
        this.saveUserPreference('autoRefresh', enabled);
        
        if (enabled) {
            this.startAutoRefresh();
            this.showNotification('Auto-refresh enabled (30s interval)', 'info');
        } else {
            this.stopAutoRefresh();
            this.showNotification('Auto-refresh disabled', 'info');
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh(); // Clear existing interval
        this.refreshInterval = setInterval(() => {
            if (!document.hidden) {
                this.refreshDashboard();
            }
        }, 30000); // 30 seconds
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    pauseAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }

    resumeAutoRefresh() {
        if (this.isAutoRefresh) {
            this.startAutoRefresh();
        }
    }

    setupAutoRefresh() {
        const autoRefreshToggle = document.querySelector('[data-toggle="auto-refresh"]');
        if (autoRefreshToggle) {
            const savedPreference = this.getUserPreference('autoRefresh');
            if (savedPreference !== null) {
                autoRefreshToggle.checked = savedPreference;
                this.toggleAutoRefresh(savedPreference);
            }
        }
    }

    toggleDarkMode() {
        const isDark = document.documentElement.classList.contains('dark');
        document.documentElement.classList.toggle('dark', !isDark);
        this.saveUserPreference('darkMode', !isDark);
        
        // Update chart colors if chart exists
        if (this.chart) {
            this.updateChartTheme();
        }
        
        this.showNotification(`${!isDark ? 'Dark' : 'Light'} mode enabled`, 'info');
    }

    updateChartTheme() {
        const isDark = document.documentElement.classList.contains('dark');
        const colors = this.getChartColors(isDark);
        
        this.chart.options.scales.y.grid.color = colors.grid;
        this.chart.options.scales.y.ticks.color = colors.text;
        this.chart.options.scales.x.ticks.color = colors.text;
        this.chart.update('none');
    }

    getChartColors(isDark) {
        return {
            primary: isDark ? '#60A5FA' : '#3B82F6',
            text: isDark ? '#E5E7EB' : '#374151',
            grid: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
            surface: isDark ? '#1F2937' : '#FFFFFF',
        };
    }

    async exportData() {
        const format = document.querySelector('[data-export-format]')?.value || 'json';
        
        try {
            const response = await fetch(`/core/dashboard/export/?format=${format}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (!response.ok) throw new Error('Export failed');

            if (format === 'json') {
                const data = await response.json();
                this.downloadJSON(data, 'dashboard-data.json');
            } else if (format === 'csv') {
                const blob = await response.blob();
                this.downloadBlob(blob, 'dashboard-data.csv');
            }

            this.showNotification('Data exported successfully', 'success');
        } catch (error) {
            console.error('Export error:', error);
            this.showNotification('Export failed', 'error');
        }
    }

    downloadJSON(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        this.downloadBlob(blob, filename);
    }

    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    setupWebSocket() {
        if (this.websocket) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard/`;

        try {
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.showNotification('Real-time updates enabled', 'info');
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket message parsing error:', error);
                }
            };

            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.websocket = null;
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.setupWebSocket(), 5000);
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('WebSocket setup error:', error);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'dashboard_update':
                this.updateDashboard(data.data);
                break;
            case 'notification':
                this.showNotification(data.message, data.level);
                break;
            case 'metric_update':
                this.updateMetrics([data.metric]);
                break;
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }

    initializeChart() {
        const ctx = document.getElementById('contentChart');
        if (!ctx) return;

        const isDark = document.documentElement.classList.contains('dark');
        const colors = this.getChartColors(isDark);

        // Get data from the page
        const chartData = window.chartData || { labels: [], values: [] };

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Count',
                    data: chartData.values,
                    backgroundColor: this.createGradient(ctx, colors.primary),
                    borderColor: colors.primary,
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: colors.surface,
                        titleColor: colors.text,
                        bodyColor: colors.text,
                        borderColor: colors.grid,
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 12,
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: colors.grid },
                        ticks: { color: colors.text }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: colors.text }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart',
                }
            }
        });
    }

    createGradient(ctx, color) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, color + '40');
        return gradient;
    }

    setupNotifications() {
        // Create notification container if it doesn't exist
        if (!document.querySelector('.notification-container')) {
            const container = document.createElement('div');
            container.className = 'notification-container fixed top-4 right-4 z-50 space-y-2';
            document.body.appendChild(container);
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        const container = document.querySelector('.notification-container');
        if (!container) return;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type} p-4 rounded-lg shadow-lg transform translate-x-full transition-transform duration-300 ease-out`;
        
        const colors = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            warning: 'bg-yellow-500 text-white',
            info: 'bg-blue-500 text-white'
        };

        notification.className += ` ${colors[type] || colors.info}`;
        notification.innerHTML = `
            <div class="flex items-center space-x-3">
                <span class="material-symbols-outlined">${this.getNotificationIcon(type)}</span>
                <span>${message}</span>
                <button class="ml-auto" onclick="this.parentElement.parentElement.remove()">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
        `;

        container.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 10);

        // Auto-remove after duration
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check_circle',
            error: 'error',
            warning: 'warning',
            info: 'info'
        };
        return icons[type] || icons.info;
    }

    applyFilter(filterType, value) {
        // Handle different filter types
        switch (filterType) {
            case 'date-range':
                this.filterByDateRange(value);
                break;
            case 'status':
                this.filterByStatus(value);
                break;
            case 'category':
                this.filterByCategory(value);
                break;
            default:
                console.log('Unknown filter type:', filterType);
        }
    }

    handleSearch(query) {
        const items = document.querySelectorAll('[data-searchable]');
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            const matches = text.includes(query.toLowerCase());
            item.style.display = matches ? 'block' : 'none';
        });
    }

    focusSearch() {
        const searchInput = document.querySelector('[data-search]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    showKeyboardShortcuts() {
        const shortcuts = [
            { key: 'Ctrl+R', action: 'Refresh dashboard' },
            { key: 'Ctrl+E', action: 'Export data' },
            { key: 'Ctrl+D', action: 'Toggle dark mode' },
            { key: 'Ctrl+F', action: 'Focus search' },
            { key: 'Ctrl+H', action: 'Show shortcuts' },
            { key: 'Esc', action: 'Close modals' }
        ];

        const modal = this.createModal('Keyboard Shortcuts', shortcuts.map(s => 
            `<div class="flex justify-between py-2">
                <span class="font-mono bg-gray-100 px-2 py-1 rounded">${s.key}</span>
                <span>${s.action}</span>
            </div>`
        ).join(''));

        document.body.appendChild(modal);
    }

    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                <h3 class="text-lg font-semibold mb-4">${title}</h3>
                <div class="space-y-2">${content}</div>
                <button class="mt-4 px-4 py-2 bg-primary-500 text-white rounded hover:bg-primary-600" onclick="this.closest('.modal').remove()">
                    Close
                </button>
            </div>
        `;
        return modal;
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => modal.remove());
    }

    loadUserPreferences() {
        const darkMode = this.getUserPreference('darkMode');
        if (darkMode !== null) {
            document.documentElement.classList.toggle('dark', darkMode);
        }
    }

    getUserPreference(key) {
        try {
            const value = localStorage.getItem(`dashboard_${key}`);
            return value ? JSON.parse(value) : null;
        } catch (error) {
            console.error('Error loading user preference:', error);
            return null;
        }
    }

    saveUserPreference(key, value) {
        try {
            localStorage.setItem(`dashboard_${key}`, JSON.stringify(value));
        } catch (error) {
            console.error('Error saving user preference:', error);
        }
    }

    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    destroy() {
        this.stopAutoRefresh();
        if (this.websocket) {
            this.websocket.close();
        }
        document.removeEventListener('keydown', this.handleKeydown);
        document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        window.removeEventListener('resize', this.handleResize);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboardManager) {
        window.dashboardManager.destroy();
    }
});