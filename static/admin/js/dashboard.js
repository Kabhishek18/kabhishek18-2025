// static/js/dashboard.js
class DashboardManager {
    constructor() {
        this.refreshInterval = null;
        this.chart = null;
        this.isAutoRefresh = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupAutoRefresh();
        this.setupKeyboardShortcuts();
        this.loadUserPreferences();
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

        // Real-time updates via WebSocket (if available)
        if (typeof WebSocket !== 'undefined') {
            this.setupWebSocket();
        }
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
                }
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
            const response = await fetch('/core/dashboard/api/');
            if (!response.ok) throw new Error('Failed to refresh dashboard');

            const data = await response.json();
            this.updateDashboard(data.data);
            this.showNotification('Dashboard refreshed successfully', 'success');
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            this.showNotification('Failed to refresh dashboard', 'error');
        } finally {
            if (refreshButton) {