#!/usr/bin/env python3
"""Add metadata front matter to all agent .md files.

Adds author, contributors, version, source, and division fields
to the YAML front matter of each agent file.
"""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {'examples', 'strategy', 'integrations', '.github', 'scripts'}
SKIP_FILES = {'README.md', 'CONTRIBUTING.md', 'CONTRIBUTING_zh-CN.md', 'LICENSE', 'EXECUTIVE-BRIEF.md', 'QUICKSTART.md'}

# GitHub username mapping (git name -> GitHub handle where known)
GITHUB_HANDLES = {
    'Michael Sitarzewski': 'msitarzewski',
    'Matt Bernier': 'mattbernier',
    'Claude': 'anthropic-claude',
    'ryuketsukami': 'ryuketsukami',
    'jiangnan': 'jiangnan',
    'KienBM ubuntu': 'KienBM',
    'Toni Defez': 'ToniDefez',
    'John Williams': 'JohnWilliams',
    'heyrich': 'heyrich',
    'Saravi': 'Saravi',
    'Spencer Poisseroux': 'SpencerPoisseroux',
    'DKFuH': 'DKFuH',
    'PamvInf': 'PamvInf',
    'Rovey': 'Rovey',
    'GaelicThunder': 'GaelicThunder',
    'Sebastien Tang': 'SebastienTang',
    'Travis Sanford': 'TravisSanford',
    'Benji': 'Benji',
    'sam123': 'sam123',
    'hobostay': 'hobostay',
    'Subhodip': 'Subhodip',
    'Meghan': 'MeghanBao',
    'dreynow': 'dreynow',
    'knuckles-stack': 'knuckles-stack',
    'nameforyou': 'nameforyou',
    'bkblocksolutions-rgb': 'bkblocksolutions-rgb',
    'Shiven Garia': 'Shiven0504',
    'itlasso-drupal11': 'itlasso',
    'Aryan Verma': 'AryanVerma',
    'Rachamim Kennard': 'RachamimKennard',
    'Fayzan Malik': 'FayzanMalik',
    'José A. Cordón': 'JoseACordón',
    'Aditya-Ranjan1234': 'Aditya-Ranjan1234',
    'JosephChomboM': 'JosephChomboM',
    'BitmanAlan': 'BitmanAlan',
    'Javier Garcia Air': 'JavierGarciaAir',
    'juancarlos.cavero': 'juancarlos-cavero',
    'Mihajlo [Misa] Nikolic': 'MihajloNikolic',
    '4shil': '4shil',
}


def get_original_author(filepath):
    """Get the original author of a file from git log."""
    rel = os.path.relpath(filepath, REPO_ROOT)
    result = subprocess.run(
        ['git', 'log', '--diff-filter=A', '--format=%an', '--', rel],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    authors = result.stdout.strip().split('\n')
    return authors[-1] if authors and authors[-1] else 'Unknown'


def get_all_contributors(filepath):
    """Get all unique contributors to a file."""
    rel = os.path.relpath(filepath, REPO_ROOT)
    result = subprocess.run(
        ['git', 'log', '--format=%an', '--', rel],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    names = result.stdout.strip().split('\n')
    seen = set()
    unique = []
    for name in names:
        name = name.strip()
        if name and name not in seen:
            seen.add(name)
            unique.append(name)
    return unique


def get_division(filepath):
    """Derive the division/category from the file path."""
    rel = os.path.relpath(filepath, REPO_ROOT)
    parts = rel.split(os.sep)
    if len(parts) == 1:
        return 'root'
    return parts[0]


def get_source(filepath, author):
    """Determine the source: upstream, fork, or community."""
    if author == 'Matt Bernier':
        return 'bernierllc/agency-agents'
    return 'msitarzewski/agency-agents'


def to_github_handle(name):
    """Convert a git author name to a GitHub handle if known."""
    return GITHUB_HANDLES.get(name, name)


def parse_front_matter(content):
    """Parse existing YAML front matter. Returns (front_matter_dict, body, had_frontmatter)."""
    if not content.startswith('---'):
        return {}, content, False

    # Find the closing ---
    end = content.find('---', 3)
    if end == -1:
        return {}, content, False

    fm_text = content[3:end].strip()
    body = content[end + 3:].lstrip('\n')

    # Simple YAML parsing (handles the fields we care about)
    fm = {}
    current_key = None
    current_val_lines = []

    for line in fm_text.split('\n'):
        # Check if this is a new key
        match = re.match(r'^(\w[\w-]*)\s*:\s*(.*)', line)
        if match:
            # Save previous key
            if current_key:
                val = '\n'.join(current_val_lines).strip()
                fm[current_key] = val
            current_key = match.group(1)
            current_val_lines = [match.group(2)]
        elif current_key:
            current_val_lines.append(line)

    if current_key:
        val = '\n'.join(current_val_lines).strip()
        fm[current_key] = val

    return fm, body, True


def build_front_matter(fm):
    """Build YAML front matter string from dict, preserving field order."""
    # Desired field order
    order = ['name', 'description', 'version', 'author', 'contributors', 'source', 'division', 'color', 'emoji', 'tools']
    lines = ['---']

    for key in order:
        if key not in fm:
            continue
        val = fm[key]
        if key == 'description' and ('\n' in val or len(val) > 100):
            # Use > for long descriptions
            if val.startswith('>\n') or val.startswith('>'):
                lines.append(f'{key}: >')
                # Strip the > prefix and indent
                desc = val.lstrip('>').strip()
                for dline in desc.split('\n'):
                    lines.append(f'  {dline.strip()}')
            else:
                lines.append(f'{key}: >')
                for dline in val.split('\n'):
                    lines.append(f'  {dline.strip()}')
        elif key == 'contributors':
            lines.append(f'{key}:')
            # Parse contributor list
            contribs = val if isinstance(val, list) else [c.strip() for c in val.split(',') if c.strip()]
            for c in contribs:
                lines.append(f'  - "{c}"')
        elif key in ('description', 'name') and ('"' in str(val) or ':' in str(val)):
            lines.append(f'{key}: "{val}"')
        else:
            lines.append(f'{key}: {val}')

    # Any remaining keys not in order
    for key in fm:
        if key not in order:
            lines.append(f'{key}: {fm[key]}')

    lines.append('---')
    return '\n'.join(lines)


def process_file(filepath):
    """Add metadata to a single agent file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fm, body, had_fm = parse_front_matter(content)

    if not had_fm:
        print(f"  SKIP (no front matter): {filepath}")
        return False

    # Get git metadata
    author = get_original_author(filepath)
    contributors = get_all_contributors(filepath)
    division = get_division(filepath)
    source = get_source(filepath, author)

    # Build contributor list (excluding the original author)
    author_handle = to_github_handle(author)
    contributor_handles = []
    for c in contributors:
        handle = to_github_handle(c)
        if handle != author_handle:
            contributor_handles.append(handle)

    # Add new metadata fields (don't overwrite existing)
    if 'version' not in fm:
        fm['version'] = '1.0.0'
    if 'author' not in fm:
        fm['author'] = author_handle
    if 'contributors' not in fm and contributor_handles:
        fm['contributors'] = contributor_handles
    if 'source' not in fm:
        fm['source'] = source
    if 'division' not in fm:
        fm['division'] = division

    # Rebuild
    new_fm = build_front_matter(fm)
    new_content = new_fm + '\n\n' + body

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def main():
    count = 0
    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip non-agent directories
        rel_root = os.path.relpath(root, REPO_ROOT)
        top_dir = rel_root.split(os.sep)[0]
        if top_dir in SKIP_DIRS:
            continue

        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            if fname in SKIP_FILES:
                continue

            filepath = os.path.join(root, fname)
            if process_file(filepath):
                count += 1
                print(f"  Updated: {os.path.relpath(filepath, REPO_ROOT)}")

    print(f"\nDone! Updated {count} agent files with metadata.")


if __name__ == '__main__':
    main()
