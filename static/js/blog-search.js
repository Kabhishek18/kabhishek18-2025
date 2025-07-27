/**
 * Enhanced Blog Search and Navigation JavaScript
 * Handles advanced search, filtering, suggestions, and navigation
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize search functionality
    initializeSearch();
    initializeAdvancedFilters();
    initializePagination();
});

function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchSuggestions = document.getElementById('searchSuggestions');
    const searchForm = document.getElementById('searchForm');
    
    if (!searchInput) return;
    
    let searchTimeout;
    let currentSuggestionIndex = -1;
    
    // Search input event handlers
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length >= 2) {
            searchTimeout = setTimeout(() => {
                fetchSearchSuggestions(query);
            }, 300);
        } else {
            hideSuggestions();
        }
    });
    
    // Keyboard navigation for suggestions
    searchInput.addEventListener('keydown', function(e) {
        const suggestions = searchSuggestions.querySelectorAll('.suggestion-item');
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                currentSuggestionIndex = Math.min(currentSuggestionIndex + 1, suggestions.length - 1);
                updateSuggestionHighlight(suggestions);
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                currentSuggestionIndex = Math.max(currentSuggestionIndex - 1, -1);
                updateSuggestionHighlight(suggestions);
                break;
                
            case 'Enter':
                if (currentSuggestionIndex >= 0 && suggestions[currentSuggestionIndex]) {
                    e.preventDefault();
                    selectSuggestion(suggestions[currentSuggestionIndex]);
                }
                break;
                
            case 'Escape':
                hideSuggestions();
                searchInput.blur();
                break;
        }
    });
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchSuggestions.contains(e.target)) {
            hideSuggestions();
        }
    });
    
    // Fetch search suggestions
    async function fetchSearchSuggestions(query) {
        try {
            const response = await fetch(`/blog/search/suggestions/?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.suggestions && data.suggestions.length > 0) {
                displaySuggestions(data.suggestions);
            } else {
                hideSuggestions();
            }
        } catch (error) {
            console.error('Error fetching search suggestions:', error);
            hideSuggestions();
        }
    }
    
    // Display search suggestions
    function displaySuggestions(suggestions) {
        searchSuggestions.innerHTML = '';
        currentSuggestionIndex = -1;
        
        suggestions.forEach((suggestion, index) => {
            const suggestionElement = document.createElement('div');
            suggestionElement.className = 'suggestion-item';
            suggestionElement.innerHTML = `
                <div class="suggestion-text">${escapeHtml(suggestion.text)}</div>
                <div class="suggestion-category">${escapeHtml(suggestion.category)}</div>
            `;
            
            suggestionElement.addEventListener('click', () => selectSuggestion(suggestionElement));
            suggestionElement.addEventListener('mouseenter', () => {
                currentSuggestionIndex = index;
                updateSuggestionHighlight(searchSuggestions.querySelectorAll('.suggestion-item'));
            });
            
            searchSuggestions.appendChild(suggestionElement);
        });
        
        searchSuggestions.classList.add('active');
    }
    
    // Update suggestion highlight
    function updateSuggestionHighlight(suggestions) {
        suggestions.forEach((suggestion, index) => {
            suggestion.classList.toggle('highlighted', index === currentSuggestionIndex);
        });
    }
    
    // Select a suggestion
    function selectSuggestion(suggestionElement) {
        const text = suggestionElement.querySelector('.suggestion-text').textContent;
        searchInput.value = text;
        hideSuggestions();
        searchForm.submit();
    }
    
    // Hide suggestions
    function hideSuggestions() {
        searchSuggestions.classList.remove('active');
        currentSuggestionIndex = -1;
    }
}

function initializeAdvancedFilters() {
    const advancedToggle = document.getElementById('advancedSearchToggle');
    const advancedPanel = document.getElementById('advancedSearchPanel');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const clearFiltersBtn = document.getElementById('clearFilters');
    
    if (!advancedToggle || !advancedPanel) return;
    
    // Toggle advanced search panel
    advancedToggle.addEventListener('click', function() {
        const isActive = advancedPanel.classList.contains('active');
        
        if (isActive) {
            advancedPanel.classList.remove('active');
            advancedToggle.classList.remove('active');
        } else {
            advancedPanel.classList.add('active');
            advancedToggle.classList.add('active');
        }
    });
    
    // Apply filters
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            applyAdvancedFilters();
        });
    }
    
    // Clear filters
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            clearAllFilters();
        });
    }
    
    // Auto-apply filters when select values change
    const filterSelects = advancedPanel.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            // Optional: Auto-apply filters on change
            // applyAdvancedFilters();
        });
    });
}

function applyAdvancedFilters() {
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const tagFilter = document.getElementById('tagFilter');
    const dateFilter = document.getElementById('dateFilter');
    const sortFilter = document.getElementById('sortFilter');
    
    // Build URL with filters
    const params = new URLSearchParams();
    
    if (searchInput && searchInput.value.trim()) {
        params.set('q', searchInput.value.trim());
    }
    
    if (categoryFilter && categoryFilter.value !== 'all') {
        params.set('category', categoryFilter.value);
    }
    
    if (tagFilter && tagFilter.value !== 'all') {
        params.set('tag', tagFilter.value);
    }
    
    if (dateFilter && dateFilter.value !== 'all') {
        params.set('date_range', dateFilter.value);
    }
    
    if (sortFilter && sortFilter.value !== 'newest') {
        params.set('sort', sortFilter.value);
    }
    
    // Navigate to filtered results
    const baseUrl = '/blog/';
    const fullUrl = params.toString() ? `${baseUrl}?${params.toString()}` : baseUrl;
    window.location.href = fullUrl;
}

function clearAllFilters() {
    // Clear all filter inputs
    const searchInput = document.getElementById('searchInput');
    const categoryFilter = document.getElementById('categoryFilter');
    const tagFilter = document.getElementById('tagFilter');
    const dateFilter = document.getElementById('dateFilter');
    const sortFilter = document.getElementById('sortFilter');
    
    if (searchInput) searchInput.value = '';
    if (categoryFilter) categoryFilter.value = 'all';
    if (tagFilter) tagFilter.value = 'all';
    if (dateFilter) dateFilter.value = 'all';
    if (sortFilter) sortFilter.value = 'newest';
    
    // Navigate to clean blog list
    window.location.href = '/blog/';
}

function initializePagination() {
    // Enhanced pagination with keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return; // Don't interfere with form inputs
        }
        
        const currentPage = document.querySelector('.page-btn.active');
        if (!currentPage) return;
        
        let targetLink = null;
        
        switch(e.key) {
            case 'ArrowLeft':
                targetLink = document.querySelector('.pagination a[href*="page=' + (parseInt(currentPage.textContent) - 1) + '"]');
                break;
                
            case 'ArrowRight':
                targetLink = document.querySelector('.pagination a[href*="page=' + (parseInt(currentPage.textContent) + 1) + '"]');
                break;
        }
        
        if (targetLink && !targetLink.classList.contains('disabled')) {
            e.preventDefault();
            targetLink.click();
        }
    });
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
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

// Search result highlighting enhancement
function highlightSearchTerms() {
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');
    
    if (!query) return;
    
    // Highlight search terms in visible content
    const contentElements = document.querySelectorAll('.blog-card-title, .blog-excerpt');
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    
    contentElements.forEach(element => {
        if (element.innerHTML.includes('search-highlight')) return; // Already highlighted
        
        element.innerHTML = element.innerHTML.replace(regex, '<mark class="search-highlight">$1</mark>');
    });
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Initialize highlighting after page load
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(highlightSearchTerms, 100);
});

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Loading states for AJAX requests
function showLoadingState(element) {
    element.classList.add('loading');
    element.style.opacity = '0.6';
    element.style.pointerEvents = 'none';
}

function hideLoadingState(element) {
    element.classList.remove('loading');
    element.style.opacity = '';
    element.style.pointerEvents = '';
}

// Error handling for failed requests
function handleSearchError(error) {
    console.error('Search error:', error);
    
    // Show user-friendly error message
    const errorMessage = document.createElement('div');
    errorMessage.className = 'search-error-message';
    errorMessage.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        <span>Search temporarily unavailable. Please try again.</span>
    `;
    
    const searchContainer = document.querySelector('.search-container');
    if (searchContainer) {
        searchContainer.appendChild(errorMessage);
        
        setTimeout(() => {
            errorMessage.remove();
        }, 5000);
    }
}
/
/ Initialize per-page selector
document.addEventListener('DOMContentLoaded', function() {
    const perPageSelect = document.getElementById('perPageSelect');
    
    if (perPageSelect) {
        perPageSelect.addEventListener('change', function() {
            const currentUrl = new URL(window.location);
            currentUrl.searchParams.set('per_page', this.value);
            currentUrl.searchParams.delete('page'); // Reset to first page
            window.location.href = currentUrl.toString();
        });
    }
});

// Enhanced category and tag link interactions
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth transitions for category links
    const categoryLinks = document.querySelectorAll('.category-link, .subcategory-link');
    
    categoryLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(4px)';
        });
        
        link.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
    
    // Add click analytics for tags and categories
    const tagLinks = document.querySelectorAll('.tag-link, .post-tag');
    
    tagLinks.forEach(link => {
        link.addEventListener('click', function() {
            // Optional: Track tag/category clicks for analytics
            const tagName = this.textContent.trim();
            console.log('Tag clicked:', tagName);
        });
    });
});

// Keyboard shortcuts for search and navigation
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
    
    // Escape to clear search
    if (e.key === 'Escape') {
        const searchInput = document.getElementById('searchInput');
        if (searchInput && document.activeElement === searchInput) {
            searchInput.value = '';
            searchInput.blur();
            hideSuggestions();
        }
    }
});

// Add loading animation for search
function addSearchLoadingAnimation() {
    const searchIcon = document.querySelector('.search-icon i');
    if (searchIcon) {
        searchIcon.classList.add('fa-spin');
        setTimeout(() => {
            searchIcon.classList.remove('fa-spin');
        }, 1000);
    }
}

// Enhanced error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
});

// Performance optimization: Lazy load suggestions
let suggestionCache = new Map();

async function fetchSearchSuggestionsCached(query) {
    if (suggestionCache.has(query)) {
        return suggestionCache.get(query);
    }
    
    try {
        const response = await fetch(`/blog/search/suggestions/?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        // Cache the result for 5 minutes
        suggestionCache.set(query, data);
        setTimeout(() => {
            suggestionCache.delete(query);
        }, 5 * 60 * 1000);
        
        return data;
    } catch (error) {
        console.error('Error fetching search suggestions:', error);
        return { suggestions: [] };
    }
}