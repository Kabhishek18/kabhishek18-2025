// Portfolio Data from your context
const portfolioData = {
    profile: {
        name: "Kumar Abhishek",
        username: "kabhishek18",
        title: "Full Stack Software Developer",
        subtitle: "Rich experience in Web & Mobile Application Development",
        email: "developer@kabhishek18.com",
        github: "https://github.com/kabhishek18",
        linkedin: "https://linkedin.com/in/kabhishek18",
        twitter: "https://twitter.com/kabhishek18",
        freelancer: "https://www.freelancer.com/u/kabhishek18",
        orcid: "https://orcid.org/0009-0006-6321-2424",
        website: "https://kabhishek18.com",
        bio: "I'm an experienced Full Stack Software Developer with over 9 years of experience in Python, PHP, and ReactJS.",
        location: "India",
        experience: "9+ Years",
        pypiPackages: "4",
        totalProjects: "50+",
        publicRepos: "35+",
        technologies: "20+"
    }
};

// Enhanced Loader System
class EnhancedLoader {
    constructor() {
        this.messages = [
            'Initializing neural pathways...',
            'Loading AI consciousness modules...',
            'Establishing quantum entanglement...',
            'Calibrating creativity engines...',
            'Synchronizing digital architecture...',
            'Compiling innovative solutions...',
            'Optimizing user experience...',
            'Finalizing system protocols...',
            'System ready. Welcome to the future.'
        ];
        this.currentMessageIndex = 0;
        this.progress = 0;
        this.isFirstLoad = !sessionStorage.getItem('visitedBefore');
    }

    show() {
        if (!this.isFirstLoad) return Promise.resolve();

        return new Promise((resolve) => {
            this.createLoader();
            this.animateMessages(() => {
                this.hideLoader(resolve);
                sessionStorage.setItem('visitedBefore', 'true');
            });
        });
    }

    createLoader() {
        const loader = document.createElement('div');
        loader.id = 'enhancedLoader';
        loader.className = 'enhanced-loader';
        loader.innerHTML = `
            <div class="loader-content">
                <div class="loader-logo">
                    <div class="logo-ring"></div>
                    <div class="logo-ring ring-2"></div>
                    <div class="logo-ring ring-3"></div>
                    <div class="logo-text">KA</div>
                </div>
                <div class="loader-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                        <div class="progress-glow"></div>
                    </div>
                    <div class="progress-percentage" id="progressPercentage">0%</div>
                </div>
                <div class="loader-message" id="loaderMessage">
                    <div class="message-text"></div>
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
                <div class="loader-particles" id="loaderParticles"></div>
            </div>
        `;

        document.body.appendChild(loader);
        this.addLoaderStyles();
        this.createParticles();
    }

    addLoaderStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .enhanced-loader {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 30000;
                font-family: 'JetBrains Mono', monospace;
                overflow: hidden;
            }

            .loader-content {
                text-align: center;
                position: relative;
                z-index: 2;
            }

            .loader-logo {
                position: relative;
                width: 120px;
                height: 120px;
                margin: 0 auto 3rem;
            }

            .logo-ring {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                border: 2px solid rgba(0, 217, 255, 0.3);
                border-radius: 50%;
                animation: logoSpin 3s linear infinite;
            }

            .logo-ring:nth-child(1) {
                width: 120px;
                height: 120px;
                border-top-color: #00d9ff;
                animation-duration: 3s;
            }

            .logo-ring:nth-child(2) {
                width: 90px;
                height: 90px;
                border-right-color: #a855f7;
                animation-duration: 2s;
                animation-direction: reverse;
            }

            .logo-ring:nth-child(3) {
                width: 60px;
                height: 60px;
                border-bottom-color: #00ff88;
                animation-duration: 1.5s;
            }

            .logo-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-family: 'Orbitron', monospace;
                font-size: 2rem;
                font-weight: 700;
                color: #00d9ff;
                text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
                animation: textPulse 2s ease-in-out infinite;
            }

            @keyframes logoSpin {
                0% { transform: translate(-50%, -50%) rotate(0deg); }
                100% { transform: translate(-50%, -50%) rotate(360deg); }
            }

            @keyframes textPulse {
                0%, 100% { opacity: 0.8; transform: translate(-50%, -50%) scale(1); }
                50% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
            }

            .loader-progress {
                margin-bottom: 2rem;
                width: 300px;
                margin-left: auto;
                margin-right: auto;
            }

            .progress-bar {
                width: 100%;
                height: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                overflow: hidden;
                position: relative;
                margin-bottom: 1rem;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #00d9ff, #a855f7, #00ff88);
                border-radius: 10px;
                width: 0%;
                transition: width 0.3s ease;
                position: relative;
            }

            .progress-glow {
                position: absolute;
                top: -3px;
                left: 0;
                right: 0;
                bottom: -3px;
                background: #00d9ff;
                border-radius: 10px;
                opacity: 0.4;
                filter: blur(8px);
                animation: progressGlow 2s ease-in-out infinite alternate;
            }

            @keyframes progressGlow {
                0% { opacity: 0.2; }
                100% { opacity: 0.6; }
            }

            .progress-percentage {
                text-align: center;
                color: #00d9ff;
                font-weight: 600;
                font-size: 1.2rem;
                font-family: 'Orbitron', monospace;
            }

            .loader-message {
                min-height: 60px;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 1rem;
            }

            .message-text {
                color: #e5e5e5;
                font-size: 1.1rem;
                text-align: center;
                opacity: 0;
                transform: translateY(20px);
                animation: messageSlideIn 0.5s ease forwards;
            }

            @keyframes messageSlideIn {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            .typing-dots {
                display: flex;
                gap: 0.5rem;
                justify-content: center;
            }

            .typing-dots span {
                width: 8px;
                height: 8px;
                background: #00d9ff;
                border-radius: 50%;
                animation: typingDots 1.5s infinite;
            }

            .typing-dots span:nth-child(2) {
                animation-delay: 0.2s;
            }

            .typing-dots span:nth-child(3) {
                animation-delay: 0.4s;
            }

            @keyframes typingDots {
                0%, 60%, 100% {
                    transform: translateY(0);
                    opacity: 0.4;
                }
                30% {
                    transform: translateY(-15px);
                    opacity: 1;
                }
            }

            .loader-particles {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
                z-index: 1;
            }

            .loader-particle {
                position: absolute;
                width: 3px;
                height: 3px;
                background: #00d9ff;
                border-radius: 50%;
                animation: particleFloat 6s infinite linear;
                opacity: 0.7;
            }

            @keyframes particleFloat {
                0% {
                    transform: translateY(100vh) rotate(0deg);
                    opacity: 0;
                }
                10% {
                    opacity: 0.7;
                }
                90% {
                    opacity: 0.7;
                }
                100% {
                    transform: translateY(-100px) rotate(360deg);
                    opacity: 0;
                }
            }

            .loader-exit {
                animation: loaderFadeOut 1s ease forwards;
            }

            @keyframes loaderFadeOut {
                0% {
                    opacity: 1;
                    transform: scale(1);
                }
                100% {
                    opacity: 0;
                    transform: scale(1.1);
                }
            }

            @media (max-width: 768px) {
                .loader-progress {
                    width: 250px;
                }
                
                .message-text {
                    font-size: 1rem;
                    padding: 0 1rem;
                }
                
                .loader-logo {
                    width: 100px;
                    height: 100px;
                }
                
                .logo-ring:nth-child(1) {
                    width: 100px;
                    height: 100px;
                }
                
                .logo-ring:nth-child(2) {
                    width: 75px;
                    height: 75px;
                }
                
                .logo-ring:nth-child(3) {
                    width: 50px;
                    height: 50px;
                }
                
                .logo-text {
                    font-size: 1.5rem;
                }
            }
        `;
        document.head.appendChild(style);
    }

    createParticles() {
        const container = document.getElementById('loaderParticles');
        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                const particle = document.createElement('div');
                particle.className = 'loader-particle';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.animationDelay = Math.random() * 3 + 's';
                particle.style.animationDuration = (4 + Math.random() * 4) + 's';
                container.appendChild(particle);
            }, i * 200);
        }
    }

    animateMessages(callback) {
        const messageEl = document.querySelector('.message-text');
        const progressFill = document.getElementById('progressFill');
        const progressPercentage = document.getElementById('progressPercentage');
        
        const showMessage = () => {
            if (this.currentMessageIndex < this.messages.length) {
                messageEl.textContent = this.messages[this.currentMessageIndex];
                messageEl.style.animation = 'none';
                messageEl.offsetHeight; // Trigger reflow
                messageEl.style.animation = 'messageSlideIn 0.5s ease forwards';
                
                // Update progress
                this.progress = ((this.currentMessageIndex + 1) / this.messages.length) * 100;
                progressFill.style.width = this.progress + '%';
                progressPercentage.textContent = Math.round(this.progress) + '%';
                
                this.currentMessageIndex++;
                
                const delay = this.currentMessageIndex === this.messages.length ? 1500 : 1800;
                setTimeout(showMessage, delay);
            } else {
                callback();
            }
        };
        
        showMessage();
    }

    hideLoader(callback) {
        const loader = document.getElementById('enhancedLoader');
        loader.classList.add('loader-exit');
        
        setTimeout(() => {
            if (loader && loader.parentNode) {
                loader.parentNode.removeChild(loader);
            }
            callback();
        }, 1000);
    }
}

// Matrix Rain Effect - Fixed version
class MatrixRain {
    constructor() {
        this.canvas = document.getElementById('matrix');
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
        this.charArray = this.chars.split('');
        this.drops = [];
        this.fontSize = 14;
        this.animationId = null;
        
        this.init();
        this.animate();
    }
    
    init() {
        if (!this.canvas) return;
        
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        
        const columns = Math.floor(this.canvas.width / this.fontSize);
        this.drops = [];
        for(let i = 0; i < columns; i++) {
            this.drops[i] = 1;
        }
    }
    
    animate() {
        if (!this.ctx) return;
        
        this.ctx.fillStyle = 'rgba(10, 10, 10, 0.05)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.ctx.fillStyle = '#00ff00';
        this.ctx.font = this.fontSize + 'px monospace';
        
        for(let i = 0; i < this.drops.length; i++) {
            const text = this.charArray[Math.floor(Math.random() * this.charArray.length)];
            this.ctx.fillText(text, i * this.fontSize, this.drops[i] * this.fontSize);
            
            if(this.drops[i] * this.fontSize > this.canvas.height && Math.random() > 0.975) {
                this.drops[i] = 0;
            }
            this.drops[i]++;
        }
        
        this.animationId = requestAnimationFrame(() => this.animate());
    }
    
    resize() {
        this.init();
    }
    
    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}

// Neural Network Animation - Fixed version
class NeuralNetwork {
    constructor() {
        this.container = document.getElementById('neuralNetwork');
        if (!this.container) return;
        
        this.nodes = [];
        this.connections = [];
        this.init();
    }
    
    init() {
        this.createNodes();
        this.createConnections();
        this.animate();
    }
    
    createNodes() {
        if (!this.container) return;
        
        const nodeCount = Math.min(20, Math.floor(window.innerWidth / 100));
        for(let i = 0; i < nodeCount; i++) {
            const node = document.createElement('div');
            node.className = 'neural-node';
            node.style.cssText = `
                position: absolute;
                width: 4px;
                height: 4px;
                background: #00ffff;
                border-radius: 50%;
                left: ${Math.random() * 100}%;
                top: ${Math.random() * 100}%;
                box-shadow: 0 0 6px #00ffff;
                animation: neuralPulse ${2 + Math.random() * 3}s ease-in-out infinite;
                pointer-events: none;
            `;
            this.container.appendChild(node);
            this.nodes.push(node);
        }
    }
    
    createConnections() {
        // Add CSS for neural connections
        if (!document.getElementById('neural-styles')) {
            const style = document.createElement('style');
            style.id = 'neural-styles';
            style.textContent = `
                @keyframes neuralPulse {
                    0%, 100% { opacity: 0.3; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.5); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    animate() {
        setInterval(() => {
            this.nodes.forEach(node => {
                if(Math.random() > 0.98) {
                    node.style.left = Math.random() * 100 + '%';
                    node.style.top = Math.random() * 100 + '%';
                }
            });
        }, 5000);
    }
}

// Data Particles System - Fixed version
class DataParticles {
    constructor() {
        this.container = document.getElementById('dataParticles');
        if (!this.container) return;
        
        this.particleCount = window.innerWidth < 768 ? 8 : 15;
        this.init();
    }
    
    init() {
        this.createParticles();
    }
    
    createParticles() {
        for(let i = 0; i < this.particleCount; i++) {
            setTimeout(() => {
                this.createParticle();
            }, i * 2000);
        }
        
        setInterval(() => {
            this.createParticle();
        }, 3000);
    }
    
    createParticle() {
        if (!this.container) return;
        
        const particle = document.createElement('div');
        particle.className = 'data-particle';
        particle.style.cssText = `
            left: ${Math.random() * 100}%;
            animation-duration: ${8 + Math.random() * 4}s;
            animation-delay: ${Math.random() * 2}s;
        `;
        
        this.container.appendChild(particle);
        
        setTimeout(() => {
            if(particle && particle.parentNode) {
                particle.parentNode.removeChild(particle);
            }
        }, 12000);
    }
}

// Typewriter Effect - Fixed version
class TypewriterEffect {
    constructor(element, texts, speed = 100) {
        this.element = element;
        this.texts = texts;
        this.speed = speed;
        this.currentTextIndex = 0;
        this.currentCharIndex = 0;
        this.isDeleting = false;
        this.timeoutId = null;
        
        if (this.element) {
            this.init();
        }
    }
    
    init() {
        this.type();
    }
    
    type() {
        if (!this.element) return;
        
        const currentText = this.texts[this.currentTextIndex];
        
        if (this.isDeleting) {
            this.element.textContent = currentText.substring(0, this.currentCharIndex - 1);
            this.currentCharIndex--;
        } else {
            this.element.textContent = currentText.substring(0, this.currentCharIndex + 1);
            this.currentCharIndex++;
        }
        
        let typeSpeed = this.speed;
        
        if (this.isDeleting) {
            typeSpeed /= 2;
        }
        
        if (!this.isDeleting && this.currentCharIndex === currentText.length) {
            typeSpeed = 2000;
            this.isDeleting = true;
        } else if (this.isDeleting && this.currentCharIndex === 0) {
            this.isDeleting = false;
            this.currentTextIndex = (this.currentTextIndex + 1) % this.texts.length;
            typeSpeed = 500;
        }
        
        this.timeoutId = setTimeout(() => this.type(), typeSpeed);
    }
    
    destroy() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
        }
    }
}

// Glitch Text Effect - Fixed version
class GlitchText {
    constructor(element) {
        this.element = element;
        if (!this.element) return;
        
        this.originalText = element.textContent;
        this.chars = '!<>-_\\/[]{}—=+*^?#________';
        this.intervalId = null;
        this.init();
    }
    
    init() {
        this.intervalId = setInterval(() => {
            this.glitch();
        }, 4000 + Math.random() * 3000);
    }
    
    glitch() {
        if (!this.element) return;
        
        const iterations = 10;
        let iteration = 0;
        
        const glitchInterval = setInterval(() => {
            this.element.textContent = this.originalText
                .split('')
                .map((char, index) => {
                    if (index < iteration) {
                        return this.originalText[index];
                    }
                    return this.chars[Math.floor(Math.random() * this.chars.length)];
                })
                .join('');
            
            if (iteration >= this.originalText.length) {
                clearInterval(glitchInterval);
                this.element.textContent = this.originalText;
            }
            
            iteration += 1 / 3;
        }, 30);
    }
    
    destroy() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
}

// Progress Animation - Fixed version
class ProgressAnimation {
    constructor() {
        this.progressFill = document.querySelector('.progress-fill');
        this.progressPercentage = document.querySelector('.progress-percentage');
        this.observer = null;
        
        if (this.progressFill) {
            this.init();
        }
    }
    
    init() {
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateProgress();
                    this.observer.unobserve(entry.target);
                }
            });
        });
        
        this.observer.observe(this.progressFill);
    }
    
    animateProgress() {
        const targetPercentage = 87;
        let currentPercentage = 0;
        const duration = 3000;
        const stepTime = 50;
        const steps = duration / stepTime;
        const increment = targetPercentage / steps;
        
        const progressInterval = setInterval(() => {
            currentPercentage += increment;
            
            if (currentPercentage >= targetPercentage) {
                currentPercentage = targetPercentage;
                clearInterval(progressInterval);
            }
            
            if (this.progressFill) {
                this.progressFill.style.width = currentPercentage + '%';
            }
            if (this.progressPercentage) {
                this.progressPercentage.textContent = Math.floor(currentPercentage) + '%';
            }
        }, stepTime);
    }
    
    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }
    }
}

// Enhanced Particle System for Interactions - Fixed version
class InteractiveParticles {
    constructor() {
        this.particles = [];
        this.maxParticles = window.innerWidth < 768 ? 3 : 5;
        this.init();
    }
    
    init() {
        document.addEventListener('mousemove', (e) => {
            if (Math.random() > 0.95 && this.particles.length < this.maxParticles) {
                this.createParticle(e.clientX, e.clientY);
            }
        });
        
        document.addEventListener('click', (e) => {
            for(let i = 0; i < 3; i++) {
                setTimeout(() => {
                    this.createParticle(
                        e.clientX + (Math.random() - 0.5) * 20,
                        e.clientY + (Math.random() - 0.5) * 20
                    );
                }, i * 100);
            }
        });
    }
    
    createParticle(x, y) {
        const particle = document.createElement('div');
        const size = Math.random() * 4 + 2;
        const colors = ['#00ffff', '#8a2be2', '#ff6600', '#00ff00'];
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        particle.style.cssText = `
            position: fixed;
            left: ${x}px;
            top: ${y}px;
            width: ${size}px;
            height: ${size}px;
            background: ${color};
            border-radius: 50%;
            pointer-events: none;
            z-index: 1000;
            box-shadow: 0 0 ${size * 2}px ${color};
        `;
        
        document.body.appendChild(particle);
        this.particles.push(particle);
        
        // Animate particle
        const angle = Math.random() * Math.PI * 2;
        const velocity = Math.random() * 100 + 50;
        const lifetime = 2000 + Math.random() * 1000;
        
        const animation = particle.animate([
            {
                transform: 'translate(0, 0) scale(1)',
                opacity: 1
            },
            {
                transform: `translate(${Math.cos(angle) * velocity}px, ${Math.sin(angle) * velocity}px) scale(0)`,
                opacity: 0
            }
        ], {
            duration: lifetime,
            easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
        });
        
        animation.onfinish = () => {
            if (particle && particle.parentNode) {
                particle.parentNode.removeChild(particle);
            }
            this.particles = this.particles.filter(p => p !== particle);
        };
    }
}

// App initialization with error handling
class App {
    constructor() {
        this.components = [];
        this.loader = new EnhancedLoader();
    }

    async init() {
        try {
            // Show loader first
            await this.loader.show();
            
            // Initialize all components
            this.initializeComponents();
            this.addEventListeners();
            this.addConsoleCommands();
            
            console.log('%c🤖 SYSTEM INITIALIZED', 'color: #00ffff; font-size: 16px; font-weight: bold;');
            console.log('%cWelcome to the digital consciousness of Kumar Abhishek', 'color: #8a2be2; font-size: 12px;');
            console.log('%cType "help()" for available commands', 'color: #00ff00; font-size: 10px;');
            
        } catch (error) {
            console.error('Error initializing app:', error);
        }
    }

    initializeComponents() {
        try {
            // Initialize Matrix Rain
            const matrixRain = new MatrixRain();
            this.components.push(matrixRain);
            
            // Initialize Neural Network
            const neuralNetwork = new NeuralNetwork();
            this.components.push(neuralNetwork);
            
            // Initialize Data Particles
            const dataParticles = new DataParticles();
            this.components.push(dataParticles);
            
            // Initialize Typewriter Effect
            const typewriterTexts = [
                'Crafting digital experiences...',
                'Building AI-powered solutions...',
                'Architecting the future...',
                'Coding neural pathways...',
                'Designing intelligent systems...'
            ];
            
            const typewriterElement = document.getElementById('typewriter');
            if (typewriterElement) {
                const typewriter = new TypewriterEffect(typewriterElement, typewriterTexts, 80);
                this.components.push(typewriter);
            }
            
            // Initialize Glitch Text
            const glitchElements = document.querySelectorAll('.digital-glitch');
            glitchElements.forEach(element => {
                const glitch = new GlitchText(element);
                this.components.push(glitch);
            });
            
            // Initialize Progress Animation
            const progress = new ProgressAnimation();
            this.components.push(progress);
            
            // Initialize Interactive Particles
            const interactiveParticles = new InteractiveParticles();
            this.components.push(interactiveParticles);
            
            // Performance optimization - reduce effects on mobile
            this.optimizeForMobile();
            
        } catch (error) {
            console.error('Error initializing components:', error);
        }
    }

    optimizeForMobile() {
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            // Reduce matrix rain opacity
            const matrixCanvas = document.getElementById('matrix');
            if (matrixCanvas) {
                matrixCanvas.style.opacity = '0.03';
            }
            
            // Reduce neural network nodes
            const neuralNodes = document.querySelectorAll('.neural-node');
            neuralNodes.forEach((node, index) => {
                if (index % 2 === 0) {
                    node.remove();
                }
            });
        }
    }

    addEventListeners() {
        // Handle window resize
        window.addEventListener('resize', () => {
            this.components.forEach(component => {
                if (component && typeof component.resize === 'function') {
                    component.resize();
                }
            });
        });

        // Enhanced social link interactions
        this.initializeSocialLinks();
        
        // AI Status Panel Animation
        this.initializeStatusPanel();
        
        // Enhanced avatar interactions
        this.initializeAvatarInteractions();
        
        // Email terminal enhancement
        this.initializeEmailTerminal();
        
        // Stats animation on scroll
        this.initializeStatsAnimation();
        
        // Domain cards enhancement
        this.initializeDomainCards();
    }

    initializeSocialLinks() {
        const socialLinks = document.querySelectorAll('.social-link');
        socialLinks.forEach(link => {
            link.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-3px) scale(1.05)';
            });
            
            link.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
            
            link.addEventListener('click', function(e) {
                // Create ripple effect
                const ripple = document.createElement('div');
                ripple.style.cssText = `
                    position: absolute;
                    border-radius: 50%;
                    background: rgba(0, 255, 255, 0.3);
                    transform: scale(0);
                    animation: ripple 0.6s linear;
                    pointer-events: none;
                `;
                
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
                ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
                
                this.appendChild(ripple);
                
                setTimeout(() => {
                    if (ripple && ripple.parentNode) {
                        ripple.parentNode.removeChild(ripple);
                    }
                }, 600);
            });
        });
        
        // Add ripple animation CSS if not exists
        if (!document.getElementById('ripple-styles')) {
            const rippleStyle = document.createElement('style');
            rippleStyle.id = 'ripple-styles';
            rippleStyle.textContent = `
                @keyframes ripple {
                    to {
                        transform: scale(4);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(rippleStyle);
        }
    }

    initializeStatusPanel() {
        const statusItems = document.querySelectorAll('.status-item');
        statusItems.forEach((item, index) => {
            setInterval(() => {
                const value = item.querySelector('.status-value');
                if (!value) return;
                
                const originalText = value.textContent;
                
                // Simulate status checking
                value.textContent = 'CHECKING...';
                value.style.color = '#ff6600';
                
                setTimeout(() => {
                    value.textContent = originalText;
                    value.style.color = '#00ff00';
                }, 1000 + Math.random() * 2000);
            }, 10000 + index * 2000);
        });
    }

    initializeAvatarInteractions() {
        const avatar = document.querySelector('.avatar');
        if (avatar) {
            avatar.addEventListener('click', () => {
                const scanLines = [];
                for(let i = 0; i < 5; i++) {
                    const scanLine = document.createElement('div');
                    scanLine.style.cssText = `
                        position: absolute;
                        top: ${Math.random() * 100}%;
                        left: -100%;
                        width: 100%;
                        height: 1px;
                        background: #00ff00;
                        animation: quickScan 0.3s ease-out;
                        animation-delay: ${i * 0.1}s;
                        pointer-events: none;
                    `;
                    avatar.appendChild(scanLine);
                    scanLines.push(scanLine);
                }
                
                setTimeout(() => {
                    scanLines.forEach(line => {
                        if (line && line.parentNode) {
                            line.parentNode.removeChild(line);
                        }
                    });
                }, 2000);
            });
        }
        
        // Add quick scan animation CSS if not exists
        if (!document.getElementById('scan-styles')) {
            const quickScanStyle = document.createElement('style');
            quickScanStyle.id = 'scan-styles';
            quickScanStyle.textContent = `
                @keyframes quickScan {
                    0% { left: -100%; opacity: 0; }
                    50% { opacity: 1; }
                    100% { left: 100%; opacity: 0; }
                }
            `;
            document.head.appendChild(quickScanStyle);
        }
    }

    initializeEmailTerminal() {
        const emailLink = document.querySelector('.email-link');
        if (emailLink) {
            emailLink.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Simulate sending message
                const terminalBody = document.querySelector('.terminal-body');
                if (terminalBody) {
                    const newLine = document.createElement('div');
                    newLine.className = 'terminal-line';
                    newLine.innerHTML = `
                        <span class="prompt">>>> </span>
                        <span class="command">send_encrypted_message()</span>
                    `;
                    terminalBody.appendChild(newLine);
                    
                    setTimeout(() => {
                        const responseLine = document.createElement('div');
                        responseLine.className = 'terminal-line';
                        responseLine.innerHTML = `<span class="output">Message encrypted and sent via quantum channel...</span>`;
                        terminalBody.appendChild(responseLine);
                        
                        // Open email client after animation
                        setTimeout(() => {
                            window.location.href = 'mailto:developer@kabhishek18.com';
                        }, 1000);
                    }, 800);
                }
            });
        }
    }

    initializeStatsAnimation() {
        const statNumbers = document.querySelectorAll('.stat-number');
        if (statNumbers.length === 0) return;
        
        const statsObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateStatNumber(entry.target);
                    statsObserver.unobserve(entry.target);
                }
            });
        });
        
        statNumbers.forEach(stat => {
            statsObserver.observe(stat);
        });
    }

    animateStatNumber(element) {
        const finalText = element.textContent;
        const isInfinity = finalText === '∞';
        
        if (isInfinity) {
            element.style.animation = 'infinityPulse 2s ease-in-out infinite';
            return;
        }
        
        const hasPlus = finalText.includes('+');
        const number = parseInt(finalText.replace(/\D/g, '')) || 0;
        let current = 0;
        const increment = number / 50;
        const duration = 2000;
        const stepTime = duration / 50;
        
        element.textContent = '0' + (hasPlus ? '+' : '');
        
        const counter = setInterval(() => {
            current += increment;
            if (current >= number) {
                current = number;
                clearInterval(counter);
            }
            element.textContent = Math.floor(current) + (hasPlus ? '+' : '');
        }, stepTime);
    }

    initializeDomainCards() {
        const domainData = {
            'e-commerce': {
                projects: ['Django E-commerce Template', 'Payment Gateway Integration', 'Inventory Management'],
                technologies: ['Django', 'Python', 'PostgreSQL', 'Redis']
            },
            'aviation': {
                projects: ['Flight Booking System', 'Airport Management', 'Crew Scheduling'],
                technologies: ['React Native', 'Node.js', 'MongoDB', 'WebSocket']
            },
            'edtech': {
                projects: ['Learning Management System', 'Resume Builder', 'Online Assessment'],
                technologies: ['React', 'Django', 'Machine Learning', 'WebRTC']
            }
        };
        
        const domainCards = document.querySelectorAll('.domain-card');
        domainCards.forEach(card => {
            const domain = card.getAttribute('data-domain');
            
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-10px) scale(1.02)';
                card.style.boxShadow = '0 20px 40px rgba(0, 255, 255, 0.3)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
                card.style.boxShadow = 'none';
            });
            
            card.addEventListener('click', () => {
                if (domainData[domain]) {
                    this.showDomainDetails(card, domainData[domain]);
                }
            });
        });
    }

    showDomainDetails(card, data) {
        // Create modal overlay
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: #111111;
            border: 1px solid #00ffff;
            border-radius: 15px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            color: white;
            font-family: 'JetBrains Mono', monospace;
            max-height: 80vh;
            overflow-y: auto;
        `;
        
        const titleElement = card.querySelector('.domain-title');
        const title = titleElement ? titleElement.textContent : 'Domain Details';
        
        modalContent.innerHTML = `
            <h3 style="color: #00ffff; margin-bottom: 1rem; font-family: 'Orbitron', monospace;">
                ${title}
            </h3>
            <div style="margin-bottom: 1rem;">
                <strong>Key Projects:</strong>
                <ul style="margin-top: 0.5rem; padding-left: 1rem;">
                    ${data.projects.map(project => `<li style="margin-bottom: 0.3rem;">${project}</li>`).join('')}
                </ul>
            </div>
            <div style="margin-bottom: 1rem;">
                <strong>Technologies:</strong>
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
                    ${data.technologies.map(tech => `
                        <span style="background: rgba(0, 255, 255, 0.1); border: 1px solid #00ffff; padding: 0.2rem 0.5rem; border-radius: 5px; font-size: 0.8rem;">
                            ${tech}
                        </span>
                    `).join('')}
                </div>
            </div>
            <button class="modal-close-btn" style="background: #00ffff; color: #000; border: none; padding: 0.5rem 1rem; border-radius: 5px; cursor: pointer; font-family: inherit;">
                Close
            </button>
        `;
        
        modal.className = 'modal-overlay';
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Close button functionality
        const closeBtn = modalContent.querySelector('.modal-close-btn');
        closeBtn.addEventListener('click', () => {
            modal.remove();
        });
        
        // Animate in
        setTimeout(() => {
            modal.style.opacity = '1';
        }, 10);
        
        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        // Close on Escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
    }

    addConsoleCommands() {
        // Add console commands for fun
        window.help = function() {
            console.log(`
%cAvailable Commands:
%cprofile() - View developer profile
%cprojects() - List all projects  
%cskills() - Show technical skills
%ccontact() - Get contact information
%cmatrix() - Toggle matrix rain
%cai_mode() - Activate AI assistance mode
            `, 
            'color: #00ffff; font-weight: bold;',
            'color: #ffffff;', 'color: #ffffff;', 'color: #ffffff;', 
            'color: #ffffff;', 'color: #ffffff;', 'color: #ffffff;');
        };
        
        window.profile = function() {
            console.table(portfolioData.profile);
        };
        
        window.projects = function() {
            console.log('%cRecent Projects:', 'color: #00ffff; font-weight: bold;');
            console.log('%c- Django E-commerce Template', 'color: #8a2be2; font-weight: bold;');
            console.log('%c- Flight Booking System', 'color: #8a2be2; font-weight: bold;');
            console.log('%c- Learning Management System', 'color: #8a2be2; font-weight: bold;');
        };
        
        window.skills = function() {
            console.log('%cTechnical Skills:', 'color: #00ffff; font-weight: bold;');
            console.log('%cPython • PHP • JavaScript • React • Django • FastAPI', 'color: #00ff00;');
        };
        
        window.contact = function() {
            console.log('%cContact Information:', 'color: #00ffff; font-weight: bold;');
            console.log('%cEmail: developer@kabhishek18.com', 'color: #ff6600;');
            console.log('%cGitHub: https://github.com/kabhishek18', 'color: #ff6600;');
        };
        
        window.ai_mode = function() {
            console.log('%c🧠 AI ASSISTANCE MODE ACTIVATED', 'color: #ff6600; font-size: 14px; font-weight: bold;');
            console.log('%cI am ready to help you navigate the digital realm...', 'color: #00ffff;');
        };
        
        window.matrix = function() {
            const canvas = document.getElementById('matrix');
            if (canvas) {
                const currentOpacity = parseFloat(canvas.style.opacity) || 0.1;
                canvas.style.opacity = currentOpacity > 0.05 ? '0.02' : '0.1';
                console.log('%cMatrix rain toggled', 'color: #00ff00;');
            }
        };
    }

    // Add infinity pulse animation if not exists
    addInfinityAnimation() {
        if (!document.getElementById('infinity-styles')) {
            const infinityStyle = document.createElement('style');
            infinityStyle.id = 'infinity-styles';
            infinityStyle.textContent = `
                @keyframes infinityPulse {
                    0%, 100% { 
                        transform: scale(1) rotate(0deg); 
                        color: #00ffff; 
                    }
                    50% { 
                        transform: scale(1.2) rotate(180deg); 
                        color: #8a2be2; 
                    }
                }
            `;
            document.head.appendChild(infinityStyle);
        }
    }

    // Clean up method
    destroy() {
        this.components.forEach(component => {
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
        });
        this.components = [];
    }
}

// Global error handling with style
window.addEventListener('error', function(e) {
    console.error('%c⚠️ SYSTEM ERROR DETECTED', 'color: #ff0000; font-size: 14px; font-weight: bold;');
    console.error('%cInitiating auto-repair protocols...', 'color: #ff6600;');
    console.error('Error details:', e.error);
});

// Unhandled promise rejection handling
window.addEventListener('unhandledrejection', function(e) {
    console.error('%c⚠️ PROMISE REJECTION DETECTED', 'color: #ff0000; font-size: 14px; font-weight: bold;');
    console.error('Promise rejection details:', e.reason);
});

// Easter egg - Konami Code
document.addEventListener('keydown', function(e) {
    const konamiCode = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65];
    window.konamiProgress = window.konamiProgress || 0;
    
    if (e.keyCode === konamiCode[window.konamiProgress]) {
        window.konamiProgress++;
        if (window.konamiProgress === konamiCode.length) {
            console.log('%c🎮 CHEAT CODE ACTIVATED!', 'color: #ff6600; font-size: 16px; font-weight: bold;');
            console.log('%cYou have unlocked the secret developer mode!', 'color: #00ffff;');
            
            // Add special effects
            document.body.style.animation = 'rainbow 2s ease-in-out';
            
            if (!document.getElementById('rainbow-styles')) {
                const rainbowStyle = document.createElement('style');
                rainbowStyle.id = 'rainbow-styles';
                rainbowStyle.textContent = `
                    @keyframes rainbow {
                        0% { filter: hue-rotate(0deg); }
                        100% { filter: hue-rotate(360deg); }
                    }
                `;
                document.head.appendChild(rainbowStyle);
            }
            
            window.konamiProgress = 0;
        }
    } else {
        window.konamiProgress = 0;
    }
});

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const app = new App();
    app.init().catch(error => {
        console.error('Failed to initialize app:', error);
    });
    
    // Add infinity animation styles
    app.addInfinityAnimation();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        app.destroy();
    });
});


