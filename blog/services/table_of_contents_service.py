"""
Table of Contents Service for Blog Posts

This service provides functionality to automatically generate table of contents
for blog posts by extracting headings from HTML content and creating anchor links.
"""

import re
from bs4 import BeautifulSoup
from django.utils.text import slugify
from django.utils.html import format_html
from typing import List, Dict, Optional, Tuple


class TableOfContentsService:
    """Service class for generating table of contents from HTML content"""
    
    # Minimum number of headings required to show TOC
    MIN_HEADINGS_FOR_TOC = 3
    
    # Maximum depth for TOC (h1-h6)
    MAX_HEADING_DEPTH = 6
    
    # Heading tags to extract (in order of hierarchy)
    HEADING_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    @classmethod
    def generate_toc(cls, content: str, min_headings: int = None) -> Dict:
        """
        Generate table of contents from HTML content.
        
        Args:
            content: HTML content string
            min_headings: Minimum number of headings required (defaults to MIN_HEADINGS_FOR_TOC)
            
        Returns:
            Dictionary containing:
            - 'headings': List of heading dictionaries
            - 'content': Modified HTML content with anchor links
            - 'show_toc': Boolean indicating if TOC should be displayed
        """
        if not content:
            return {
                'headings': [],
                'content': content,
                'show_toc': False
            }
        
        min_headings = min_headings or cls.MIN_HEADINGS_FOR_TOC
        
        # Parse HTML content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract headings
        headings = cls.extract_headings(soup)
        
        # Check if we should show TOC
        show_toc = len(headings) >= min_headings
        
        if show_toc:
            # Add anchor links to headings
            modified_content = cls.add_anchor_links(soup, headings)
        else:
            modified_content = str(soup)
        
        return {
            'headings': headings,
            'content': modified_content,
            'show_toc': show_toc
        }
    
    @classmethod
    def extract_headings(cls, soup: BeautifulSoup) -> List[Dict]:
        """
        Extract headings from BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            List of heading dictionaries with text, level, and anchor
        """
        headings = []
        used_anchors = set()
        
        # Find all heading tags
        for heading_tag in soup.find_all(cls.HEADING_TAGS):
            # Get heading text (strip HTML tags)
            text = heading_tag.get_text().strip()
            
            if not text:
                continue
            
            # Get heading level (h1=1, h2=2, etc.)
            level = int(heading_tag.name[1])
            
            # Generate unique anchor
            anchor = cls.generate_unique_anchor(text, used_anchors)
            used_anchors.add(anchor)
            
            headings.append({
                'text': text,
                'level': level,
                'anchor': anchor,
                'element': heading_tag
            })
        
        return headings
    
    @classmethod
    def generate_unique_anchor(cls, text: str, used_anchors: set) -> str:
        """
        Generate a unique anchor ID from heading text.
        
        Args:
            text: Heading text
            used_anchors: Set of already used anchor IDs
            
        Returns:
            Unique anchor ID string
        """
        # Create base anchor from text
        base_anchor = slugify(text)
        
        # Ensure it's not empty
        if not base_anchor:
            base_anchor = 'heading'
        
        # Make it unique
        anchor = base_anchor
        counter = 1
        
        while anchor in used_anchors:
            anchor = f"{base_anchor}-{counter}"
            counter += 1
        
        return anchor
    
    @classmethod
    def add_anchor_links(cls, soup: BeautifulSoup, headings: List[Dict]) -> str:
        """
        Add anchor links to headings in the HTML content.
        
        Args:
            soup: BeautifulSoup parsed HTML
            headings: List of heading dictionaries
            
        Returns:
            Modified HTML content as string
        """
        for heading_data in headings:
            element = heading_data['element']
            anchor = heading_data['anchor']
            
            # Add ID attribute to heading
            element['id'] = anchor
            
            # Add anchor link icon (optional)
            anchor_link = soup.new_tag('a', href=f'#{anchor}', **{
                'class': 'heading-anchor',
                'aria-label': f'Link to {heading_data["text"]}'
            })
            anchor_link.string = '#'
            
            # Insert anchor link at the beginning of heading
            element.insert(0, anchor_link)
        
        return str(soup)
    
    @classmethod
    def build_toc_html(cls, headings: List[Dict], max_depth: int = None) -> str:
        """
        Build HTML structure for table of contents.
        
        Args:
            headings: List of heading dictionaries
            max_depth: Maximum heading depth to include
            
        Returns:
            HTML string for table of contents
        """
        if not headings:
            return ''
        
        max_depth = max_depth or cls.MAX_HEADING_DEPTH
        
        # Filter headings by max depth
        filtered_headings = [h for h in headings if h['level'] <= max_depth]
        
        if not filtered_headings:
            return ''
        
        # Build nested structure
        toc_html = ['<nav class="table-of-contents" role="navigation" aria-label="Table of Contents">']
        toc_html.append('<div class="toc-header">')
        toc_html.append('<h3 class="toc-title"><i class="fas fa-list"></i> Table of Contents</h3>')
        toc_html.append('<button class="toc-toggle" aria-label="Toggle table of contents">')
        toc_html.append('<i class="fas fa-chevron-up"></i>')
        toc_html.append('</button>')
        toc_html.append('</div>')
        
        toc_html.append('<ol class="toc-list">')
        
        current_level = filtered_headings[0]['level']
        level_stack = [current_level]
        
        for heading in filtered_headings:
            level = heading['level']
            text = heading['text']
            anchor = heading['anchor']
            
            # Handle level changes
            if level > current_level:
                # Going deeper - open new nested list
                for _ in range(level - current_level):
                    toc_html.append('<li><ol class="toc-sublist">')
                    level_stack.append(level)
            elif level < current_level:
                # Going up - close nested lists
                levels_to_close = current_level - level
                for _ in range(levels_to_close):
                    toc_html.append('</ol></li>')
                    if level_stack:
                        level_stack.pop()
            
            # Add the heading item
            toc_html.append(f'<li class="toc-item toc-level-{level}">')
            toc_html.append(f'<a href="#{anchor}" class="toc-link" data-level="{level}">')
            toc_html.append(f'<span class="toc-text">{text}</span>')
            toc_html.append('</a>')
            toc_html.append('</li>')
            
            current_level = level
        
        # Close any remaining open lists
        while len(level_stack) > 1:
            toc_html.append('</ol></li>')
            level_stack.pop()
        
        toc_html.append('</ol>')
        toc_html.append('</nav>')
        
        return ''.join(toc_html)
    
    @classmethod
    def should_show_toc(cls, content: str, min_headings: int = None) -> bool:
        """
        Determine if table of contents should be shown for given content.
        
        Args:
            content: HTML content string
            min_headings: Minimum number of headings required
            
        Returns:
            Boolean indicating if TOC should be displayed
        """
        if not content:
            return False
        
        min_headings = min_headings or cls.MIN_HEADINGS_FOR_TOC
        
        # Quick check using regex (faster than full parsing)
        heading_pattern = r'<h[1-6][^>]*>.*?</h[1-6]>'
        headings = re.findall(heading_pattern, content, re.IGNORECASE | re.DOTALL)
        
        return len(headings) >= min_headings
    
    @classmethod
    def get_reading_time_by_sections(cls, content: str, headings: List[Dict]) -> Dict[str, int]:
        """
        Calculate reading time for each section of the content.
        
        Args:
            content: HTML content string
            headings: List of heading dictionaries
            
        Returns:
            Dictionary mapping section anchors to reading times in minutes
        """
        if not headings:
            return {}
        
        soup = BeautifulSoup(content, 'html.parser')
        section_times = {}
        
        # Average reading speed (words per minute)
        WPM = 200
        
        for i, heading in enumerate(headings):
            # Find content between this heading and the next
            current_element = heading['element']
            
            # Get next heading element if exists
            next_element = headings[i + 1]['element'] if i + 1 < len(headings) else None
            
            # Extract text content for this section
            section_text = cls._extract_section_text(current_element, next_element)
            
            # Calculate reading time
            word_count = len(section_text.split())
            reading_time = max(1, round(word_count / WPM))
            
            section_times[heading['anchor']] = reading_time
        
        return section_times
    
    @classmethod
    def _extract_section_text(cls, start_element, end_element) -> str:
        """
        Extract text content between two elements.
        
        Args:
            start_element: Starting element (heading)
            end_element: Ending element (next heading) or None
            
        Returns:
            Text content of the section
        """
        text_parts = []
        current = start_element.next_sibling
        
        while current and current != end_element:
            if hasattr(current, 'get_text'):
                text_parts.append(current.get_text())
            elif isinstance(current, str):
                text_parts.append(current.strip())
            current = current.next_sibling
        
        return ' '.join(text_parts)
    
    @classmethod
    def generate_toc_data_for_template(cls, post) -> Dict:
        """
        Generate table of contents data specifically for Django templates.
        
        Args:
            post: Blog post model instance
            
        Returns:
            Dictionary with TOC data for template context
        """
        if not post.table_of_contents or not post.content:
            return {
                'show_toc': False,
                'toc_html': '',
                'headings': [],
                'content': post.content
            }
        
        toc_data = cls.generate_toc(post.content)
        
        if toc_data['show_toc']:
            toc_html = cls.build_toc_html(toc_data['headings'])
            
            # Add reading times for sections
            section_times = cls.get_reading_time_by_sections(
                post.content, 
                toc_data['headings']
            )
            
            # Add reading times to headings
            for heading in toc_data['headings']:
                heading['reading_time'] = section_times.get(heading['anchor'], 1)
            
            return {
                'show_toc': True,
                'toc_html': toc_html,
                'headings': toc_data['headings'],
                'content': toc_data['content'],
                'section_reading_times': section_times
            }
        
        return {
            'show_toc': False,
            'toc_html': '',
            'headings': [],
            'content': post.content
        }