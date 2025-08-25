# LinkedIn Hashtag Configuration Guide

## Overview

The LinkedIn hashtag configuration system allows you to automatically generate relevant hashtags for your LinkedIn posts based on blog post content, tags, and categories. This guide covers configuration options, best practices, and examples.

## Configuration Options

### Basic Hashtag Settings

#### Enable Hashtags
- **Field**: `enable_hashtags`
- **Type**: Boolean
- **Default**: `True`
- **Description**: Master switch to enable/disable hashtag generation for all LinkedIn posts

#### Maximum Hashtags
- **Field**: `max_hashtags`
- **Type**: Integer (0-30)
- **Default**: `5`
- **Description**: Maximum number of hashtags to include in each LinkedIn post
- **Best Practice**: LinkedIn recommends 3-5 hashtags for optimal reach

### Advanced Hashtag Configuration

#### Custom Hashtag Rules
- **Field**: `custom_hashtag_rules`
- **Type**: JSON Object
- **Description**: Define category-specific hashtag rules with required and suggested hashtags

**Example Configuration**:
```json
{
  "technology": {
    "required_hashtags": ["#Tech", "#Programming"],
    "suggested_hashtags": ["#Development", "#Coding", "#Software"],
    "max_hashtags": 4,
    "priority": 1
  },
  "tutorial": {
    "required_hashtags": ["#Tutorial", "#HowTo"],
    "suggested_hashtags": ["#Learning", "#Guide", "#Tips"],
    "max_hashtags": 3,
    "priority": 2
  },
  "ai": {
    "required_hashtags": ["#AI", "#MachineLearning"],
    "suggested_hashtags": ["#DeepLearning", "#DataScience", "#Innovation"],
    "max_hashtags": 5,
    "priority": 1
  }
}
```

**Rule Structure**:
- `required_hashtags`: Always included if space allows
- `suggested_hashtags`: Included if space remains after required hashtags
- `max_hashtags`: Override global max for this category
- `priority`: Higher priority categories get preference (1 = highest)

#### Hashtag Blacklist
- **Field**: `hashtag_blacklist`
- **Type**: JSON Array
- **Description**: Words/phrases that should never become hashtags

**Example Configuration**:
```json
[
  "spam",
  "clickbait",
  "urgent",
  "breaking",
  "exclusive",
  "secret",
  "hack",
  "trick"
]
```

## Hashtag Generation Process

### Generation Sources (in priority order)

1. **Custom Rules** (Highest Priority)
   - Uses category-specific required hashtags
   - Applies suggested hashtags if space allows

2. **Post Tags** (High Priority)
   - Converts blog post tags to hashtags
   - Validates and formats each tag

3. **Post Categories** (Medium Priority)
   - Uses category names as hashtags
   - Applies category-specific rules if defined

4. **Content Analysis** (Lower Priority)
   - Extracts keywords from title and excerpt
   - Uses frequency analysis for relevance

### Hashtag Validation Rules

All generated hashtags must meet LinkedIn's requirements:
- Start with a letter or underscore
- Contain only letters, numbers, and underscores
- Be between 1-100 characters long
- Not be in the blacklist
- Follow proper formatting (#hashtag)

## Configuration Examples

### Example 1: Technology Blog
```json
{
  "enable_hashtags": true,
  "max_hashtags": 5,
  "custom_hashtag_rules": {
    "programming": {
      "required_hashtags": ["#Programming", "#Code"],
      "suggested_hashtags": ["#Development", "#Software", "#Tech"],
      "max_hashtags": 4
    },
    "web-development": {
      "required_hashtags": ["#WebDev", "#Frontend"],
      "suggested_hashtags": ["#JavaScript", "#React", "#CSS"],
      "max_hashtags": 5
    },
    "devops": {
      "required_hashtags": ["#DevOps", "#CloudComputing"],
      "suggested_hashtags": ["#AWS", "#Docker", "#Kubernetes"],
      "max_hashtags": 4
    }
  },
  "hashtag_blacklist": ["hack", "trick", "secret", "clickbait"]
}
```

### Example 2: Business Blog
```json
{
  "enable_hashtags": true,
  "max_hashtags": 4,
  "custom_hashtag_rules": {
    "marketing": {
      "required_hashtags": ["#Marketing", "#DigitalMarketing"],
      "suggested_hashtags": ["#SEO", "#ContentMarketing", "#SocialMedia"],
      "max_hashtags": 4
    },
    "leadership": {
      "required_hashtags": ["#Leadership", "#Management"],
      "suggested_hashtags": ["#TeamBuilding", "#Strategy", "#Growth"],
      "max_hashtags": 3
    },
    "entrepreneurship": {
      "required_hashtags": ["#Entrepreneurship", "#Startup"],
      "suggested_hashtags": ["#Innovation", "#Business", "#Success"],
      "max_hashtags": 4
    }
  },
  "hashtag_blacklist": ["urgent", "breaking", "exclusive"]
}
```

### Example 3: Educational Content
```json
{
  "enable_hashtags": true,
  "max_hashtags": 6,
  "custom_hashtag_rules": {
    "tutorial": {
      "required_hashtags": ["#Tutorial", "#Learning"],
      "suggested_hashtags": ["#Education", "#HowTo", "#Guide"],
      "max_hashtags": 5
    },
    "course": {
      "required_hashtags": ["#OnlineLearning", "#Course"],
      "suggested_hashtags": ["#Education", "#Skills", "#Training"],
      "max_hashtags": 4
    },
    "tips": {
      "required_hashtags": ["#Tips", "#Advice"],
      "suggested_hashtags": ["#BestPractices", "#Learning", "#Growth"],
      "max_hashtags": 4
    }
  },
  "hashtag_blacklist": ["spam", "clickbait"]
}
```

## Best Practices

### Hashtag Selection
1. **Relevance First**: Ensure hashtags are directly related to content
2. **Mix Popular and Niche**: Combine broad hashtags (#Technology) with specific ones (#ReactJS)
3. **Avoid Overuse**: Don't use the same hashtags for every post
4. **Industry Standards**: Use hashtags common in your industry

### LinkedIn-Specific Guidelines
1. **Optimal Count**: Use 3-5 hashtags per post
2. **Placement**: Add hashtags at the end of your post
3. **Capitalization**: Use camelCase for readability (#WebDevelopment)
4. **Avoid Spam**: Don't use irrelevant or trending hashtags

### Configuration Management
1. **Regular Review**: Update rules based on performance
2. **Category Alignment**: Ensure rules match your content categories
3. **Blacklist Maintenance**: Keep blacklist updated with spam terms
4. **Testing**: Use preview functionality to test configurations

## Troubleshooting

### Common Issues

#### No Hashtags Generated
**Possible Causes**:
- `enable_hashtags` is set to `false`
- `max_hashtags` is set to `0`
- All generated hashtags are blacklisted
- Post has no tags, categories, or analyzable content

**Solutions**:
- Check basic configuration settings
- Review blacklist for overly broad terms
- Add fallback hashtags in custom rules

#### Too Few Hashtags
**Possible Causes**:
- Restrictive blacklist
- Invalid hashtag formats
- Limited content for analysis

**Solutions**:
- Review and refine blacklist
- Add suggested hashtags to custom rules
- Ensure post has tags or categories

#### Irrelevant Hashtags
**Possible Causes**:
- Relying too heavily on content analysis
- Generic category names
- Missing custom rules

**Solutions**:
- Define custom rules for important categories
- Use more specific post tags
- Refine content analysis keywords

### Validation Errors

#### Invalid JSON Format
```
Error: Invalid JSON format: Expecting ',' delimiter
```
**Solution**: Validate JSON syntax using online tools or admin validation

#### Invalid Hashtag Format
```
Error: Invalid hashtag '#123invalid' in required_hashtags
```
**Solution**: Ensure hashtags start with letter/underscore and contain only valid characters

#### Exceeding Limits
```
Error: max_hashtags for 'technology' must be between 0 and 30
```
**Solution**: Adjust max_hashtags values to be within acceptable range

## Monitoring and Analytics

### Logging
The system logs hashtag generation activities:
- Generation success/failure
- Source of hashtags (tags, categories, content)
- Validation errors
- Performance metrics

### Metrics Tracked
- Hashtag generation time
- Success/failure rates
- Source distribution
- Blacklist filter effectiveness

### Performance Optimization
- Hashtag generation is cached per post
- Configuration is loaded once per session
- Validation is performed efficiently
- Fallback mechanisms prevent failures

## API Reference

### HashtagGenerator Class

#### Methods

##### `generate_hashtags(blog_post, max_count=None)`
Generate hashtags for a blog post using all available sources.

**Parameters**:
- `blog_post`: Blog Post model instance
- `max_count`: Maximum hashtags to generate (overrides config)

**Returns**: List of formatted hashtags

**Example**:
```python
from blog.services.linkedin_content_formatter import HashtagGenerator

generator = HashtagGenerator(config)
hashtags = generator.generate_hashtags(blog_post, max_count=5)
# Returns: ['#Technology', '#Programming', '#WebDev']
```

##### `generate_from_tags(blog_post, max_count)`
Generate hashtags from blog post tags.

##### `generate_from_categories(blog_post, max_count)`
Generate hashtags from blog post categories.

##### `generate_from_content(blog_post, max_count)`
Generate hashtags from blog post content analysis.

##### `validate_hashtag(hashtag)`
Validate hashtag format according to LinkedIn standards.

##### `format_hashtag(text)`
Format text as a proper hashtag.

### LinkedInConfig Model

#### Methods

##### `get_hashtag_config()`
Get hashtag configuration as dictionary.

**Returns**:
```python
{
    'enable_hashtags': True,
    'max_hashtags': 5,
    'custom_hashtag_rules': {...},
    'hashtag_blacklist': [...]
}
```

##### `should_include_hashtags(blog_post=None)`
Determine if hashtags should be included for a specific post.

**Parameters**:
- `blog_post`: Blog Post instance (optional)

**Returns**: Boolean indicating whether to include hashtags