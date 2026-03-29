import React from 'react';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import './Projects.css';

const PROJECTS = [
  {
    title: 'HerKey Agentic Fleet',
    desc: 'Proprietary Cognitive Context Layer and Agentic Fleet (Knowledge, Data, Action Agents) to orchestrate complex GenAI workflows with PII guardrails.',
    tech: ['Python', 'LangChain', 'LLMs'],
    link: '#'
  },
  {
    title: 'Magic Profanity Detection',
    desc: 'Automated trust & safety engine leveraging hybrid NLP models and AWS Rekognition for high-stakes content moderation at scale.',
    tech: ['spaCy', 'TensorFlow', 'AWS'],
    link: '#'
  },
  {
    title: 'Airbus PLM Modernization',
    desc: 'Migrated legacy European aviation systems to modern internal architectures, drastically improving performance and system robustness.',
    tech: ['Django', 'React', 'Docker'],
    link: '#'
  }
];

export const Projects: React.FC = () => {
  return (
    <section className="section-container" id="projects">
      <h2 className="headline-lg projects-header">02. DEPLOYMENTS</h2>
      <div className="projects-grid">
        {PROJECTS.map((proj, idx) => (
          <Card key={idx} hoverable className="project-card">
            <h3 className="title-lg">{proj.title}</h3>
            <p className="body-lg">{proj.desc}</p>
            <div className="project-tech">
              {proj.tech.map((t) => <Badge key={t}>{t}</Badge>)}
            </div>
            <a href={proj.link} className="label-md project-link">View Demo &rarr;</a>
          </Card>
        ))}
      </div>
    </section>
  );
};
