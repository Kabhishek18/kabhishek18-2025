/**
 * Table of Contents JavaScript Functionality
 * 
 * Provides interactive features for the table of contents including:
 * - Scroll spy for active section highlighting
 * - Smooth scrolling to sections
 * - Toggle functionality for collapsing/expanding
 * - Progress tracking
 */

class TableOfContents {
    constructor() {
        this.toc = document.querySelector('.table-of-contents');
        this.tocLinks = document.querySelectorAll('.toc-link');
        this.tocToggle = document.querySelector('.toc-toggle');
        this.headings = document.querySelectorAll('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]');
        
        this.currentActiveLink = null;
        this.isScrolling = false;
        this.scrollTimeout = null;
        
        if (this.toc && this.tocLinks.length > 0) {
            this.init();
        }
    }
    
    init() {
        this.setupToggleButton();
        this.setupSmoothScrolling();
        this.setupScrollSpy();
        this.setupProgressIndicator();
        this.setupKeyboardNavigation();
        this.setupIntersectionObserver();
        
        // Initial active link setup
        this.updateActiveLink();
        
        console.log('Table of Contents initialized with', this.tocLinks.length, 'links');
    }
    
    setupToggleButton() {
        if (!this.tocToggle) return;
        
        this.tocToggle.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleTOC();
        });
        
        // Load saved state from localStorage
        const isCollapsed = localStorage.getItem('toc-collapsed') === 'true';
        if (isCollapsed) {
            this.toc.classList.add('collapsed');
        }
    }
    
    toggleTOC() {
        const isCollapsed = this.toc.classList.toggle('collapsed');
        
        // Save state to localStorage
        localStorage.setItem('toc-collapsed', isCollapsed.toString());
        
        // Update aria-expanded for accessibility
        this.tocToggle.setAttribute('aria-expanded', (!isCollapsed).toString());
        
        // Announce to screen readers
        const announcement = isCollapsed ? 'Table of contents collapsed' : 'Table of contents expanded';
        this.announceToScreenReader(announcement);
    }
    
    setupSmoothScrolling() {
        this.tocLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                const targetId = link.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    this.isScrolling = true;
                    
                    // Calculate offset for sticky headers
                    const offset = this.calculateScrollOffset();
                    const targetPosition = targetElement.offsetTop - offset;
                    
                    // Smooth scroll to target
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                    
                    // Update active link immediately
                    this.setActiveLink(link);
                    
                    // Reset scrolling flag after animation
                    setTimeout(() => {
                        this.isScrolling = false;
                    }, 1000);
                    
                    // Focus the target heading for accessibility
                    setTimeout(() => {
                        targetElement.focus();
                        targetElement.scrollIntoView({ block: 'nearest' });
                    }, 500);
                }
            });
        });
    }
    
    setupScrollSpy() {
        let ticking = false;
        
        const updateScrollSpy = () => {
            if (!this.isScrolling) {
                this.updateActiveLink();
            }
            ticking = false;
        };
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(updateScrollSpy);
                ticking = true;
            }
        });
        
        // Also update on resize
        window.addEventListener('resize', () => {
            clearTimeout(this.scrollTimeout);
            this.scrollTimeout = setTimeout(() => {
                this.updateActiveLink();
            }, 100);
        });
    }
    
    setupIntersectionObserver() {
        // Use Intersection Observer for better performance
        const observerOptions = {
            rootMargin: '-20% 0px -35% 0px',
            threshold: 0
        };
        
        const observer = new IntersectionObserver((entries) => {
            if (this.isScrolling) return;
            
            entries.forEach(entry => {
                const id = entry.target.id;
                const link = document.querySelector(`.toc-link[href="#${id}"]`);
                
                if (entry.isIntersecting && link) {
                    this.setActiveLink(link);
                }
            });
        }, observerOptions);
        
        // Observe all headings
        this.headings.forEach(heading => {
            observer.observe(heading);
        });
    }
    
    updateActiveLink() {
        const scrollPosition = window.scrollY + this.calculateScrollOffset() + 50;
        let activeHeading = null;
        
        // Find the current heading
        for (let i = this.headings.length - 1; i >= 0; i--) {
            const heading = this.headings[i];
            if (heading.offsetTop <= scrollPosition) {
                activeHeading = heading;
                break;
            }
        }
        
        if (activeHeading) {
            const activeLink = document.querySelector(`.toc-link[href="#${activeHeading.id}"]`);
            if (activeLink && activeLink !== this.currentActiveLink) {
                this.setActiveLink(activeLink);
            }
        }
    }
    
    setActiveLink(link) {
        // Remove active class from all links
        this.tocLinks.forEach(l => l.classList.remove('active'));
        
        // Add active class to current link
        if (link) {
            link.classList.add('active');
            this.currentActiveLink = link;
            
            // Scroll TOC to show active link
            this.scrollTOCToActiveLink(link);
            
            // Update progress indicator
            this.updateProgressIndicator(link);
        }
    }
    
    scrollTOCToActiveLink(link) {
        const tocList = this.toc.querySelector('.toc-list');
        if (!tocList) return;
        
        const linkRect = link.getBoundingClientRect();
        const tocRect = tocList.getBoundingClientRect();
        
        // Check if link is visible in TOC
        if (linkRect.top < tocRect.top || linkRect.bottom > tocRect.bottom) {
            const scrollTop = link.offsetTop - tocList.offsetTop - (tocList.clientHeight / 2) + (link.clientHeight / 2);
            
            tocList.scrollTo({
                top: scrollTop,
                behavior: 'smooth'
            });
        }
    }
    
    setupProgressIndicator() {
        // Create progress indicator element
        const progressIndicator = document.createElement('div');
        progressIndicator.className = 'toc-progress';
        this.toc.appendChild(progressIndicator);
        
        this.progressIndicator = progressIndicator;
    }
    
    updateProgressIndicator(activeLink) {
        if (!this.progressIndicator || !activeLink) return;
        
        const tocList = this.toc.querySelector('.toc-list');
        if (!tocList) return;
        
        const linkIndex = Array.from(this.tocLinks).indexOf(activeLink);
        const progress = (linkIndex + 1) / this.tocLinks.length;
        const height = progress * tocList.clientHeight;
        
        this.progressIndicator.style.height = `${height}px`;
    }
    
    setupKeyboardNavigation() {
        this.toc.addEventListener('keydown', (e) => {
            const focusedLink = document.activeElement;
            
            if (!focusedLink.classList.contains('toc-link')) return;
            
            const currentIndex = Array.from(this.tocLinks).indexOf(focusedLink);
            let nextIndex = currentIndex;
            
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    nextIndex = Math.min(currentIndex + 1, this.tocLinks.length - 1);
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    nextIndex = Math.max(currentIndex - 1, 0);
                    break;
                    
                case 'Home':
                    e.preventDefault();
                    nextIndex = 0;
                    break;
                    
                case 'End':
                    e.preventDefault();
                    nextIndex = this.tocLinks.length - 1;
                    break;
                    
                case 'Enter':
                case ' ':
                    e.preventDefault();
                    focusedLink.click();
                    return;
                    
                default:
                    return;
            }
            
            if (nextIndex !== currentIndex) {
                this.tocLinks[nextIndex].focus();
            }
        });
    }
    
    calculateScrollOffset() {
        // Calculate offset for sticky headers, navigation, etc.
        let offset = 20; // Base offset
        
        // Check for sticky navigation
        const stickyNav = document.querySelector('.detail-nav');
        if (stickyNav) {
            offset += stickyNav.offsetHeight;
        }
        
        // Check for reading progress bar
        const progressBar = document.querySelector('.reading-progress');
        if (progressBar) {
            offset += progressBar.offsetHeight;
        }
        
        return offset;
    }
    
    announceToScreenReader(message) {
        // Create temporary element for screen reader announcements
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        // Remove after announcement
        setTimeout(() => {
            document.body.removeChild(announcement);
        }, 1000);
    }
    
    // Public methods for external control
    scrollToHeading(headingId) {
        const link = document.querySelector(`.toc-link[href="#${headingId}"]`);
        if (link) {
            link.click();
        }
    }
    
    expandTOC() {
        this.toc.classList.remove('collapsed');
        localStorage.setItem('toc-collapsed', 'false');
    }
    
    collapseTOC() {
        this.toc.classList.add('collapsed');
        localStorage.setItem('toc-collapsed', 'true');
    }
    
    getCurrentSection() {
        return this.currentActiveLink ? this.currentActiveLink.getAttribute('href').substring(1) : null;
    }
    
    getProgress() {
        if (!this.currentActiveLink) return 0;
        const currentIndex = Array.from(this.tocLinks).indexOf(this.currentActiveLink);
        return (currentIndex + 1) / this.tocLinks.length;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize table of contents
    window.tableOfContents = new TableOfContents();
    
    // Add global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Toggle TOC with Ctrl/Cmd + T
        if ((e.ctrlKey || e.metaKey) && e.key === 't' && window.tableOfContents) {
            e.preventDefault();
            window.tableOfContents.toggleTOC();
        }
    });
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TableOfContents;
}