import React from 'react';
import './Experience.css';

const EXPERIENCES = [
  {
    role: 'Senior Software Tech Lead',
    company: 'HerKey',
    date: '05/2023 - Present',
    desc: 'Architected multiple GenAI production systems and Agentic Airflows (Simkey) serving 500+ concurrent requests. Optimized system architecture driving 30% boost in user retention.'
  },
  {
    role: 'Senior Software Developer',
    company: 'Capgemini',
    date: '08/2021 - 04/2023',
    desc: 'Developed AI-driven anomaly detection for Airbus Review Tool (ART). Orchestrated migration of legacy Design Quality Check systems reducing support tickets by 20%.'
  },
  {
    role: 'Full Stack Developer',
    company: 'SOFTWILL Infotech',
    date: '06/2019 - 10/2020',
    desc: 'Built secure, scalable RESTful APIs with RBAC for high-traffic ERP/CRM platforms and automated testing to reduce delivery cycles by 25%.'
  },
  {
    role: 'Junior Associate Engineer',
    company: 'Bird Global',
    date: '08/2017 - 05/2019',
    desc: 'Engineered robust ETL workflows and REST APIs, reducing data processing time by 40% and improving overall system reliability.'
  }
];

export const Experience: React.FC = () => {
  return (
    <section className="section-container" id="experience">
      <h2 className="headline-lg exp-header">03. CHRONOLOGY</h2>
      <div className="timeline-container">
        {EXPERIENCES.map((exp, idx) => (
          <div key={idx} className="timeline-item">
            <div className="timeline-marker"></div>
            <div className="timeline-content glass-panel">
              <span className="label-md text-primary">{exp.date}</span>
              <h3 className="title-lg">{exp.role}</h3>
              <h4 className="body-lg text-secondary">{exp.company}</h4>
              <p className="body-lg timeline-desc">{exp.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
