#!/usr/bin/env python3
"""Synchronize existing provincial directories from explicit, reviewed associations."""
import argparse
from collections import Counter
from datetime import date
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'scripts/province-insights.json'


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate province registry key: ' + key)
        result[key] = value
    return result


def load(root):
    data = json.loads((root / CONFIG).read_text(), object_pairs_hook=unique_keys)
    topics, articles, legacy = data['topics'], data['articles'], data['legacy_unclassified']
    if len(legacy) != len(set(legacy)) or set(legacy) & set(articles):
        raise ValueError('Duplicate or conflicting historical province classification')
    for topic, path in topics.items():
        if not re.fullmatch(r'src/[a-z0-9-]+-insights\.(?:html|njk)', path):
            raise ValueError('Invalid province directory path: ' + str(path))
        if not (root / path).is_file():
            raise ValueError('Province directory does not exist; do not create it: ' + path)
    for route, record in articles.items():
        if not re.fullmatch(r'/articles/[a-z0-9-]+', route):
            raise ValueError('Invalid province article route: ' + route)
        memberships = record.get('topics')
        if not isinstance(memberships, list) or len(memberships) != len(set(memberships)):
            raise ValueError('Invalid or duplicate province association: ' + route)
        if any(topic not in topics for topic in memberships):
            raise ValueError('Unknown province association; confirmation required: ' + route)
        value = record.get('published', '')
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('Invalid publication date: ' + route)
    return data


def review_warnings(root):
    try:
        pending = load(root)['legacy_unclassified']
    except (OSError, ValueError, KeyError, TypeError):
        return []  # validate() separately reports invalid configuration as a failure.
    return ([f'Province Insights: {len(pending)} historical articles pending association review '
             '(nonblocking); see scripts/province-insights.json legacy_unclassified'] if pending else [])


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.routes = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get('href', '')
        if tag == 'a' and href.startswith('/articles/'):
            self.routes.append(href.removesuffix('.html'))


def directory(text):
    matches = list(re.finditer(r'<ul\b[^>]*class="article-directory"[^>]*>(.*?)</ul>', text, re.S))
    if len(matches) != 1:
        raise ValueError('Expected exactly one existing article-directory')
    return matches[0]


def validate(root, article_routes):
    errors = []
    try:
        data = load(root)
        actual = set(article_routes)
        registered = set(data['articles']) | set(data['legacy_unclassified'])
        for route in sorted(actual - registered):
            errors.append('Province association unresolved: ' + route +
                          '; explicitly register topics (or [] for non-provincial); ask for confirmation if unclear')
        for route in sorted(registered - actual):
            errors.append('Province registry references missing article: ' + route)
        for topic, source in data['topics'].items():
            output = root / '_site' / (Path(source).stem + '.html')
            body = directory(output.read_text()).group(1)
            routes = Links(body).routes
            counts = Counter(routes)
            expected = {r for r, rec in data['articles'].items() if topic in rec['topics']}
            for route in sorted(expected - set(routes)):
                errors.append('Province Insights missing entry: ' + topic + ' ' + route)
            for route in sorted(set(routes) - expected):
                errors.append('Province Insights unconfirmed association: ' + topic + ' ' + route)
            for route, count in counts.items():
                if count > 1:
                    errors.append('Province Insights duplicate entry: ' + topic + ' ' + route)
            dated = [data['articles'][r]['published'] for r in routes if r in expected]
            if dated != sorted(dated, reverse=True):
                errors.append('Province Insights not ordered by publication date: ' + topic)
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append('Province Insights configuration error: ' + str(error))
    return errors


def card(route, record, topic):
    title, english, summary = (record.get(k) for k in ('title', 'title_en', 'description'))
    if not all(isinstance(value, str) and value.strip() for value in (title, english, summary)):
        raise ValueError('Missing reviewed card title/title_en/description: ' + route)
    note_class = 'summary' if topic == 'ontario' else 'article-note'
    return ('\n<!-- ' + record['published'] + ' -->\n<li>\n'
            '  <span class="title-zh">' + escape(title) + '</span>\n'
            '  <span class="title-en">' + escape(english) + '</span>\n'
            '  <span class="' + note_class + '">' + escape(record['published'] + ' · ' + summary) + '</span>\n'
            '  <a class="read-more" href="' + route + '">Read Article | 阅读全文 →</a>\n</li>')


def synchronize(root):
    data = load(root)
    proposed = {}
    for topic, source in data['topics'].items():
        path = root / source
        text = path.read_text()
        match = directory(text)
        body = match.group(1)
        expected = {r: rec for r, rec in data['articles'].items() if topic in rec['topics']}
        chunks, placeholders, last = {}, [], 0
        for item in re.finditer(r'<li\b[^>]*>.*?</li>', body, re.S):
            routes = Links(item.group(0)).routes
            chunk = body[last:item.end()]
            last = item.end()
            if not routes:
                placeholders.append(chunk)
                continue
            if len(routes) != 1 or routes[0] in chunks or routes[0] not in expected:
                raise ValueError('Duplicate/unconfirmed directory entry; confirmation required: ' + source)
            chunks[routes[0]] = chunk
        missing = set(expected) - set(chunks)
        ordered = sorted(expected, key=lambda r: (expected[r]['published'], r), reverse=True)
        if not missing and list(chunks) == ordered:
            continue
        # Keep all existing card bytes and links. Only insert missing cards and reorder blocks.
        for route in missing:
            chunks[route] = card(route, expected[route], topic)
        if placeholders and chunks:
            if not all('No articles have been published' in block for block in placeholders):
                raise ValueError('Unknown non-article directory content; confirmation required: ' + source)
        replacement = ''.join(chunks[r] for r in ordered) + body[last:]
        proposed[path] = text[:match.start(1)] + replacement + text[match.end(1):]
    # Validate all proposals before writing. Never rewrite protected hashes automatically.
    for path, text in proposed.items():
        path.write_text(text)
    return [str(path.relative_to(root)) for path in proposed]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Update existing directory lists; review diffs and approved hashes afterwards')
    args = parser.parse_args()
    if not args.write:
        parser.error('Use --write only during an authorized local publishing task; builds check but never repair lists')
    try:
        changed = synchronize(ROOT)
        print('Updated province directories: ' + (', '.join(changed) if changed else 'none'))
        if changed:
            print('Review the diff, then update ONLY approved seo-baseline.json entries before checked build.')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
