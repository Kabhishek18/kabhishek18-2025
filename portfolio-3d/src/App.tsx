import { useEffect, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

import { Header } from './components/Header';
import { AvatarStudio } from './components/3D/AvatarStudio';
import { HeroCanvas } from './components/3D/HeroCanvas';
import { getBlogPostBySlug } from './data/blogPosts';
import { BlogDetailPage } from './pages/BlogDetailPage';
import { BlogPage } from './pages/BlogPage';
import { Hero } from './sections/Hero';
import { About } from './sections/About';
import { Projects } from './sections/Projects';
import { Experience } from './sections/Experience';
import { TechStack } from './sections/TechStack';
import { Contact } from './sections/Contact';
import { Footer } from './sections/Footer';

// Register GSAP plugins globally
gsap.registerPlugin(ScrollTrigger);

const DEFAULT_MODEL_URL = '/model.glb';
const AVATURN_STORAGE_KEY = 'portfolio-3d:avaturn-export';

type Route =
  | { name: 'home' }
  | { name: 'blog' }
  | { name: 'blog-detail'; slug: string };

const getRouteFromPath = (pathname: string): Route => {
  if (pathname === '/blog') return { name: 'blog' };
  if (pathname.startsWith('/blog/')) {
    return { name: 'blog-detail', slug: pathname.replace('/blog/', '') };
  }
  return { name: 'home' };
};

function App() {
  const [isAvatarStudioOpen, setIsAvatarStudioOpen] = useState(false);
  const [modelUrl, setModelUrl] = useState(DEFAULT_MODEL_URL);
  const [route, setRoute] = useState<Route>(() => getRouteFromPath(window.location.pathname));

  useEffect(() => {
    const savedAvatar = window.localStorage.getItem(AVATURN_STORAGE_KEY);
    if (!savedAvatar) return;

    try {
      const parsed = JSON.parse(savedAvatar) as { glbUrl?: string };
      if (parsed.glbUrl) {
        setModelUrl(parsed.glbUrl);
      }
    } catch (error) {
      console.warn('Failed to parse saved Avaturn export', error);
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setRoute(getRouteFromPath(window.location.pathname));
      window.scrollTo({ top: 0, behavior: 'auto' });
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    if (route.name !== 'home') return;

    // Fade-in animation for all section containers
    const sections = document.querySelectorAll('.section-container');
    
    sections.forEach((section) => {
      gsap.fromTo(
        section,
        { opacity: 0, y: 50 },
        {
          opacity: 1,
          y: 0,
          duration: 1,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: section,
            start: 'top 80%',
            toggleActions: 'play none none reverse',
          },
        }
      );
    });

    // Clean up
    return () => {
      ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
    };
  }, [route.name]);

  const navigate = (path: string) => {
    window.history.pushState({}, '', path);
    setRoute(getRouteFromPath(path));
    window.scrollTo({ top: 0, behavior: 'auto' });
  };

  const selectedPost = route.name === 'blog-detail' ? getBlogPostBySlug(route.slug) : null;

  return (
    <>
      <AvatarStudio
        isOpen={isAvatarStudioOpen}
        onClose={() => setIsAvatarStudioOpen(false)}
        onExport={(payload, glbUrl) => {
          setModelUrl(glbUrl);
          window.localStorage.setItem(
            AVATURN_STORAGE_KEY,
            JSON.stringify({ glbUrl, payload, exportedAt: new Date().toISOString() })
          );
        }}
      />
      {route.name === 'home' && (
        <div className="global-canvas-container">
          <HeroCanvas modelUrl={modelUrl} />
        </div>
      )}
      <div className="layout-wrapper" id="main-scroll-container">
        <Header route={route.name} onNavigate={navigate} />
        {route.name === 'home' && (
          <>
            <Hero
              onLaunchAvatarStudio={() => setIsAvatarStudioOpen(true)}
              onOpenBlog={() => navigate('/blog')}
            />
            <About />
            <Projects />
            <Experience />
            <TechStack />
            <Contact />
            <Footer />
          </>
        )}
        {route.name === 'blog' && <BlogPage onOpenPost={(slug) => navigate(`/blog/${slug}`)} />}
        {route.name === 'blog-detail' && selectedPost && (
          <BlogDetailPage
            post={selectedPost}
            onBackToBlog={() => navigate('/blog')}
            onOpenPortfolio={() => navigate('/')}
          />
        )}
        {route.name === 'blog-detail' && !selectedPost && (
          <BlogPage onOpenPost={(slug) => navigate(`/blog/${slug}`)} />
        )}
      </div>
    </>
  );
}

export default App;
