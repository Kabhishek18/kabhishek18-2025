import "./styles/Career.css";

const Career = () => {
  return (
    <div className="career-section section-container">
      <div className="career-container">
        <h2>
          My career <span>&</span>
          <br /> experience
        </h2>
        <div className="career-info">
          <div className="career-timeline">
            <div className="career-dot"></div>
          </div>
          <div className="career-info-box">
            <div className="career-info-in">
              <div className="career-role">
                <h4>Tech Lead</h4>
                <h5>HerKey</h5>
              </div>
              <h3>2023–NOW</h3>
            </div>
            <p>
              Architected Agentic RAG assistant handling 500+ concurrent requests. Optimized system architecture driving 30% boost in user retention.
            </p>
          </div>
          <div className="career-info-box">
            <div className="career-info-in">
              <div className="career-role">
                <h4>Software Developer</h4>
                <h5>Capgemini</h5>
              </div>
              <h3>2021–2023</h3>
            </div>
            <p>
              Developed AI-driven anomaly detection for Airbus Review Tool (ART). Orchestrated migration of legacy systems to modern architectures.
            </p>
          </div>
          <div className="career-info-box">
            <div className="career-info-in">
              <div className="career-role">
                <h4>Full Stack Dev</h4>
                <h5>SOFTWILL</h5>
              </div>
              <h3>2019–2020</h3>
            </div>
            <p>
              Built secure, scalable RESTful APIs with RBAC for high-traffic ERP/CRM platforms and automated testing to reduce delivery cycles by 25%.
            </p>
          </div>
          <div className="career-info-box">
            <div className="career-info-in">
              <div className="career-role">
                <h4>Associate Dev</h4>
                <h5>Bird Global</h5>
              </div>
              <h3>2017–2019</h3>
            </div>
            <p>
              Engineered robust ETL workflows and REST APIs, reducing data processing time by 40% and improving overall system reliability.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Career;
