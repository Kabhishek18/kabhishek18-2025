import { useState, useCallback } from "react";
import "./styles/Work.css";
import { MdArrowBack, MdArrowForward, MdOpenInNew } from "react-icons/md";

const projects = [
  {
    title: "AI Mock Interview Bot",
    repo: "AI-Mock-Interview-Bot",
    category: "Voice AI Career Simulation",
    description:
      "A voice-based mock interview system that speaks questions, listens to spoken answers, uses your resume for tailored prompts, and generates a structured evaluation report locally.",
    highlights: [
      "100% local execution with Ollama, Whisper, and pyttsx3",
      "Resume-aware interview generation",
      "No API keys or paid services required",
    ],
    tools: "Python, Ollama, Whisper, pyttsx3, STT/TTS",
    link: "https://github.com/Kabhishek18/AI-Mock-Interview-Bot",
  },
  {
    title: "Magic Profanity",
    repo: "magic_profanity",
    category: "Trust and Safety Library",
    description:
      "A Python library for detecting and censoring profanity with customizable word lists and character mappings, built for English and Hinglish moderation workflows.",
    highlights: [
      "Customizable censoring and mappings",
      "English and Hinglish support",
      "Sentiment analysis and text enhancement suggestions",
    ],
    tools: "Python, NLP, moderation tooling",
    link: "https://github.com/Kabhishek18/magic_profanity",
  },
  {
    title: "Jitsi Plus Plugin",
    repo: "jitsi-plugin",
    category: "Realtime Communication Platform",
    description:
      "A comprehensive Python integration for Jitsi Meet covering conferencing, audio calls, broadcasting, and VOD, aimed at serious realtime communication products.",
    highlights: [
      "Video conferencing, polls, Q&A, whiteboard, and chat",
      "Broadcasting with RTMP/HLS and recording support",
      "VOD playback with advertisement support and high scalability",
    ],
    tools: "Python, Jitsi Meet, streaming, realtime systems",
    link: "https://github.com/Kabhishek18/jitsi-plugin",
  },
  {
    title: "Deep Live Cam",
    repo: "Deep-Live-Cam",
    category: "Responsible AI Media Tooling",
    description:
      "A deepfake-oriented media tool framed around responsible usage, built-in content restrictions, and explicit ethical guidance for AI-generated media workflows.",
    highlights: [
      "Designed for productive AI media workflows",
      "Built-in restrictions for unsafe or sensitive content",
      "Strong emphasis on consent, labeling, and legal compliance",
    ],
    tools: "AI media, computer vision, responsible AI",
    link: "https://github.com/Kabhishek18/Deep-Live-Cam",
  },
];

const Work = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const goToSlide = useCallback(
    (index: number) => {
      if (isAnimating) return;
      setIsAnimating(true);
      setCurrentIndex(index);
      setTimeout(() => setIsAnimating(false), 500);
    },
    [isAnimating]
  );

  const goToPrev = useCallback(() => {
    const newIndex =
      currentIndex === 0 ? projects.length - 1 : currentIndex - 1;
    goToSlide(newIndex);
  }, [currentIndex, goToSlide]);

  const goToNext = useCallback(() => {
    const newIndex =
      currentIndex === projects.length - 1 ? 0 : currentIndex + 1;
    goToSlide(newIndex);
  }, [currentIndex, goToSlide]);

  return (
    <div className="work-section" id="work">
      <div className="work-container section-container">
        <div className="work-header">
          <div>
            <p className="work-kicker">Selected Projects</p>
            <h2>
              Project <span>Systems</span>
            </h2>
            <p className="work-summary">
              A focused set of open projects spanning voice AI, trust and
              safety, realtime communication, and responsible AI media tooling.
            </p>
          </div>
          <a
            className="work-profile-link"
            href="https://github.com/Kabhishek18?tab=repositories"
            target="_blank"
            rel="noreferrer"
            data-cursor="disable"
          >
            View All Repositories <MdOpenInNew />
          </a>
        </div>

        <div className="carousel-wrapper">
          <button
            className="carousel-arrow carousel-arrow-left"
            onClick={goToPrev}
            aria-label="Previous project"
            data-cursor="disable"
          >
            <MdArrowBack />
          </button>
          <button
            className="carousel-arrow carousel-arrow-right"
            onClick={goToNext}
            aria-label="Next project"
            data-cursor="disable"
          >
            <MdArrowForward />
          </button>

          <div className="carousel-track-container">
            <div
              className="carousel-track"
              style={{
                transform: `translateX(-${currentIndex * 100}%)`,
              }}
            >
              {projects.map((project, index) => (
                <div className="carousel-slide" key={project.repo}>
                  <div className="carousel-content carousel-content-text">
                    <div className="carousel-info carousel-info-text">
                      <div className="carousel-number">
                        <h3>0{index + 1}</h3>
                      </div>
                      <div className="carousel-details">
                        <div className="work-meta-row">
                          <span>{project.category}</span>
                          <span>{project.repo}</span>
                        </div>
                        <h4>{project.title}</h4>
                        <p className="carousel-description">
                          {project.description}
                        </p>
                        <div className="carousel-tools">
                          <span className="tools-label">Stack & Focus</span>
                          <p>{project.tools}</p>
                        </div>
                        <div className="work-highlight-list">
                          {project.highlights.map((highlight) => (
                            <div className="work-highlight-item" key={highlight}>
                              {highlight}
                            </div>
                          ))}
                        </div>
                        <div className="work-actions">
                          <a
                            href={project.link}
                            target="_blank"
                            rel="noreferrer"
                            data-cursor="disable"
                          >
                            GitHub Repo
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="carousel-dots">
            {projects.map((project, index) => (
              <button
                key={project.repo}
                className={`carousel-dot ${
                  index === currentIndex ? "carousel-dot-active" : ""
                }`}
                onClick={() => goToSlide(index)}
                aria-label={`Go to project ${index + 1}`}
                data-cursor="disable"
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Work;
