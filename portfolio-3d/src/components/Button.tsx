import React from 'react';
import './Button.css';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({ variant = 'primary', children, ...props }) => {
  return (
    <button className={`aether-btn aether-btn-${variant}`} {...props}>
      {children}
    </button>
  );
};
