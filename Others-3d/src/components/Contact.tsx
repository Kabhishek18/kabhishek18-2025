import { MdArrowOutward, MdCopyright } from "react-icons/md";
import "./styles/Contact.css";

const Contact = () => {
  return (
    <div className="contact-section section-container" id="contact">
      <div className="contact-container">
        <h3>Contact</h3>
        <div className="contact-flex">
          <div className="contact-box">
            <h4>Connect</h4>
            <p>
              <a
                href="https://www.linkedin.com/in/kabhishek18/"
                target="_blank"
                rel="noreferrer"
                data-cursor="disable"
              >
                LinkedIn — kabhishek18
              </a>
            </p>
            <h4>Education</h4>
            <p>
              B.Tech Computer Science, G.L. Bajaj Institute of Technology and Management —
              2013–2017
            </p>
          </div>
          <div className="contact-box">
            <h4>Social</h4>
            <a
              href="https://github.com/kabhishek18"
              target="_blank"
              rel="noreferrer"
              data-cursor="disable"
              className="contact-social"
            >
              GitHub <MdArrowOutward />
            </a>
            <a
              href="https://www.linkedin.com/in/kabhishek18/"
              target="_blank"
              rel="noreferrer"
              data-cursor="disable"
              className="contact-social"
            >
              LinkedIn <MdArrowOutward />
            </a>
            <a
              href="mailto:developer@kabhishek18.com"
              data-cursor="disable"
              className="contact-social"
            >
              Email <MdArrowOutward />
            </a>
            <a
              href="https://kabhishek18.com"
              target="_blank"
              rel="noreferrer"
              data-cursor="disable"
              className="contact-social"
            >
              Website <MdArrowOutward />
            </a>
          </div>
          <div className="contact-box">
            <h2>
              Designed and Developed <br /> by <span>Kumar Abhishek</span>
            </h2>
            <h5>
              <MdCopyright /> 2026
            </h5>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Contact;
