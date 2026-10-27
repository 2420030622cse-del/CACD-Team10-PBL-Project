import argparse
import json
import os
import re
import shutil
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import render_template

from ai.recommendation_engine import identify_aspects
from app import app
from simulator.rule_based import DEFAULT_RULES


METHODS = ('brute_force', 'dictionary', 'rule_based', 'hybrid', 'password_safety')
SIMULATION_METHODS = ('brute_force', 'dictionary', 'rule_based', 'hybrid')
RATINGS = {
    'security_strength': 0.0,
    'memorability': 0.0,
    'randomness': 0.0,
    'pattern_safety': 0.0,
    'typing_usability': 0.0,
    'overall_rating': 0.0,
}


def default_base_path():
    configured = os.environ.get('PAGES_BASE_PATH', '').strip()
    if configured:
        base = configured
    else:
        repository = os.environ.get('GITHUB_REPOSITORY', '')
        repo_name = repository.rsplit('/', 1)[-1]
        base = '/' if not repo_name or repo_name.endswith('.github.io') else f'/{repo_name}/'
    if not base.startswith('/'):
        base = f'/{base}'
    return base if base.endswith('/') else f'{base}/'


def static_route(url):
    parsed = urlsplit(url)
    page = parsed.path.strip('/')
    query = parse_qs(parsed.query)
    if page == 'static':
        return f'static/{parsed.path[len("/static/"):]}'
    if not page:
        return ''
    if page in ('configure', 'simulation'):
        method = query.get('method', ['brute_force'])[0]
        if method not in METHODS:
            method = 'brute_force'
        page = f'{page}/{method}'
    if page in ('attacks', 'configure', 'report'):
        return f'{page}/' + (f'?{parsed.query}' if parsed.query else '')
    if page.startswith(('configure/', 'simulation/')):
        return f'{page}/' + (f'?{parsed.query}' if parsed.query else '')
    return url.lstrip('/')


def rewrite_static_html(html, base_path):
    html = html.replace('<base href="/">', f'<base href="{base_path}">')

    def rewrite(match):
        attribute, value = match.group(1), match.group(2)
        if value.startswith('/static/'):
            value = static_route(value)
        elif value == '/' or value.startswith(('/attacks', '/configure', '/simulation', '/report')):
            value = static_route(value)
        return f'{attribute}="{value}"'

    return re.sub(r'\b(href|src)="([^"]*)"', rewrite, html)


def write_page(output, relative_path, template, path, **context):
    with app.test_request_context(path):
        html = render_template(template, **context)
    target = output / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding='utf-8')


def build(output, base_path, api_base_url):
    output.mkdir(parents=True, exist_ok=True)
    (output / '.nojekyll').touch()
    shutil.copytree(Path(app.root_path) / 'static', output / 'static', dirs_exist_ok=True)

    pages = [
        ('index.html', 'index.html', '/', {}),
        ('attacks/index.html', 'attacks.html', '/attacks', {}),
    ]
    for method in METHODS:
        pages.append((
            f'configure/{method}/index.html',
            'configure.html',
            f'/configure?method={method}',
            {'method': method, 'rule_ids': DEFAULT_RULES.get('PIN', []), 'max_rules': 2},
        ))
        if method in SIMULATION_METHODS:
            pages.append((
                f'simulation/{method}/index.html',
                'simulation.html',
                f'/simulation?method={method}',
                {
                    'method': method, 'ptype': 'PIN', 'search_space': 1_000_000,
                    'formatted_space': '1,000,000', 'worst_time': '2 hours 19 minutes',
                    'max_attempts': 0 if method == 'brute_force' else 1_000_000,
                    'max_time': 0 if method == 'brute_force' else 60,
                    'speed': 120, 'rule_ids': DEFAULT_RULES.get('PIN', []), 'max_rules': 2,
                },
            ))
    pages.extend([
        (
            'configure/index.html', 'configure.html', '/configure',
            {'method': 'brute_force', 'rule_ids': DEFAULT_RULES.get('PIN', []), 'max_rules': 2},
        ),
        (
            'report/index.html', 'report.html', '/report',
            {
                'password_len': 0, 'method': 'brute_force', 'ptype': 'PIN',
                'attempts': 0, 'time_taken': 0.0, 'speed': 0.0, 'found': False,
                'reason': 'limit_reached',
                'ratings': RATINGS, 'aspects': identify_aspects(RATINGS),
                'recommendation': 'Generating your report...', 'formatted_space': '—',
            },
        ),
    ])
    for relative_path, template, path, context in pages:
        write_page(output, relative_path, template, path, **context)

    for page in output.rglob('*.html'):
        html = rewrite_static_html(page.read_text(encoding='utf-8'), base_path)
        page.write_text(html, encoding='utf-8')
    config = {
        'API_BASE_URL': api_base_url.rstrip('/'),
        'APP_BASE_PATH': base_path,
        'IS_STATIC_BUILD': True,
    }
    (output / 'static' / 'js' / 'runtime-config.js').write_text(
        f'window.APP_CONFIG = {json.dumps(config)};\n',
        encoding='utf-8',
    )


def main():
    parser = argparse.ArgumentParser(description='Build the CyberForce app for GitHub Pages.')
    parser.add_argument('--output', type=Path, default=Path('site'))
    parser.add_argument('--base-path', default=default_base_path())
    parser.add_argument('--api-base-url', default=os.environ.get('API_BASE_URL', '').strip())
    args = parser.parse_args()
    if args.api_base_url and not args.api_base_url.startswith('https://'):
        parser.error('--api-base-url must use HTTPS.')
    if (not args.base_path.startswith('/') or args.base_path.startswith('//')
            or '\\' in args.base_path or '..' in args.base_path
            or '?' in args.base_path or '#' in args.base_path):
        parser.error('--base-path must be a safe site path such as /project/.')
    base_path = args.base_path if args.base_path.endswith('/') else f'{args.base_path}/'
    build(args.output.resolve(), base_path, args.api_base_url)
    print(f'Built GitHub Pages app at {args.output.resolve()} with base path {base_path}')


if __name__ == '__main__':
    main()
