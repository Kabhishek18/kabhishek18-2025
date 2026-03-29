import React from 'react';
import { Button } from '../components/Button';
import './Hero.css';

interface HeroProps {
  onLaunchAvatarStudio: () => void;
  onOpenBlog: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onLaunchAvatarStudio, onOpenBlog }) => {
  return (
    <section className="hero-section" id="hero">
      <div className="hero-content">

        <h1 className="display-lg hero-title">
          KUMAR ABHISHEK
        </h1>
        <h2 className="display-lg hero-title"> <span className="text-secondary">SENIOR SOFTWARE ENGINEER.</span></h2>
        <p className="body-lg hero-tagline">
          Architecting highly scalable, Agentic AI systems and GenAI platforms with a deep focus on Trust Engineering and distributed performance.
        </p>

        <div className="hero-highlights">
          <div className="hero-highlight glass-panel">
            <span className="label-md">Role</span>
            <span className="hero-highlight-value">Technical Lead @ HerKey</span>
          </div>
          <div className="hero-highlight glass-panel">
            <span className="label-md">Expertise</span>
            <span className="hero-highlight-value">GenAI & Trust Engineering</span>
          </div>
          <div className="hero-highlight glass-panel">
            <span className="label-md">Scale</span>
            <span className="hero-highlight-value">Engineered for 4.5M+ users</span>
          </div>
        </div>

        <div className="hero-ctas">
          <Button variant="primary" onClick={onLaunchAvatarStudio}>
            Create Avatar
          </Button>
          <Button
            variant="secondary"
            onClick={() => document.getElementById('projects')?.scrollIntoView({ behavior: 'smooth' })}
          >
            View Work
          </Button>
          <Button variant="secondary" onClick={onOpenBlog}>
            Read Blog
          </Button>
        </div>

      </div>
    </section>
  );
};
