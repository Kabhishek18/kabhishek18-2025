# Enhanced Sitemap Implementation

## Overview
The sitemap generation has been upgraded from a basic single-page sitemap to a comprehensive, SEO-optimized sitemap system that includes categories and blog posts with intelligent prioritization and change frequency detection.

## Features Implemented

### 1. Comprehensive URL Coverage
- **Homepage**: Priority 1.0, daily updates
- **Blog homepage**: Priority 0.9, daily updates  
- **Categories**: Priority 0.7, weekly updates
- **Tags**: Priority 0.6, weekly updates (only tags with published posts)
- **Blog posts**: Priority 0.6-0.8 (higher for featured posts), dynamic change frequency

### 2. Intelligent Change Frequency
Blog posts automatically get appropriate change frequencies based on age:
- **New posts (< 7 days)**: Daily updates
- **Recent posts (< 30 days)**: Weekly updates  
- **Older posts**: Monthly updates

### 3. Priority System
- Featured blog posts get higher priority (0.8 vs 0.6)
- Categories get medium priority (0.7)
- Tags get lower priority (0.6)
- Homepage gets maximum priority (1.0)

### 4. Two Generation Modes

#### Standard Sitemap (`--sitemap`)
Generates a single `sitemap.xml` file with all URLs. Suitable for smaller sites.

#### Sitemap Index (`--sitemap-index`)
Generates separate sitemap files for better organization and performance:
- `sitemap_main.xml` - Homepage and main pages
- `sitemap_categories.xml` - All blog categories
- `sitemap_tags.xml` - All tags with published posts
- `sitemap_posts.xml` - All published blog posts
- `sitemap_index.xml` - Index file referencing all sitemaps

### 5. Smart robots.txt Integration
The robots.txt file automatically references the appropriate sitemap:
- Uses `sitemap_index.xml` if it exists
- Falls back to `sitemap.xml` otherwise

## Usage

### Generate Standard Sitemap
```bash
python manage.py update_site_files --sitemap --verbose
```

### Generate Sitemap Index (Recommended for larger sites)
```bash
python manage.py update_site_files --sitemap-index --verbose
```

### Update All Files
```bash
python manage.py update_site_files --all --verbose
```

## Benefits

1. **SEO Optimization**: Proper priorities and change frequencies help search engines understand content importance
2. **Performance**: Separate sitemap files prevent large single files that could slow down crawling
3. **Scalability**: Sitemap index approach scales well with growing content
4. **Automation**: Integrates with existing Celery task system for automatic updates
5. **Flexibility**: Two modes to suit different site sizes and requirements

## Technical Details

### Database Queries Optimized
- Uses `select_related()` and `prefetch_related()` where appropriate
- Filters only published content
- Orders by update time for better cache efficiency

### File Structure
All sitemap files are generated in the project root directory and are accessible via direct URLs:
- `/sitemap.xml` or `/sitemap_index.xml`
- `/sitemap_main.xml`
- `/sitemap_categories.xml`
- `/sitemap_tags.xml`
- `/sitemap_posts.xml`

### Configuration
Sitemap generation is controlled by the `SiteFilesConfig` model:
- `site_url`: Base URL for all sitemap entries
- `update_sitemap`: Enable/disable automatic sitemap updates
- `sitemap_path`: Custom path for the main sitemap file

## Migration from Basic Sitemap

The enhanced sitemap is backward compatible. Existing `sitemap.xml` files will be updated with the new comprehensive structure. For larger sites, consider switching to the sitemap index approach using the `--sitemap-index` flag.