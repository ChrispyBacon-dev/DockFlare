import os
import re
import markdown
from flask import Blueprint, render_template, current_app, abort
from flask_login import login_required

help_bp = Blueprint('help', __name__, template_folder='../templates')

def parse_docs_nav():
    """Parses the navigation.md file to build the navigation structure for the help pages."""
    nav_structure = []
    docs_path = os.path.join(current_app.root_path, 'templates', 'docs')
    home_md_path = os.path.join(docs_path, 'navigation.md')

    if not os.path.exists(home_md_path):
        current_app.logger.error(f"Help navigation file not found at {home_md_path}")
        return []

    with open(home_md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    link_regex = re.compile(r'\[([^\]]+)\]\(([^)]+\.md)\)')
    
    for line in lines:
        
        if line.startswith('*   '):
            item_text = line[4:].strip()
            
            
            if item_text.startswith('**') and not link_regex.search(item_text):
                category_name = item_text.replace('**', '').strip()
                category = {'name': category_name, 'is_category': True, 'children': []}
                nav_structure.append(category)
            
            else:
                match = link_regex.search(item_text)
                if match:
                    link_item = {'name': match.group(1), 'link': match.group(2)}
                    nav_structure.append(link_item)
        
        
        elif line.startswith('    *   '):
            if nav_structure and nav_structure[-1].get('is_category'):
                item_text = line[8:].strip()
                match = link_regex.search(item_text)
                if match:
                    child_item = {'name': match.group(1), 'link': match.group(2)}
                    nav_structure[-1]['children'].append(child_item)

    return nav_structure

@help_bp.route('/help')
@help_bp.route('/help/<path:page>')
@login_required
def help_page(page='Home.md'):
    """Renders a documentation page from a markdown file."""
    if not page.endswith('.md'):
        abort(404)

    docs_path = os.path.abspath(os.path.join(current_app.root_path, 'templates', 'docs'))
    file_path = os.path.abspath(os.path.join(docs_path, page))

    if not file_path.startswith(docs_path + os.sep) or not os.path.isfile(file_path):
        abort(404)

    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()


    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.toc',
        'markdown.extensions.meta',
        'markdown.extensions.nl2br',
        'pymdownx.superfences',
        'pymdownx.highlight',
        'pymdownx.tasklist',
        'pymdownx.tilde',
    ]
    extension_configs = {
        'pymdownx.highlight': {
            'use_pygments': True,
            'linenums': False
        },
        'pymdownx.superfences': {},
        'pymdownx.tasklist': {'custom_checkbox': True},
    }


    html_content = markdown.markdown(
        md_content,
        extensions=extensions,
        extension_configs=extension_configs,
        output_format='html5'
    )
    
    navigation = parse_docs_nav()

    title_match = re.search(r'^#\s+(.*)', md_content, re.MULTILINE)
    title = title_match.group(1) if title_match else page.replace('.md', '').replace('-', ' ')

    return render_template('help.html', 
                           title=title, 
                           content=html_content, 
                           navigation=navigation,
                           current_page=page)