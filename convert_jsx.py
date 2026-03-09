import re

def convert_tsx_to_django(src_path, dest_path, include_github_script=False):
    with open(src_path, 'r') as f:
        content = f.read()

    # Extract what's inside return (...) -> starting with <div or <>
    start_idx = content.find('return (')
    if start_idx != -1:
        content = content[start_idx:]
        
        # We need a robust match for the JSX inside the return. 
        # Usually it starts with <div or <>
        match = re.search(r'return\s*\(\s*(<.*)</>', content, re.DOTALL)
        if match:
            content = match.group(1) + "</>"
        else:
            match = re.search(r'return\s*\(\s*(<.*>)\s*\);', content, re.DOTALL)
            if match:
                content = match.group(1)

    # Clean up outer tags if it's fragments
    if content.startswith('<>') and content.endswith('</>'):
        content = content[2:-3].strip()

    # Replace className with class
    content = content.replace('className=', 'class=')

    # Replace htmlFor with for
    content = content.replace('htmlFor=', 'for=')

    # Replace <Link ...> with <a ...>
    content = re.sub(r'<Link\b', '<a', content)
    content = re.sub(r'</Link>', '</a>', content)

    # Remove Javascript comment braces
    content = content.replace('{`//`}', '//')

    # Replace {/* ... */} with <!-- ... -->
    content = re.sub(r'\{\/\*([^\*]*)\*\/\}\n?', r'<!--\1-->\n', content)
    
    # Remove next/image <Image components and replace with <img>
    content = re.sub(r'<Image([^>]*)\s*/?>', r'<img\1>', content)
    content = content.replace('fill', '') # crude fix for next/image fill prop

    # Convert React style={{height: 'X%'}} to HTML style="height: X%;"
    content = re.sub(r'style=\{\{\s*height:\s*\'([^\']+)\'\s*\}\}', r'style="height: \1;"', content)

    # Now, read destination html
    with open(dest_path, 'r') as f:
        html_content = f.read()

    # Replace from {% block navbar %} to the end
    start_navbar = html_content.find('{% block navbar %}')
    if start_navbar != -1:
        new_html = html_content[:start_navbar] + "{% block navbar %}\n{% endblock navbar %}\n\n{% block content %}\n" + content + "\n"
        
        if include_github_script:
            new_html += '<script src="/static/github_fetcher.js"></script>\n'
            
        new_html += "{% endblock content %}\n"

        with open(dest_path, 'w') as f:
            f.write(new_html)

print("Processing files...")
convert_tsx_to_django('portfolio/src/app/page.tsx', 'templates/index.html', include_github_script=True)
convert_tsx_to_django('portfolio/src/app/contact/page.tsx', 'templates/contact.html', include_github_script=False)
convert_tsx_to_django('portfolio/src/app/logs/page.tsx', 'templates/logs.html', include_github_script=False)
convert_tsx_to_django('portfolio/src/app/web_apps/page.tsx', 'templates/web_apps.html', include_github_script=False)
convert_tsx_to_django('portfolio/src/app/config/page.tsx', 'templates/config.html', include_github_script=False)
convert_tsx_to_django('portfolio/src/app/400/page.tsx', 'templates/400.html', include_github_script=False)
convert_tsx_to_django('portfolio/src/app/500/page.tsx', 'templates/500.html', include_github_script=False)
print("Successfully generated Django templates!")
