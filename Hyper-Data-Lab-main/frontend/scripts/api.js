// API Configuration and Helper Functions
let API_BASE_URL = 'http://localhost:8000/api/v1'; // Default fallback
let configLoaded = false;

// Load configuration from backend
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        API_BASE_URL = config.apiBaseUrl;
        configLoaded = true;
        console.log('API Config loaded:', API_BASE_URL);
    } catch (error) {
        console.warn('Failed to load config, using default:', API_BASE_URL);
        configLoaded = true; // Mark as loaded even if failed to allow proceeding
    }
}

// Initialize configuration immediately
const configPromise = loadConfig();

class APIClient {
    constructor() {
        // Don't store baseURL, always use the global API_BASE_URL
    }

    async request(endpoint, options = {}) {
        // Wait for config to load before making requests
        if (!configLoaded) {
            await configPromise;
        }
        
        // Always use the current API_BASE_URL value
        const url = `${API_BASE_URL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! status: ${response.status}`);
            }

            return { success: true, data };
        } catch (error) {
            console.error('API Request Error:', error);
            return { success: false, error: error.message };
        }
    }

    // Scraper Endpoints
    async scrapeSingle(symbol, headless = true) {
        return this.request('/scrapper/scrape', {
            method: 'POST',
            body: JSON.stringify({
                symbol,
                headless
            }),
        });
    }

    async scrapeBulk(symbols, headless = true) {
        return this.request('/scrapper/scrape-bulk', {
            method: 'POST',
            body: JSON.stringify({
                symbols,
                headless
            }),
        });
    }

    // Financial Data Endpoints
    async getReports(params = {}) {
        const queryParams = new URLSearchParams();
        
        if (params.symbol) queryParams.append('symbol', params.symbol);
        if (params.report_type) queryParams.append('report_type', params.report_type);
        if (params.report_year) queryParams.append('report_year', params.report_year);
        if (params.limit) queryParams.append('limit', params.limit);
        if (params.offset) queryParams.append('offset', params.offset);

        const queryString = queryParams.toString();
        const endpoint = `/financial/reports${queryString ? '?' + queryString : ''}`;
        
        return this.request(endpoint);
    }

    async getReportById(id) {
        return this.request(`/financial/reports/${id}`);
    }

    async getReportsBySymbol(symbol) {
        return this.request(`/financial/reports/symbol/${symbol}`);
    }

    async deleteReport(id) {
        return this.request(`/financial/reports/${id}`, {
            method: 'DELETE',
        });
    }

    async deleteReportsBySymbol(symbol) {
        return this.request(`/financial/reports/symbol/${symbol}`, {
            method: 'DELETE',
        });
    }

    async getStats() {
        return this.request('/financial/stats');
    }

    async getBalanceSheetItems(reportId) {
        return this.request(`/financial/reports/${reportId}/balance-sheet`);
    }

    async getIncomeStatementItems(reportId) {
        return this.request(`/financial/reports/${reportId}/income-statement`);
    }

    async getCashFlowItems(reportId) {
        return this.request(`/financial/reports/${reportId}/cash-flow`);
    }

    // Health Check
    async healthCheck() {
        return this.request('/health', { baseURL: 'http://localhost:8000' });
    }
}

// Create global API client instance
const api = new APIClient();

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function formatReportPeriod(reportType, year, quarter) {
    if (reportType === 'annual') {
        return `${year} (Annual)`;
    } else if (reportType === 'quarterly' && quarter) {
        return `Q${quarter}/${year}`;
    }
    return `${year}`;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { api, APIClient, formatDate, formatReportPeriod, showToast, escapeHtml };
}
