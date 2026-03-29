import React from 'react';
import { Badge } from '../components/Badge';
import './TechStack.css';

const STACK = {
  'AI & ML': ['LLMs', 'LangChain', 'Ollama', 'spaCy', 'TensorFlow', 'PyTorch'],
  'Backend': ['Python', 'Django', 'Node.js', 'PostgreSQL', 'Redis', 'Celery'],
  'Infrastructure': ['Docker', 'Kubernetes', 'AWS', 'Jenkins'],
  'Frontend': ['React Native', 'TypeScript', 'Next.js', 'Vite']
};

export const TechStack: React.FC = () => {
  return (
    <section className="section-container" id="tech">
      <h2 className="headline-lg stack-header">04. ARCHITECTURE_STACK</h2>
      <div className="stack-grid">
        {Object.entries(STACK).map(([category, items]) => (
          <div key={category} className="stack-category glass-panel">
            <h3 className="title-lg stack-category-title">{category}</h3>
            <div className="stack-items">
              {items.map(item => <Badge key={item}>{item}</Badge>)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
