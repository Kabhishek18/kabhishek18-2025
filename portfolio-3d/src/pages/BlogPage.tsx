import React from 'react';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { BLOG_POSTS } from '../data/blogPosts';
import { useSeo } from '../hooks/useSeo';
import './BlogPage.css';

interface BlogPageProps {
  onOpenPost: (slug: string) => void;
}

export const BlogPage: React.FC<BlogPageProps> = ({ onOpenPost }) => {
  const featuredPost = BLOG_POSTS[0];
  const remainingPosts = BLOG_POSTS.slice(1);

  useSeo({
    title: 'Blog | Abhishek Kumar',
    description:
      'Read articles about agentic AI, frontend systems, trustworthy engineering, 3D portfolios, Django, and scalable product architecture.',
    path: '/blog',
    structuredData: {
      '@context': 'https://schema.org',
      '@type': 'Blog',
      name: 'Abhishek Kumar Blog',
      description:
        'Articles on agentic AI, frontend systems, backend architecture, and trustworthy engineering.',
      blogPost: BLOG_POSTS.map((post) => ({
        '@type': 'BlogPosting',
        headline: post.title,
        datePublished: post.publishedAt,
        url: `${window.location.origin}/blog/${post.slug}`,
      })),
    },
  });

  return (
    <main className="blog-page">
      <section className="blog-hero section-container">
        <div className="blog-hero-copy">
          <p className="label-md">Knowledge Base</p>
          <h1 className="display-lg blog-page-title">Ideas, systems, and build notes.</h1>
          <p className="body-lg blog-page-intro">
            Writing about agentic AI, frontend architecture, trustworthy systems, and the practical engineering work behind immersive products.
          </p>
        </div>
      </section>

      <section className="section-container blog-featured-section">
        <Card className="blog-featured-card">
          <div className="blog-featured-label glass-panel">
            <p className="label-md">Featured</p>
            <span>{featuredPost.coverLabel}</span>
          </div>
          <article className="blog-featured-content">
            <div className="blog-meta-row">
              <span className="label-md">{featuredPost.category}</span>
              <span className="body-lg">{featuredPost.publishedAt}</span>
              <span className="body-lg">{featuredPost.readTime}</span>
            </div>
            <h2 className="headline-lg blog-featured-title">{featuredPost.title}</h2>
            <p className="body-lg">{featuredPost.excerpt}</p>
            <div className="blog-tags">
              {featuredPost.tags.map((tag) => (
                <Badge key={tag}>{tag}</Badge>
              ))}
            </div>
            <div className="blog-featured-actions">
              <Button variant="primary" onClick={() => onOpenPost(featuredPost.slug)}>
                Read Article
              </Button>
            </div>
          </article>
        </Card>
      </section>

      <section className="section-container blog-archive-section">
        <div className="blog-archive-heading">
          <p className="label-md">Archive</p>
          <h2 className="headline-lg">Long-form notes built for readability and search.</h2>
          <p className="body-lg">
            Clear titles, structured sections, and practical takeaways designed for both readers and search engines.
          </p>
        </div>
        <div className="blog-grid">
          {remainingPosts.map((post) => (
            <Card key={post.slug} className="blog-card" hoverable>
              <div className="blog-card-cover">
                <span className="label-md">{post.coverLabel}</span>
              </div>
              <article className="blog-card-content">
                <div className="blog-meta-row">
                  <span className="label-md">{post.category}</span>
                  <span className="body-lg">{post.readTime}</span>
                </div>
                <h3 className="title-lg blog-card-title">{post.title}</h3>
                <p className="body-lg">{post.excerpt}</p>
                <div className="blog-tags">
                  {post.tags.map((tag) => (
                    <Badge key={tag}>{tag}</Badge>
                  ))}
                </div>
                <button className="blog-link-button" onClick={() => onOpenPost(post.slug)}>
                  Read More
                </button>
              </article>
            </Card>
          ))}
        </div>
      </section>
    </main>
  );
};
