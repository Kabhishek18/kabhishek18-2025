/**
 * Multimedia Enhancement JavaScript
 * Handles image galleries, lightbox functionality, and video embeds
 */

class MultimediaManager {
    constructor() {
        this.lightbox = null;
        this.currentImageIndex = 0;
        this.images = [];
        
        this.init();
    }
    
    init() {
        this.setupImageGalleries();
        this.setupLightbox();
        this.setupVideoEmbeds();
        this.setupLazyLoading();
        
        console.log('Multimedia Manager initialized');
    }
    
    setupImageGalleries() {
        // Find all images in article content
        const articleImages = document.querySelectorAll('.article-content img');
        
        articleImages.forEach((img, index) => {
            // Add click handler for lightbox
            img.addEventListener('click', () => {
                this.openLightbox(index);
            });
            
            // Add hover effects
            img.addEventListener('mouseenter', () => {
                img.style.transform = 'scale(1.02)';
                img.style.cursor = 'pointer';
            });
            
            img.addEventListener('mouseleave', () => {
                img.style.transform = 'scale(1)';
            });
            
            // Store image data
            this.images.push({
                src: img.src,
                alt: img.alt || '',
                caption: img.getAttribute('data-caption') || img.alt || ''
            });
        });
    }
    
    setupLightbox() {
        // Create lightbox HTML
        const lightboxHTML = `
            <div class="lightbox-overlay" id="lightboxOverlay">
                <div class="lightbox-container">
                    <button class="lightbox-close" id="lightboxClose">
                        <i class="fas fa-times"></i>
                    </button>
                    <button class="lightbox-prev" id="lightboxPrev">
                        <i class="fas fa-chevron-left"></i>
                    </button>
                    <button class="lightbox-next" id="lightboxNext">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                    <div class="lightbox-content">
                        <img class="lightbox-image" id="lightboxImage" src="" alt="">
                        <div class="lightbox-caption" id="lightboxCaption"></div>
                        <div class="lightbox-counter" id="lightboxCounter"></div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', lightboxHTML);
        
        this.lightbox = document.getElementById('lightboxOverlay');
        this.setupLightboxControls();
    }
    
    setupLightboxControls() {
        const closeBtn = document.getElementById('lightboxClose');
        const prevBtn = document.getElementById('lightboxPrev');
        const nextBtn = document.getElementById('lightboxNext');
        
        // Close lightbox
        closeBtn.addEventListener('click', () => this.closeLightbox());
        this.lightbox.addEventListener('click', (e) => {
            if (e.target === this.lightbox) {
                this.closeLightbox();
            }
        });
        
        // Navigation
        prevBtn.addEventListener('click', () => this.previousImage());
        nextBtn.addEventListener('click', () => this.nextImage());
        
        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (!this.lightbox.classList.contains('active')) return;
            
            switch (e.key) {
                case 'Escape':
                    this.closeLightbox();
                    break;
                case 'ArrowLeft':
                    this.previousImage();
                    break;
                case 'ArrowRight':
                    this.nextImage();
                    break;
            }
        });
        
        // Touch gestures
        this.setupTouchGestures();
    }
    
    setupTouchGestures() {
        let startX = 0;
        let startY = 0;
        let currentX = 0;
        let currentY = 0;
        let isDragging = false;
        
        const lightboxContent = document.querySelector('.lightbox-content');
        
        lightboxContent.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isDragging = true;
        });
        
        lightboxContent.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            
            currentX = e.touches[0].clientX;
            currentY = e.touches[0].clientY;
            
            // Prevent default scrolling
            e.preventDefault();
        });
        
        lightboxContent.addEventListener('touchend', () => {
            if (!isDragging) return;
            
            const diffX = startX - currentX;
            const diffY = startY - currentY;
            const threshold = 50;
            
            // Horizontal swipe
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > threshold) {
                if (diffX > 0) {
                    this.nextImage();
                } else {
                    this.previousImage();
                }
            }
            // Vertical swipe down to close
            else if (diffY < -threshold) {
                this.closeLightbox();
            }
            
            isDragging = false;
        });
    }
    
    openLightbox(index) {
        if (this.images.length === 0) return;
        
        this.currentImageIndex = index;
        this.updateLightboxContent();
        this.lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Preload adjacent images
        this.preloadAdjacentImages();
    }
    
    closeLightbox() {
        this.lightbox.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    nextImage() {
        this.currentImageIndex = (this.currentImageIndex + 1) % this.images.length;
        this.updateLightboxContent();
        this.preloadAdjacentImages();
    }
    
    previousImage() {
        this.currentImageIndex = (this.currentImageIndex - 1 + this.images.length) % this.images.length;
        this.updateLightboxContent();
        this.preloadAdjacentImages();
    }
    
    updateLightboxContent() {
        const image = document.getElementById('lightboxImage');
        const caption = document.getElementById('lightboxCaption');
        const counter = document.getElementById('lightboxCounter');
        
        const currentImage = this.images[this.currentImageIndex];
        
        image.src = currentImage.src;
        image.alt = currentImage.alt;
        caption.textContent = currentImage.caption;
        counter.textContent = `${this.currentImageIndex + 1} / ${this.images.length}`;
        
        // Show/hide navigation buttons
        const prevBtn = document.getElementById('lightboxPrev');
        const nextBtn = document.getElementById('lightboxNext');
        
        prevBtn.style.display = this.images.length > 1 ? 'block' : 'none';
        nextBtn.style.display = this.images.length > 1 ? 'block' : 'none';
    }
    
    preloadAdjacentImages() {
        // Preload next and previous images for smooth navigation
        const nextIndex = (this.currentImageIndex + 1) % this.images.length;
        const prevIndex = (this.currentImageIndex - 1 + this.images.length) % this.images.length;
        
        [nextIndex, prevIndex].forEach(index => {
            if (index !== this.currentImageIndex) {
                const img = new Image();
                img.src = this.images[index].src;
            }
        });
    }
    
    setupVideoEmbeds() {
        // Find all video links and convert to embeds
        const videoLinks = document.querySelectorAll('a[href*="youtube.com"], a[href*="youtu.be"], a[href*="vimeo.com"]');
        
        videoLinks.forEach(link => {
            const videoId = this.extractVideoId(link.href);
            const platform = this.getVideoPlatform(link.href);
            
            if (videoId && platform) {
                const embedContainer = this.createVideoEmbed(videoId, platform);
                link.parentNode.replaceChild(embedContainer, link);
            }
        });
    }
    
    extractVideoId(url) {
        // YouTube
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
            const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
            const match = url.match(regex);
            return match ? match[1] : null;
        }
        
        // Vimeo
        if (url.includes('vimeo.com')) {
            const regex = /vimeo\.com\/(\d+)/;
            const match = url.match(regex);
            return match ? match[1] : null;
        }
        
        return null;
    }
    
    getVideoPlatform(url) {
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
            return 'youtube';
        }
        if (url.includes('vimeo.com')) {
            return 'vimeo';
        }
        return null;
    }
    
    createVideoEmbed(videoId, platform) {
        const container = document.createElement('div');
        container.className = 'video-embed-container';
        
        let embedUrl = '';
        if (platform === 'youtube') {
            embedUrl = `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`;
        } else if (platform === 'vimeo') {
            embedUrl = `https://player.vimeo.com/video/${videoId}`;
        }
        
        container.innerHTML = `
            <div class="video-embed-wrapper">
                <iframe 
                    src="${embedUrl}" 
                    frameborder="0" 
                    allowfullscreen
                    loading="lazy">
                </iframe>
                <div class="video-overlay" data-video-id="${videoId}" data-platform="${platform}">
                    <button class="video-play-btn">
                        <i class="fas fa-play"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Add click handler for play button
        const playBtn = container.querySelector('.video-play-btn');
        const overlay = container.querySelector('.video-overlay');
        const iframe = container.querySelector('iframe');
        
        playBtn.addEventListener('click', () => {
            overlay.style.display = 'none';
            iframe.src += '&autoplay=1';
        });
        
        return container;
    }
    
    setupLazyLoading() {
        // Implement intersection observer for lazy loading
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            img.classList.remove('lazy');
                            observer.unobserve(img);
                        }
                    }
                });
            });
            
            // Observe all lazy images
            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.multimediaManager = new MultimediaManager();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MultimediaManager;
}