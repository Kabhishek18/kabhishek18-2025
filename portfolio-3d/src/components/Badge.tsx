import React from 'react';
import './Badge.css';

interface BadgeProps {
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({ children }) => {
  return <span className="aether-badge">{children}</span>;
};
