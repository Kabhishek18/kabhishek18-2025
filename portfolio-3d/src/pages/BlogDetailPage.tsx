import React from 'react';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import type { BlogPost } from '../data/blogPosts';
import { BLOG_POSTS } from '../data/blogPosts';
import { useSeo } from '../hooks/useSeo';
import './BlogDetailPage.css';

interface BlogDetailPageProps {
  post: BlogPost;
  onBackToBlog: () => void;
  onOpenPortfolio: () => void;
}

export const BlogDetailPage: React.FC<BlogDetailPageProps> = ({
  post,
  onBackToBlog,
  onOpenPortfolio,
}) => {
  const relatedPosts = BLOG_POSTS.filter((entry) => entry.slug !== post.slug).slice(0, 2);

  useSeo({
    title: `${post.title} | Abhishek Kumar`,
    description: post.seoDescription,
    path: `/blog/${post.slug}`,
    structuredData: [
      {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        headline: post.title,
        description: post.seoDescription,
        datePublished: post.publishedAt,
        author: {
          '@type': 'Person',
          name: post.author,
        },
        keywords: post.tags.join(', '),
        url: `${window.location.origin}/blog/${post.slug}`,
      },
      {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: post.faqs.map((faq) => ({
          '@type': 'Question',
          name: faq.question,
          acceptedAnswer: {
            '@type': 'Answer',
            text: faq.answer,
          },
        })),
      },
    ],
  });

  return (
    <main className="blog-detail-page">
      <section className="blog-detail-hero section-container">
        <div className="blog-detail-breadcrumb">
          <button className="blog-link-button" onClick={onBackToBlog}>
            Back to Blog
          </button>
        </div>
        <div className="blog-detail-shell glass-panel">
          <div className="blog-detail-cover">
            <p className="label-md">{post.coverLabel}</p>
          </div>
          <div className="blog-detail-content">
            <div className="blog-meta-row">
              <span className="label-md">{post.category}</span>
              <span className="body-lg">{post.publishedAt}</span>
              <span className="body-lg">{post.readTime}</span>
              <span className="body-lg">By {post.author}</span>
            </div>
            <h1 className="display-lg blog-detail-title">{post.title}</h1>
            <p className="body-lg blog-detail-excerpt">{post.excerpt}</p>
            <div className="blog-tags">
              {post.tags.map((tag) => (
                <Badge key={tag}>{tag}</Badge>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section-container blog-detail-body-shell">
        <article className="blog-detail-article glass-panel">
          {post.sections.map((section) => (
            <section key={section.heading} className="blog-detail-section">
              <h2 className="headline-lg blog-detail-section-title">{section.heading}</h2>
              {section.paragraphs.map((paragraph, index) => (
                <p key={`${section.heading}-${index}`} className="blog-detail-paragraph">
                  {paragraph}
                </p>
              ))}
            </section>
          ))}

          <section className="blog-detail-section blog-faq-section">
            <h2 className="headline-lg blog-detail-section-title">FAQ</h2>
            <div className="blog-faq-list">
              {post.faqs.map((faq) => (
                <div key={faq.question} className="blog-faq-item">
                  <h3 className="title-lg">{faq.question}</h3>
                  <p className="blog-detail-paragraph">{faq.answer}</p>
                </div>
              ))}
            </div>
          </section>
        </article>

        <div className="blog-detail-cta glass-panel">
          <p className="label-md">Reader Notes</p>
          <h2 className="title-lg">Built to be readable, indexable, and ad-friendly.</h2>
          <p className="body-lg">
            Each article is structured with clear headings, durable summaries, and space for future ad placements without breaking the reading flow.
          </p>
          <div className="blog-related-list">
            {relatedPosts.map((relatedPost) => (
              <div key={relatedPost.slug} className="blog-related-item">
                <p className="label-md">{relatedPost.category}</p>
                <h3 className="title-lg">{relatedPost.title}</h3>
                <p className="body-lg">{relatedPost.readTime}</p>
              </div>
            ))}
          </div>
          <div className="blog-detail-actions">
            <Button variant="primary" onClick={onBackToBlog}>
              More Articles
            </Button>
            <Button variant="secondary" onClick={onOpenPortfolio}>
              Portfolio Home
            </Button>
          </div>
        </div>
      </section>
    </main>
  );
};
