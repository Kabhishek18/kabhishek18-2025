import React from 'react';
import './Footer.css';

export const Footer: React.FC = () => {
  return (
    <footer className="footer-container">
      <div className="footer-content">
        <p className="label-md">© {new Date().getFullYear()} ABHISHEK. ALL RIGHTS RESERVED.</p>
        <p className="body-lg footer-credit">
          Designed with Aether Core. Built with React & Vite. 
          <span className="cursor-block"></span>
        </p>
      </div>
    </footer>
  );
};
