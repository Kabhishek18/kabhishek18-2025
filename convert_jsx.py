import re

with open('portfolio/src/app/page.tsx', 'r') as f:
    content = f.read()

# Extract what's inside return (<> ... </>)
# Find the start of the return statement
start_idx = content.find('return (')
if start_idx != -1:
    content = content[start_idx:]
    # Match everything between <> and </>
    match = re.search(r'<>(.*?)</>', content, re.DOTALL)
    if match:
        content = match.group(1).strip()

# Replace className with class
content = content.replace('className=', 'class=')

# Replace htmlFor with for
content = content.replace('htmlFor=', 'for=')

# Replace <Link ...> with <a ...>
content = re.sub(r'<Link\b', '<a', content)
content = re.sub(r'</Link>', '</a>', content)

# Remove the {`//`} and replace with //
content = content.replace('{`//`}', '//')

# Replace {/* ... */} with <!-- ... -->
content = re.sub(r'\{\/\*([^\*]*)\*\/\}\n?', r'<!--\1-->\n', content)

# Now, read index.html
with open('templates/index.html', 'r') as f:
    index_html = f.read()

# Replace from {% block navbar %} to the end
start_navbar = index_html.find('{% block navbar %}')

new_index = index_html[:start_navbar] + """{% block navbar %}
{% endblock navbar %}

{% block content %}
""" + content + """
{% endblock content %}
"""

with open('templates/index.html', 'w') as f:
    f.write(new_index)

print("Successfully updated index.html!")
