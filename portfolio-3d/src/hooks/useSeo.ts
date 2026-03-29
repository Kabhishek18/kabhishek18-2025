import { useEffect } from 'react';

interface SeoOptions {
  title: string;
  description: string;
  path: string;
  structuredData?: Record<string, unknown> | Record<string, unknown>[];
}

const ensureMetaTag = (name: 'description' | 'og:title' | 'og:description' | 'og:url', attribute: 'name' | 'property') => {
  const selector = `meta[${attribute}="${name}"]`;
  let tag = document.head.querySelector(selector) as HTMLMetaElement | null;

  if (!tag) {
    tag = document.createElement('meta');
    tag.setAttribute(attribute, name);
    document.head.appendChild(tag);
  }

  return tag;
};

const ensureCanonicalLink = () => {
  let link = document.head.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;

  if (!link) {
    link = document.createElement('link');
    link.rel = 'canonical';
    document.head.appendChild(link);
  }

  return link;
};

export const useSeo = ({ title, description, path, structuredData }: SeoOptions) => {
  useEffect(() => {
    document.title = title;

    const url = new URL(path, window.location.origin).toString();
    ensureMetaTag('description', 'name').content = description;
    ensureMetaTag('og:title', 'property').content = title;
    ensureMetaTag('og:description', 'property').content = description;
    ensureMetaTag('og:url', 'property').content = url;
    ensureCanonicalLink().href = url;

    let script: HTMLScriptElement | null = null;
    if (structuredData) {
      script = document.createElement('script');
      script.type = 'application/ld+json';
      script.text = JSON.stringify(structuredData);
      document.head.appendChild(script);
    }

    return () => {
      if (script) script.remove();
    };
  }, [description, path, structuredData, title]);
};
