/**
 * Enhanced Blog Detail Page JavaScript
 * Handles interactive features for blog post pages including:
 * - Reading progress tracking
 * - Comment form validation and submission
 * - Social sharing functionality
 * - Bookmark/save functionality
 * - Comment reply system
 * - Smooth scrolling and navigation
 */

class BlogDetailManager {
    constructor() {
        this.readingProgress = document.getElementById('readingProgress');
        this.shareBtn = document.getElementById('shareBtn');
        this.bookmarkBtn = document.getElementById('bookmarkBtn');
        this.commentForm = document.getElementById('commentForm');
        this.commentPreview = document.getElementById('commentPreview');
        
        this.init();
    }
    
    init() {
        this.setupReadingProgress();
        this.setupSocialSharing();
        this.setupBookmarkSystem();
        this.setupCommentSystem();
        this.setupSmoothScrolling();
        this.setupKeyboardShortcuts();
        
        console.log('Blog Detail Manager initialized');
    }
    
    setupReadingProgress() {
        if (!this.readingProgress) return;
        
        const updateProgress = () => {
            const article = document.querySelector('.article-content');
            if (!article) return;
            
            const articleTop = article.offsetTop;
            const articleHeight = article.offsetHeight;
            const windowHeight = window.innerHeight;
            const scrollTop = window.pageYOffset;
            
            const articleBottom = articleTop + articleHeight;
            const windowBottom = scrollTop + windowHeight;
            
            if (scrollTop >= articleTop && scrollTop <= articleBottom - windowHeight) {
                const progress = ((scrollTop - articleTop) / (articleHeight - windowHeight)) * 100;
                this.readingProgress.style.width = Math.min(Math.max(progress, 0), 100) + '%';
            } else if (scrollTop < articleTop) {
                this.readingProgress.style.width = '0%';
            } else {
                this.readingProgress.style.width = '100%';
            }
        };
        
        window.addEventListener('scroll', this.throttle(updateProgress, 16));
        updateProgress(); // Initial call
    }
    
    setupSocialSharing() {
        if (!this.shareBtn) return;
        
        this.shareBtn.addEventListener('click', () => {
            const url = window.location.href;
            const title = document.querySelector('.article-title')?.textContent || document.title;
            
            // Check if Web Share API is supported
            if (navigator.share) {
                navigator.share({
                    title: title,
                    url: url
                }).catch(err => console.log('Error sharing:', err));
            } else {
                // Fallback: Copy to clipboard
                this.copyToClipboard(url);
                this.showNotification('Link copied to clipboard!', 'success');
            }
        });
    }
    
    setupBookmarkSystem() {
        if (!this.bookmarkBtn) return;
        
        const postSlug = this.getPostSlug();
        const savedPosts = this.getSavedPosts();
        const isBookmarked = savedPosts.includes(postSlug);
        
        this.updateBookmarkButton(isBookmarked);
        
        this.bookmarkBtn.addEventListener('click', () => {
            const currentlySaved = savedPosts.includes(postSlug);
            
            if (currentlySaved) {
                this.removeBookmark(postSlug);
                this.updateBookmarkButton(false);
                this.showNotification('Article removed from saved items', 'info');
            } else {
                this.addBookmark(postSlug);
                this.updateBookmarkButton(true);
                this.showNotification('Article saved successfully!', 'success');
            }
        });
    }
    
    setupCommentSystem() {
        if (!this.commentForm) return;
        
        this.setupCommentFormValidation();
        this.setupCommentPreview();
        this.setupReplySystem();
        this.setupCommentSorting();
        this.setupCharacterCounter();
    }
    
    setupCommentFormValidation() {
        const nameInput = document.getElementById('id_author_name');
        const emailInput = document.getElementById('id_author_email');
        const contentInput = document.getElementById('id_content');
        const submitBtn = document.getElementById('submitBtn');
        
        if (!nameInput || !emailInput || !contentInput || !submitBtn) return;
        
        // Real-time validation
        nameInput.addEventListener('blur', () => this.validateField(nameInput, 'name'));
        emailInput.addEventListener('blur', () => this.validateField(emailInput, 'email'));
        contentInput.addEventListener('blur', () => this.validateField(contentInput, 'content'));
        
        // Form submission
        this.commentForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            if (this.validateCommentForm()) {
                this.submitComment();
            }
        });
    }
    
    setupCommentPreview() {
        const previewBtn = document.getElementById('previewBtn');
        const closePreviewBtn = document.getElementById('closePreviewBtn');
        
        if (!previewBtn || !closePreviewBtn) return;
        
        previewBtn.addEventListener('click', () => {
            this.showCommentPreview();
        });
        
        closePreviewBtn.addEventListener('click', () => {
            this.hideCommentPreview();
        });
    }
    
    setupReplySystem() {
        // Setup reply buttons
        document.querySelectorAll('.reply-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const commentId = e.target.closest('.comment').id.split('-')[1];
                this.toggleReplyForm(commentId);
            });
        });
        
        // Setup reply form submissions
        document.querySelectorAll('.reply-form').forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.submitReply(form);
            });
        });
    }
    
    setupCommentSorting() {
        const sortSelect = document.getElementById('commentSort');
        if (!sortSelect) return;
        
        sortSelect.addEventListener('change', (e) => {
            this.sortComments(e.target.value);
        });
    }
    
    setupCharacterCounter() {
        const contentInput = document.getElementById('id_content');
        const charCount = document.getElementById('charCount');
        
        if (!contentInput || !charCount) return;
        
        const updateCounter = () => {
            const count = contentInput.value.length;
            charCount.textContent = count;
            
            if (count > 1800) {
                charCount.style.color = 'var(--accent-orange)';
            } else if (count > 2000) {
                charCount.style.color = 'var(--accent-pink)';
            } else {
                charCount.style.color = 'var(--text-muted)';
            }
        };
        
        contentInput.addEventListener('input', updateCounter);
        updateCounter(); // Initial call
    }
    
    setupSmoothScrolling() {
        // Smooth scroll to comments when hash is present
        if (window.location.hash === '#comments') {
            setTimeout(() => {
                document.getElementById('comments')?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }, 100);
        }
        
        // Handle anchor links
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = link.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Update URL without triggering scroll
                    history.pushState(null, null, `#${targetId}`);
                }
            });
        });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + S to bookmark
            if ((e.ctrlKey || e.metaKey) && e.key === 's' && this.bookmarkBtn) {
                e.preventDefault();
                this.bookmarkBtn.click();
            }
            
            // Ctrl/Cmd + Shift + S to share
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S' && this.shareBtn) {
                e.preventDefault();
                this.shareBtn.click();
            }
            
            // Escape to close preview
            if (e.key === 'Escape' && this.commentPreview && this.commentPreview.style.display !== 'none') {
                this.hideCommentPreview();
            }
        });
    }
    
    // Comment form validation methods
    validateField(field, type) {
        const errorElement = document.getElementById(`${type}-error`);
        let isValid = true;
        let errorMessage = '';
        
        switch (type) {
            case 'name':
                if (!field.value.trim()) {
                    errorMessage = 'Name is required';
                    isValid = false;
                } else if (field.value.trim().length < 2) {
                    errorMessage = 'Name must be at least 2 characters';
                    isValid = false;
                }
                break;
                
            case 'email':
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!field.value.trim()) {
                    errorMessage = 'Email is required';
                    isValid = false;
                } else if (!emailRegex.test(field.value)) {
                    errorMessage = 'Please enter a valid email address';
                    isValid = false;
                }
                break;
                
            case 'content':
                if (!field.value.trim()) {
                    errorMessage = 'Comment content is required';
                    isValid = false;
                } else if (field.value.trim().length < 10) {
                    errorMessage = 'Comment must be at least 10 characters';
                    isValid = false;
                } else if (field.value.length > 2000) {
                    errorMessage = 'Comment must be less than 2000 characters';
                    isValid = false;
                }
                break;
        }
        
        if (errorElement) {
            if (isValid) {
                errorElement.classList.remove('show');
                field.classList.remove('error');
            } else {
                errorElement.textContent = errorMessage;
                errorElement.classList.add('show');
                field.classList.add('error');
            }
        }
        
        return isValid;
    }
    
    validateCommentForm() {
        const nameInput = document.getElementById('id_author_name');
        const emailInput = document.getElementById('id_author_email');
        const contentInput = document.getElementById('id_content');
        
        const nameValid = this.validateField(nameInput, 'name');
        const emailValid = this.validateField(emailInput, 'email');
        const contentValid = this.validateField(contentInput, 'content');
        
        return nameValid && emailValid && contentValid;
    }
    
    async submitComment() {
        const submitBtn = document.getElementById('submitBtn');
        const btnText = submitBtn.querySelector('span');
        const btnLoader = submitBtn.querySelector('.btn-loader');
        
        // Show loading state
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'block';
        
        try {
            const formData = new FormData(this.commentForm);
            const response = await fetch(this.commentForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken')
                }
            });
            
            if (response.ok) {
                this.showNotification('Comment submitted successfully! It will appear after moderation.', 'success');
                this.commentForm.reset();
                this.hideCommentPreview();
                
                // Update character counter
                const charCount = document.getElementById('charCount');
                if (charCount) charCount.textContent = '0';
            } else {
                throw new Error('Failed to submit comment');
            }
        } catch (error) {
            console.error('Comment submission error:', error);
            this.showNotification('Failed to submit comment. Please try again.', 'error');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        }
    }
    
    showCommentPreview() {
        const contentInput = document.getElementById('id_content');
        const previewContent = this.commentPreview.querySelector('.preview-content');
        
        if (!contentInput.value.trim()) {
            this.showNotification('Please enter some content to preview', 'warning');
            return;
        }
        
        // Simple preview (in a real app, you might want to process markdown, etc.)
        previewContent.innerHTML = this.escapeHtml(contentInput.value).replace(/\n/g, '<br>');
        this.commentPreview.style.display = 'block';
        this.commentPreview.scrollIntoView({ behavior: 'smooth' });
    }
    
    hideCommentPreview() {
        this.commentPreview.style.display = 'none';
    }
    
    toggleReplyForm(commentId) {
        const replyForm = document.getElementById(`reply-form-${commentId}`);
        if (!replyForm) return;
        
        // Hide all other reply forms
        document.querySelectorAll('.reply-form-container').forEach(form => {
            if (form.id !== `reply-form-${commentId}`) {
                form.style.display = 'none';
            }
        });
        
        // Toggle current reply form
        replyForm.style.display = replyForm.style.display === 'none' ? 'block' : 'none';
        
        if (replyForm.style.display === 'block') {
            // Focus on the first input
            const firstInput = replyForm.querySelector('input[type="text"]');
            if (firstInput) firstInput.focus();
        }
    }
    
    async submitReply(form) {
        const submitBtn = form.querySelector('.reply-submit-btn');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Posting...';
        
        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken')
                }
            });
            
            if (response.ok) {
                this.showNotification('Reply submitted successfully!', 'success');
                form.reset();
                form.parentElement.style.display = 'none';
            } else {
                throw new Error('Failed to submit reply');
            }
        } catch (error) {
            console.error('Reply submission error:', error);
            this.showNotification('Failed to submit reply. Please try again.', 'error');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }
    
    sortComments(sortBy) {
        const commentsList = document.querySelector('.comments-list');
        if (!commentsList) return;
        
        const comments = Array.from(commentsList.querySelectorAll('.comment'));
        
        comments.sort((a, b) => {
            const dateA = new Date(a.querySelector('.comment-date').textContent.trim());
            const dateB = new Date(b.querySelector('.comment-date').textContent.trim());
            
            return sortBy === 'newest' ? dateB - dateA : dateA - dateB;
        });
        
        // Re-append sorted comments
        comments.forEach(comment => commentsList.appendChild(comment));
        
        this.showNotification(`Comments sorted by ${sortBy}`, 'info');
    }
    
    // Bookmark system methods
    getPostSlug() {
        return window.location.pathname.split('/').filter(Boolean).pop();
    }
    
    getSavedPosts() {
        return JSON.parse(localStorage.getItem('savedPosts') || '[]');
    }
    
    addBookmark(postSlug) {
        const savedPosts = this.getSavedPosts();
        if (!savedPosts.includes(postSlug)) {
            savedPosts.push(postSlug);
            localStorage.setItem('savedPosts', JSON.stringify(savedPosts));
        }
    }
    
    removeBookmark(postSlug) {
        const savedPosts = this.getSavedPosts();
        const index = savedPosts.indexOf(postSlug);
        if (index > -1) {
            savedPosts.splice(index, 1);
            localStorage.setItem('savedPosts', JSON.stringify(savedPosts));
        }
    }
    
    updateBookmarkButton(isBookmarked) {
        if (!this.bookmarkBtn) return;
        
        const icon = this.bookmarkBtn.querySelector('i');
        const text = this.bookmarkBtn.querySelector('span');
        
        if (isBookmarked) {
            icon.className = 'fas fa-bookmark';
            if (text) text.textContent = 'Saved';
            this.bookmarkBtn.classList.add('bookmarked');
        } else {
            icon.className = 'far fa-bookmark';
            if (text) text.textContent = 'Save';
            this.bookmarkBtn.classList.remove('bookmarked');
        }
    }
    
    // Utility methods
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    copyToClipboard(text) {
        if (navigator.clipboard) {
            return navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            return Promise.resolve();
        }
    }
    
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showNotification(message, type = 'info') {
        // Remove existing notification if any
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;

        // Add notification to page
        document.body.appendChild(notification);

        // Trigger animation
        setTimeout(() => notification.classList.add('show'), 100);

        // Remove notification after 4 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 4000);
    }
    
    getNotificationIcon(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'error': return 'exclamation-circle';
            case 'warning': return 'exclamation-triangle';
            default: return 'info-circle';
        }
    }
}

// Enhanced carousel functionality for featured posts
class FeaturedPostsCarousel {
    constructor() {
        this.carousel = document.getElementById('featuredCarousel');
        this.track = document.getElementById('carouselTrack');
        this.prevBtn = document.getElementById('carouselPrev');
        this.nextBtn = document.getElementById('carouselNext');
        this.indicators = document.querySelectorAll('.carousel-indicator');
        
        this.currentSlide = 0;
        this.totalSlides = this.indicators.length;
        this.autoPlayInterval = null;
        
        if (this.carousel && this.totalSlides > 1) {
            this.init();
        }
    }
    
    init() {
        this.setupControls();
        this.setupIndicators();
        this.setupAutoPlay();
        this.setupTouchGestures();
        this.setupKeyboardNavigation();
        
        console.log('Featured Posts Carousel initialized with', this.totalSlides, 'slides');
    }
    
    setupControls() {
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => this.previousSlide());
        }
        
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.nextSlide());
        }
    }
    
    setupIndicators() {
        this.indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => this.goToSlide(index));
        });
    }
    
    setupAutoPlay() {
        // Auto-play every 5 seconds
        this.startAutoPlay();
        
        // Pause on hover
        if (this.carousel) {
            this.carousel.addEventListener('mouseenter', () => this.stopAutoPlay());
            this.carousel.addEventListener('mouseleave', () => this.startAutoPlay());
        }
    }
    
    setupTouchGestures() {
        if (!this.carousel) return;
        
        let startX = 0;
        let currentX = 0;
        let isDragging = false;
        
        this.carousel.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            isDragging = true;
            this.stopAutoPlay();
        });
        
        this.carousel.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            currentX = e.touches[0].clientX;
        });
        
        this.carousel.addEventListener('touchend', () => {
            if (!isDragging) return;
            
            const diffX = startX - currentX;
            const threshold = 50;
            
            if (Math.abs(diffX) > threshold) {
                if (diffX > 0) {
                    this.nextSlide();
                } else {
                    this.previousSlide();
                }
            }
            
            isDragging = false;
            this.startAutoPlay();
        });
    }
    
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (!this.carousel || document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') {
                return;
            }
            
            switch (e.key) {
                case 'ArrowLeft':
                    e.preventDefault();
                    this.previousSlide();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.nextSlide();
                    break;
            }
        });
    }
    
    goToSlide(index) {
        if (index < 0 || index >= this.totalSlides) return;
        
        this.currentSlide = index;
        this.updateCarousel();
        this.updateIndicators();
    }
    
    nextSlide() {
        this.currentSlide = (this.currentSlide + 1) % this.totalSlides;
        this.updateCarousel();
        this.updateIndicators();
    }
    
    previousSlide() {
        this.currentSlide = (this.currentSlide - 1 + this.totalSlides) % this.totalSlides;
        this.updateCarousel();
        this.updateIndicators();
    }
    
    updateCarousel() {
        if (this.track) {
            const translateX = -this.currentSlide * 100;
            this.track.style.transform = `translateX(${translateX}%)`;
        }
    }
    
    updateIndicators() {
        this.indicators.forEach((indicator, index) => {
            indicator.classList.toggle('active', index === this.currentSlide);
        });
    }
    
    startAutoPlay() {
        this.stopAutoPlay();
        this.autoPlayInterval = setInterval(() => {
            this.nextSlide();
        }, 5000);
    }
    
    stopAutoPlay() {
        if (this.autoPlayInterval) {
            clearInterval(this.autoPlayInterval);
            this.autoPlayInterval = null;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize blog detail manager
    window.blogDetailManager = new BlogDetailManager();
    
    // Initialize featured posts carousel
    window.featuredPostsCarousel = new FeaturedPostsCarousel();
    
    // Global reply form toggle function for template use
    window.toggleReplyForm = (commentId) => {
        if (window.blogDetailManager) {
            window.blogDetailManager.toggleReplyForm(commentId);
        }
    };
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { BlogDetailManager, FeaturedPostsCarousel };
}