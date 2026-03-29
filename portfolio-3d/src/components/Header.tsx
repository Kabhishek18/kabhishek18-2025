import React, { useEffect, useState } from 'react';
import './Header.css';

interface HeaderProps {
  route: 'home' | 'blog' | 'blog-detail';
  onNavigate: (path: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ route, onNavigate }) => {
  const [scrolled, setScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState<string>('');

  // Add scroll listener for sticky nav style updates
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    handleScroll();
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Intersection Observer for highlighting the active section in the nav
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          setActiveSection(entry.target.id);
        }
      });
    }, { rootMargin: '-20% 0px -70% 0px' });

    // Ensure we also grab the hero section if we add an ID
    const sections = document.querySelectorAll('.section-container, .hero-section');
    sections.forEach(section => observer.observe(section));

    return () => sections.forEach(section => observer.unobserve(section));
  }, []);

  return (
    <header className={`site-header ${scrolled ? 'scrolled' : ''}`}>
      <div className="header-container">
        <button className="logo logo-button" onClick={() => onNavigate('/')}>
          The&nbsp; <span className="text-secondary">Digital</span> Architect
        </button>
        <nav className="main-nav">
          {route === 'home' ? (
            <ul className="nav-links">
              <li><a href="#about" className={activeSection === 'about' ? 'active' : ''}>About</a></li>
              <li><a href="#projects" className={activeSection === 'projects' ? 'active' : ''}>Work</a></li>
              <li><a href="#experience" className={activeSection === 'experience' ? 'active' : ''}>Experience</a></li>
              <li><a href="#tech" className={activeSection === 'tech' ? 'active' : ''}>Stack</a></li>
              <li><a href="#contact" className={activeSection === 'contact' ? 'active' : ''}>Contact</a></li>
              <li>
                <button className="nav-action" onClick={() => onNavigate('/blog')}>
                  Blog
                </button>
              </li>
            </ul>
          ) : (
            <ul className="nav-links">
              <li>
                <button
                  className={`nav-action ${route === 'blog' || route === 'blog-detail' ? 'active' : ''}`}
                  onClick={() => onNavigate('/blog')}
                >
                  Blog
                </button>
              </li>
              <li>
                <button className="nav-action" onClick={() => onNavigate('/')}>
                  Portfolio
                </button>
              </li>
            </ul>
          )}
          <a href="/resume.pdf" className="resume-btn" target="_blank" rel="noopener noreferrer">
            RESUME
          </a>
        </nav>
      </div>
    </header>
  );
};
