import React from 'react';
import { Button } from '../components/Button';
import { FaGithub, FaLinkedin, FaTwitter } from 'react-icons/fa';
import './Contact.css';

export const Contact: React.FC = () => {
  return (
    <section className="section-container" id="contact">
      <div className="contact-wrapper glass-panel">
        <div className="contact-info">
          <h2 className="headline-lg">05. INITIATE_HANDSHAKE</h2>
          <p className="body-lg">
            Currently open for new opportunities. Whether you have a question or just want to say hi, my inbox is always open.
          </p>
          <div className="social-links">
            <a href="#" className="social-icon"><FaGithub size={24} /></a>
            <a href="#" className="social-icon"><FaLinkedin size={24} /></a>
            <a href="#" className="social-icon"><FaTwitter size={24} /></a>
          </div>
        </div>
        <form className="contact-form" onSubmit={(e) => e.preventDefault()}>
          <div className="form-group">
            <input type="text" placeholder="Name" required className="aether-input" />
          </div>
          <div className="form-group">
            <input type="email" placeholder="Email" required className="aether-input" />
          </div>
          <div className="form-group">
            <textarea placeholder="Message" rows={4} required className="aether-input"></textarea>
          </div>
          <Button variant="primary" type="submit">Send Transmission</Button>
        </form>
      </div>
    </section>
  );
};
