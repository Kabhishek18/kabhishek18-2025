import React from 'react';
import './Card.css';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({ children, className = '', hoverable = false }) => {
  return (
    <div className={`aether-card glass-panel ${hoverable ? 'hoverable' : ''} ${className}`}>
      {children}
    </div>
  );
};
