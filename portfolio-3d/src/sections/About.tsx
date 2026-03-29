import React from 'react';
import { Badge } from '../components/Badge';
import './About.css';

export const About: React.FC = () => {
  return (
    <section className="section-container" id="about">
      <div className="about-grid">
        <div className="about-text">
          <h2 className="headline-lg">01. SYSTEM_ARCHITECT</h2>
          <p className="body-lg">
            I am a Technical Lead specializing in AI & Trust Engineering, focusing on where performant code meets Generative AI. My specialty lies in Agentic LLM architectures, scalable data pipelines, and building reliable distributed software systems that power millions of users.
          </p>
          <div className="skills-grid">
            <Badge>Python / Django</Badge>
            <Badge>GenAI / LangChain</Badge>
            <Badge>AWS / Kubernetes</Badge>
            <Badge>React / Next.js</Badge>
          </div>
        </div>
        <div className="about-visual glass-panel">
          <p className="label-md">Status: Online</p>
          <div className="status-indicator"></div>
        </div>
      </div>
    </section>
  );
};
