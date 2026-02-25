from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Post, Category, Tag
from django.utils.text import slugify
from django.utils import timezone
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Automated content pipeline for consistent publishing'

    def add_arguments(self, parser):
        parser.add_argument('--generate', action='store_true', help='Generate new content ideas')
        parser.add_argument('--schedule', action='store_true', help='Schedule content publishing')
        parser.add_argument('--templates', action='store_true', help='Create content templates')
        parser.add_argument('--count', type=int, default=3, help='Number of posts to generate')

    def handle(self, *args, **options):
        if options.get('generate'):
            self.generate_content_ideas(options.get('count', 3))
        
        if options.get('schedule'):
            self.schedule_content_publishing()
        
        if options.get('templates'):
            self.create_content_templates()
        
        self.stdout.write(
            self.style.SUCCESS('Content pipeline operations completed successfully')
        )

    def generate_content_ideas(self, count):
        """Generate new content ideas and draft posts"""
        self.stdout.write(f"Generating {count} new content ideas...")
        
        # Get or create author
        author, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True}
        )
        
        # Content idea templates
        content_ideas = [
            {
                'title': 'Django REST API Authentication: JWT vs Session-Based Auth',
                'category': 'Django Tutorials',
                'tags': ['Django', 'REST API', 'Authentication', 'JWT'],
                'content_type': 'comparison_guide',
                'estimated_length': '2500-3000 words'
            },
            {
                'title': 'Python Async Programming: Complete Guide to asyncio',
                'category': 'Python Programming',
                'tags': ['Python', 'Async', 'Performance', 'Tutorial'],
                'content_type': 'comprehensive_tutorial',
                'estimated_length': '3000-3500 words'
            },
            {
                'title': 'Database Indexing Strategies for High-Performance Applications',
                'category': 'Database Management',
                'tags': ['Database', 'Performance', 'Optimization', 'PostgreSQL'],
                'content_type': 'technical_guide',
                'estimated_length': '2000-2500 words'
            },
            {
                'title': 'Modern CSS Grid vs Flexbox: When to Use Which',
                'category': 'Web Development',
                'tags': ['CSS', 'Frontend', 'Layout', 'Best Practices'],
                'content_type': 'comparison_guide',
                'estimated_length': '2000-2500 words'
            },
            {
                'title': 'Microservices Architecture: Design Patterns and Best Practices',
                'category': 'Best Practices',
                'tags': ['Architecture', 'Microservices', 'Design Patterns'],
                'content_type': 'architecture_guide',
                'estimated_length': '3500-4000 words'
            },
            {
                'title': 'Docker for Django Development: Complete Setup Guide',
                'category': 'Django Tutorials',
                'tags': ['Docker', 'Django', 'DevOps', 'Tutorial'],
                'content_type': 'setup_tutorial',
                'estimated_length': '2500-3000 words'
            },
            {
                'title': 'API Rate Limiting: Implementation Strategies and Best Practices',
                'category': 'Security',
                'tags': ['API', 'Security', 'Rate Limiting', 'Performance'],
                'content_type': 'implementation_guide',
                'estimated_length': '2000-2500 words'
            },
            {
                'title': 'React Hooks: Advanced Patterns and Performance Optimization',
                'category': 'JavaScript',
                'tags': ['React', 'JavaScript', 'Hooks', 'Performance'],
                'content_type': 'advanced_tutorial',
                'estimated_length': '3000-3500 words'
            },
            {
                'title': 'GraphQL vs REST: Complete Comparison for Modern APIs',
                'category': 'Web Development',
                'tags': ['GraphQL', 'REST API', 'API Design', 'Comparison'],
                'content_type': 'comparison_guide',
                'estimated_length': '2500-3000 words'
            },
            {
                'title': 'Kubernetes for Python Applications: Deployment Guide',
                'category': 'Python Programming',
                'tags': ['Kubernetes', 'Python', 'DevOps', 'Deployment'],
                'content_type': 'deployment_guide',
                'estimated_length': '3000-3500 words'
            }
        ]
        
        # Select random ideas
        selected_ideas = random.sample(content_ideas, min(count, len(content_ideas)))
        
        for i, idea in enumerate(selected_ideas):
            # Create draft post
            category, _ = Category.objects.get_or_create(
                name=idea['category'],
                defaults={'slug': slugify(idea['category'])}
            )
            
            # Create content outline
            content_outline = self.generate_content_outline(idea)
            
            post = Post.objects.create(
                title=idea['title'],
                slug=slugify(idea['title']),
                author=author,
                content=content_outline,
                excerpt=f"Comprehensive guide covering {idea['title'].lower()}. {idea['estimated_length']} of practical insights and examples.",
                status='draft',  # Keep as draft for completion
                allow_comments=True
            )
            
            post.categories.add(category)
            
            # Add tags
            for tag_name in idea['tags']:
                tag, _ = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': slugify(tag_name), 'color': self.get_tag_color(tag_name)}
                )
                post.tags.add(tag)
            
            self.stdout.write(f"Created draft: {post.title}")
        
        self.stdout.write(f"Generated {len(selected_ideas)} content ideas as draft posts")

    def generate_content_outline(self, idea):
        """Generate a detailed content outline for the post"""
        content_type = idea['content_type']
        
        if content_type == 'comparison_guide':
            return self.get_comparison_outline(idea)
        elif content_type == 'comprehensive_tutorial':
            return self.get_tutorial_outline(idea)
        elif content_type == 'technical_guide':
            return self.get_technical_guide_outline(idea)
        elif content_type == 'architecture_guide':
            return self.get_architecture_outline(idea)
        elif content_type == 'setup_tutorial':
            return self.get_tutorial_outline(idea)
        elif content_type == 'implementation_guide':
            return self.get_technical_guide_outline(idea)
        elif content_type == 'advanced_tutorial':
            return self.get_tutorial_outline(idea)
        elif content_type == 'deployment_guide':
            return self.get_tutorial_outline(idea)
        else:
            return self.get_generic_outline(idea)

    def get_comparison_outline(self, idea):
        """Generate outline for comparison guides"""
        return f"""
<h2>Introduction to {idea['title']}</h2>
<p>[Write introduction explaining the importance of this comparison and what readers will learn]</p>

<h2>Overview of Both Approaches</h2>
<p>[Provide brief overview of both technologies/approaches being compared]</p>

<h3>Option 1: [First Technology/Approach]</h3>
<p>[Detailed explanation of first option]</p>

<h3>Option 2: [Second Technology/Approach]</h3>
<p>[Detailed explanation of second option]</p>

<h2>Detailed Comparison</h2>

<h3>Performance Comparison</h3>
<p>[Compare performance characteristics]</p>

<h3>Ease of Implementation</h3>
<p>[Compare implementation complexity]</p>

<h3>Scalability Considerations</h3>
<p>[Compare scalability aspects]</p>

<h3>Security Implications</h3>
<p>[Compare security features and considerations]</p>

<h2>Use Cases and Scenarios</h2>

<h3>When to Choose Option 1</h3>
<p>[Specific scenarios where first option is better]</p>

<h3>When to Choose Option 2</h3>
<p>[Specific scenarios where second option is better]</p>

<h2>Implementation Examples</h2>

<h3>Example 1: [First Option Implementation]</h3>
<p>[Code example and explanation]</p>

<h3>Example 2: [Second Option Implementation]</h3>
<p>[Code example and explanation]</p>

<h2>Best Practices and Recommendations</h2>
<p>[General best practices for both approaches]</p>

<h2>Migration Strategies</h2>
<p>[How to migrate from one approach to another if needed]</p>

<h2>Conclusion and Decision Framework</h2>
<p>[Summary and decision-making framework for readers]</p>

<!-- TODO: Add code examples, diagrams, and practical implementations -->
<!-- Estimated length: {idea['estimated_length']} -->
<!-- Tags: {', '.join(idea['tags'])} -->
        """

    def get_tutorial_outline(self, idea):
        """Generate outline for comprehensive tutorials"""
        return f"""
<h2>Introduction to {idea['title']}</h2>
<p>[Explain what readers will learn and prerequisites]</p>

<h2>Prerequisites and Setup</h2>
<p>[List required knowledge and setup instructions]</p>

<h3>Required Tools and Dependencies</h3>
<p>[List all necessary tools and how to install them]</p>

<h3>Environment Setup</h3>
<p>[Step-by-step environment configuration]</p>

<h2>Fundamental Concepts</h2>
<p>[Explain core concepts readers need to understand]</p>

<h3>Key Terminology</h3>
<p>[Define important terms and concepts]</p>

<h3>Basic Principles</h3>
<p>[Explain underlying principles]</p>

<h2>Step-by-Step Implementation</h2>

<h3>Step 1: [First Major Step]</h3>
<p>[Detailed instructions with code examples]</p>

<h3>Step 2: [Second Major Step]</h3>
<p>[Detailed instructions with code examples]</p>

<h3>Step 3: [Third Major Step]</h3>
<p>[Detailed instructions with code examples]</p>

<h2>Advanced Techniques</h2>
<p>[Cover advanced usage patterns and optimizations]</p>

<h3>Performance Optimization</h3>
<p>[Performance tips and best practices]</p>

<h3>Error Handling</h3>
<p>[Proper error handling strategies]</p>

<h2>Common Pitfalls and Solutions</h2>
<p>[Address common mistakes and how to avoid them]</p>

<h2>Testing and Debugging</h2>
<p>[How to test and debug implementations]</p>

<h2>Production Considerations</h2>
<p>[What to consider when deploying to production]</p>

<h2>Further Reading and Resources</h2>
<p>[Additional resources for continued learning]</p>

<h2>Conclusion</h2>
<p>[Summarize key takeaways and next steps]</p>

<!-- TODO: Add comprehensive code examples, screenshots, and practical exercises -->
<!-- Estimated length: {idea['estimated_length']} -->
<!-- Tags: {', '.join(idea['tags'])} -->
        """

    def get_technical_guide_outline(self, idea):
        """Generate outline for technical guides"""
        return f"""
<h2>Introduction to {idea['title']}</h2>
<p>[Explain the technical topic and its importance]</p>

<h2>Technical Background</h2>
<p>[Provide necessary technical context]</p>

<h3>Core Concepts</h3>
<p>[Explain fundamental technical concepts]</p>

<h3>Architecture Overview</h3>
<p>[High-level architecture or system design]</p>

<h2>Implementation Details</h2>

<h3>Design Considerations</h3>
<p>[Important design decisions and trade-offs]</p>

<h3>Technical Implementation</h3>
<p>[Detailed technical implementation with code]</p>

<h3>Configuration and Setup</h3>
<p>[Configuration options and setup procedures]</p>

<h2>Performance Analysis</h2>
<p>[Performance characteristics and optimization strategies]</p>

<h3>Benchmarking</h3>
<p>[Performance benchmarks and metrics]</p>

<h3>Optimization Techniques</h3>
<p>[Specific optimization strategies]</p>

<h2>Security Considerations</h2>
<p>[Security implications and best practices]</p>

<h2>Monitoring and Maintenance</h2>
<p>[How to monitor and maintain the implementation]</p>

<h2>Troubleshooting Guide</h2>
<p>[Common issues and their solutions]</p>

<h2>Case Studies and Examples</h2>
<p>[Real-world examples and case studies]</p>

<h2>Conclusion and Best Practices</h2>
<p>[Summary of best practices and recommendations]</p>

<!-- TODO: Add technical diagrams, code examples, and performance data -->
<!-- Estimated length: {idea['estimated_length']} -->
<!-- Tags: {', '.join(idea['tags'])} -->
        """

    def get_generic_outline(self, idea):
        """Generate generic outline for other content types"""
        return f"""
<h2>Introduction</h2>
<p>[Introduction to the topic - explain what readers will learn]</p>

<h2>Background and Context</h2>
<p>[Provide necessary background information]</p>

<h2>Main Content Section 1</h2>
<p>[First major section of content]</p>

<h2>Main Content Section 2</h2>
<p>[Second major section of content]</p>

<h2>Main Content Section 3</h2>
<p>[Third major section of content]</p>

<h2>Practical Examples</h2>
<p>[Code examples and practical implementations]</p>

<h2>Best Practices</h2>
<p>[Industry best practices and recommendations]</p>

<h2>Common Challenges and Solutions</h2>
<p>[Address common issues and provide solutions]</p>

<h2>Conclusion</h2>
<p>[Summarize key points and provide next steps]</p>

<!-- TODO: Expand each section with detailed content, examples, and code -->
<!-- Estimated length: {idea['estimated_length']} -->
<!-- Tags: {', '.join(idea['tags'])} -->
        """

    def get_tag_color(self, tag_name):
        """Get appropriate color for tags"""
        color_map = {
            'Django': '#092e20',
            'Python': '#3776ab',
            'JavaScript': '#f7df1e',
            'React': '#61dafb',
            'Database': '#336791',
            'Security': '#dc3545',
            'Performance': '#28a745',
            'API': '#17a2b8',
            'Tutorial': '#20c997',
            'Guide': '#6610f2',
            'Docker': '#2496ed',
            'Kubernetes': '#326ce5',
            'DevOps': '#ff6b35',
            'Architecture': '#6f42c1',
            'Frontend': '#e83e8c',
            'Backend': '#fd7e14'
        }
        return color_map.get(tag_name, '#6c757d')

    def schedule_content_publishing(self):
        """Schedule draft posts for publishing"""
        self.stdout.write("Scheduling content for publishing...")
        
        draft_posts = Post.objects.filter(status='draft').order_by('created_at')
        
        if not draft_posts:
            self.stdout.write("No draft posts found to schedule")
            return
        
        # Schedule posts for the next few weeks (2-3 posts per week)
        base_date = timezone.now().date()
        schedule_dates = []
        
        # Generate publishing schedule (Monday, Wednesday, Friday)
        for week in range(4):  # Next 4 weeks
            week_start = base_date + timedelta(weeks=week)
            # Find Monday of the week
            monday = week_start - timedelta(days=week_start.weekday())
            
            schedule_dates.extend([
                monday,  # Monday
                monday + timedelta(days=2),  # Wednesday
                monday + timedelta(days=4),  # Friday
            ])
        
        scheduled_count = 0
        for i, post in enumerate(draft_posts[:len(schedule_dates)]):
            # Don't schedule posts that are just outlines
            if len(post.content) < 1000:
                self.stdout.write(f"Skipping {post.title} - needs more content")
                continue
            
            schedule_date = schedule_dates[i]
            # Set publishing date (you might want to implement a custom field for this)
            post.created_at = timezone.make_aware(
                datetime.combine(schedule_date, datetime.min.time())
            )
            post.save()
            scheduled_count += 1
            
            self.stdout.write(f"Scheduled: {post.title} for {schedule_date}")
        
        self.stdout.write(f"Scheduled {scheduled_count} posts for publishing")

    def create_content_templates(self):
        """Create reusable content templates"""
        self.stdout.write("Creating content templates...")
        
        templates = {
            'tutorial_template.md': self.get_tutorial_template(),
            'comparison_template.md': self.get_comparison_template(),
            'case_study_template.md': self.get_case_study_template(),
            'technical_guide_template.md': self.get_technical_guide_template()
        }
        
        import os
        template_dir = 'content_templates'
        os.makedirs(template_dir, exist_ok=True)
        
        for filename, content in templates.items():
            filepath = os.path.join(template_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            self.stdout.write(f"Created template: {filepath}")
        
        self.stdout.write(f"Created {len(templates)} content templates in {template_dir}/")

    def get_tutorial_template(self):
        """Get tutorial template"""
        return """# [TUTORIAL TITLE]

## Introduction
- What will readers learn?
- Prerequisites
- Estimated time to complete

## Prerequisites and Setup
- Required knowledge
- Tools and dependencies
- Environment setup

## Step-by-Step Guide

### Step 1: [First Step]
- Detailed instructions
- Code examples
- Expected output

### Step 2: [Second Step]
- Detailed instructions
- Code examples
- Expected output

### Step 3: [Third Step]
- Detailed instructions
- Code examples
- Expected output

## Advanced Techniques
- Performance optimization
- Best practices
- Common patterns

## Troubleshooting
- Common issues
- Solutions
- Debugging tips

## Conclusion
- Summary of what was learned
- Next steps
- Additional resources

## Code Repository
- Link to complete code examples
- Installation instructions
- Usage examples
"""

    def get_comparison_template(self):
        """Get comparison template"""
        return """# [TECHNOLOGY A] vs [TECHNOLOGY B]: Complete Comparison

## Introduction
- Why this comparison matters
- What readers will learn
- Decision framework overview

## Overview
### [Technology A]
- Brief description
- Key features
- Primary use cases

### [Technology B]
- Brief description
- Key features
- Primary use cases

## Detailed Comparison

### Performance
- Speed benchmarks
- Resource usage
- Scalability

### Ease of Use
- Learning curve
- Development experience
- Documentation quality

### Ecosystem
- Community support
- Available libraries
- Third-party integrations

### Security
- Security features
- Vulnerability history
- Best practices

## Use Cases

### When to Choose [Technology A]
- Specific scenarios
- Team considerations
- Project requirements

### When to Choose [Technology B]
- Specific scenarios
- Team considerations
- Project requirements

## Implementation Examples
- Side-by-side code examples
- Configuration comparisons
- Deployment differences

## Migration Considerations
- Moving from A to B
- Moving from B to A
- Hybrid approaches

## Conclusion
- Summary table
- Decision framework
- Recommendations
"""

    def get_case_study_template(self):
        """Get case study template"""
        return """# [PROJECT NAME]: Technical Case Study

## Project Overview
- Problem statement
- Goals and objectives
- Success metrics

## Technical Challenges
- Primary challenges faced
- Constraints and limitations
- Requirements analysis

## Solution Architecture
- High-level architecture
- Technology stack decisions
- Design patterns used

## Implementation Details

### Phase 1: [First Phase]
- Objectives
- Implementation approach
- Key decisions

### Phase 2: [Second Phase]
- Objectives
- Implementation approach
- Key decisions

### Phase 3: [Third Phase]
- Objectives
- Implementation approach
- Key decisions

## Technical Deep Dive
- Code examples
- Database design
- API architecture
- Performance optimizations

## Challenges and Solutions
- Major obstacles encountered
- How they were overcome
- Lessons learned

## Results and Metrics
- Performance improvements
- User experience enhancements
- Business impact

## Lessons Learned
- What worked well
- What could be improved
- Recommendations for similar projects

## Conclusion
- Key takeaways
- Future improvements
- Applicability to other projects
"""

    def get_technical_guide_template(self):
        """Get technical guide template"""
        return """# [TECHNICAL TOPIC]: Complete Implementation Guide

## Introduction
- Problem this solves
- Target audience
- What readers will achieve

## Technical Background
- Core concepts
- Theoretical foundation
- Industry context

## Architecture and Design

### System Architecture
- High-level design
- Component interactions
- Data flow

### Design Decisions
- Trade-offs considered
- Rationale for choices
- Alternative approaches

## Implementation

### Setup and Configuration
- Environment requirements
- Installation steps
- Initial configuration

### Core Implementation
- Main functionality
- Code examples
- Configuration options

### Advanced Features
- Optional enhancements
- Performance optimizations
- Customization options

## Testing and Validation
- Testing strategies
- Validation procedures
- Quality assurance

## Deployment and Operations

### Deployment Process
- Deployment steps
- Environment considerations
- Rollback procedures

### Monitoring and Maintenance
- Key metrics to monitor
- Maintenance procedures
- Troubleshooting guide

## Performance and Scalability
- Performance characteristics
- Scalability considerations
- Optimization techniques

## Security Considerations
- Security best practices
- Vulnerability mitigation
- Compliance requirements

## Conclusion
- Summary of benefits
- Best practices recap
- Future considerations
"""