export interface BlogSection {
  heading: string;
  paragraphs: string[];
}

export interface BlogFaq {
  question: string;
  answer: string;
}

export interface BlogPost {
  slug: string;
  title: string;
  excerpt: string;
  seoDescription: string;
  category: string;
  readTime: string;
  publishedAt: string;
  author: string;
  tags: string[];
  coverLabel: string;
  sections: BlogSection[];
  faqs: BlogFaq[];
}

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'building-agentic-ai-products-with-trust',
    title: 'Building Agentic AI Products Without Losing Trust',
    excerpt:
      'A practical framework for shipping agentic systems that stay observable, reviewable, and safe under real production load.',
    seoDescription:
      'A practical guide to building trustworthy agentic AI products with observability, human review, policy checks, and safer autonomy.',
    category: 'AI Systems',
    readTime: '7 min read',
    publishedAt: 'March 18, 2026',
    author: 'Abhishek Kumar',
    tags: ['Agentic AI', 'Trust Engineering', 'Observability'],
    coverLabel: 'Guardrails x Agents',
    sections: [
      {
        heading: 'Why trust breaks first in agentic systems',
        paragraphs: [
          'Agentic systems feel magical in demos because they compress several decision loops into one experience. In production, that same compression can hide why the system made a decision, whether the decision was grounded, and what fallback path it took when the ideal path failed.',
          'When users lose confidence, it is usually not because the system made one mistake. It is because the product gave them no clean way to understand the mistake, predict the next action, or recover safely.',
        ],
      },
      {
        heading: 'Separate autonomy from accountability',
        paragraphs: [
          'The strongest agentic products separate autonomy from accountability. Let the system plan, route, and synthesize, but always preserve enough structure for humans to inspect tool calls, confidence signals, retries, and policy checks.',
          'A good operating model is to give the agent freedom inside sharply defined boundaries. The broader the permissions, the more visible the decision trail must become.',
        ],
      },
      {
        heading: 'Design for auditability from day one',
        paragraphs: [
          'Treat every agent run like an auditable workflow. Capture intermediate state, log the source of generated claims, and expose enough telemetry that a product owner can explain a bad outcome without reading raw traces for an hour.',
          'This is also where product trust and engineering trust meet. A system that is easier to debug is almost always easier to trust.',
        ],
      },
      {
        heading: 'What teams should prioritize',
        paragraphs: [
          'Trust is rarely improved by adding more prompts. It is improved by adding review surfaces, explicit failure modes, narrow permissions, and predictable escape hatches back to the user.',
          'If a team focuses on just three things, I would prioritize observability, reversible actions, and clear human override points.',
        ],
      },
    ],
    faqs: [
      {
        question: 'What is the fastest trust improvement for an existing agentic product?',
        answer:
          'Add clearer execution traces and human review checkpoints before expanding autonomy further. Visibility usually improves trust faster than more prompt tuning.',
      },
      {
        question: 'Do all agentic products need human approval?',
        answer:
          'Not for every action, but high-impact or irreversible actions should have tighter review thresholds and stronger policy enforcement.',
      },
    ],
  },
  {
    slug: 'designing-3d-portfolios-that-still-convert',
    title: 'Designing 3D Portfolios That Still Convert',
    excerpt:
      'How to use immersive visuals, animated avatars, and cinematic layout without burying the actual story of your work.',
    seoDescription:
      'Learn how to design a 3D developer portfolio that balances visual immersion with conversion, readability, and project clarity.',
    category: 'Frontend',
    readTime: '6 min read',
    publishedAt: 'March 12, 2026',
    author: 'Abhishek Kumar',
    tags: ['3D', 'Portfolio', 'UX'],
    coverLabel: 'Immersion x Clarity',
    sections: [
      {
        heading: 'Use 3D to support hierarchy, not replace it',
        paragraphs: [
          'A 3D portfolio should increase memorability, not friction. The model, lighting, and motion need to support the narrative hierarchy instead of competing with headlines, proof points, and calls to action.',
          'If the visitor cannot understand who you are and what you build within a few seconds, the 3D layer is working against the portfolio instead of for it.',
        ],
      },
      {
        heading: 'Fix dead space with composition, not filler',
        paragraphs: [
          'The hero section usually carries too much dead space because designers leave the 3D element isolated on one side. The better move is compositional overlap: let the avatar, title, and stat blocks feel intentionally arranged so the hero reads like a poster rather than a split-screen.',
          'This keeps the screen visually active while preserving enough whitespace for scanning.',
        ],
      },
      {
        heading: 'Tie the 3D layer to content structure',
        paragraphs: [
          'Interactivity matters most when it reinforces scanning. Position shifts tied to sections, subtle animation changes, and responsive scaling all help the visitor understand that the 3D layer belongs to the content structure.',
          'That sense of relationship is what makes the experience feel designed rather than decorative.',
        ],
      },
      {
        heading: 'Conversion still comes from clarity',
        paragraphs: [
          'Every visually ambitious portfolio needs a direct route to projects, proof of technical range, and an easy contact path within seconds of landing.',
          'The portfolio earns attention through visuals, but it earns trust through clear work samples and accessible writing.',
        ],
      },
    ],
    faqs: [
      {
        question: 'Should a 3D portfolio always include a character model?',
        answer:
          'No. Use a character only if it strengthens your visual identity and still keeps the work itself easy to understand.',
      },
      {
        question: 'What matters more for hiring outcomes: animation or content?',
        answer:
          'Content clarity matters more. Animation should amplify the message, not become the message.',
      },
    ],
  },
  {
    slug: 'shipping-django-and-genai-at-scale',
    title: 'Shipping Django and GenAI at Scale',
    excerpt:
      'Notes from combining Django, queues, LLM tooling, and structured backends into a stack that survives real traffic and editorial workflows.',
    seoDescription:
      'A practical look at scaling Django and GenAI products with queues, service boundaries, structured validation, and reliable background processing.',
    category: 'Backend',
    readTime: '8 min read',
    publishedAt: 'March 4, 2026',
    author: 'Abhishek Kumar',
    tags: ['Django', 'Celery', 'LLMs'],
    coverLabel: 'Django x GenAI',
    sections: [
      {
        heading: 'GenAI backends are orchestration systems',
        paragraphs: [
          'The first mistake teams make with GenAI backends is treating them like normal request-response features. They are usually orchestration problems involving retries, asynchronous work, rate limits, partial failures, and expensive third-party dependencies.',
          'Once you see the system that way, the architecture decisions become clearer and less magical.',
        ],
      },
      {
        heading: 'Why Django still works well',
        paragraphs: [
          'Django remains a strong foundation when you pair it with explicit task queues, typed service boundaries, and model-level discipline. The framework gives you structure; the hard part is deciding where AI-specific behavior belongs and where plain business logic should remain boring.',
          'That boring foundation is often the thing that lets the AI features evolve safely.',
        ],
      },
      {
        heading: 'Service boundaries matter',
        paragraphs: [
          'In practice, the stack becomes more stable when prompt construction, external model access, validation, and persistence each live in separate modules. That boundary lets you swap providers, tighten policy checks, and test core flows without mocking half the application.',
          'It also creates cleaner ownership lines for teams working across platform, product, and operations concerns.',
        ],
      },
      {
        heading: 'Scale comes from operational discipline',
        paragraphs: [
          'Scalability is less about one giant architecture move and more about refusing ambiguity in background jobs, schema contracts, and operator visibility.',
          'If you make failures explicit and contracts narrow, the system becomes far easier to extend under real production traffic.',
        ],
      },
    ],
    faqs: [
      {
        question: 'Should GenAI tasks run inside web requests?',
        answer:
          'Only for short, low-risk tasks. Anything expensive, retry-prone, or provider-dependent usually belongs in background work.',
      },
      {
        question: 'What helps most when scaling a Django plus GenAI stack?',
        answer:
          'Clear service boundaries, durable queues, strict validation, and strong operational visibility tend to provide the biggest stability gains.',
      },
    ],
  },
];

export const getBlogPostBySlug = (slug: string) =>
  BLOG_POSTS.find((post) => post.slug === slug);
