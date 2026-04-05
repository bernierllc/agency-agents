#!/usr/bin/env python3
"""Add metadata front matter to all agent .md files.

Adds author, contributors, version, source, and division fields
to the YAML front matter of each agent file.

Supports incremental scanning via a cursor file (.metadata-scan-cursor)
that stores the last scanned commit SHA. On subsequent runs, only files
changed since that commit are re-processed for contributor updates.

Usage:
    python3 scripts/add-metadata.py           # incremental (default)
    python3 scripts/add-metadata.py --full     # full rescan from scratch
"""

import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURSOR_FILE = os.path.join(REPO_ROOT, '.metadata-scan-cursor')

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


# ---------------------------------------------------------------------------
# Cursor file helpers
# ---------------------------------------------------------------------------

def read_cursor():
    """Read the last scanned commit SHA from the cursor file."""
    if os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE, 'r') as f:
            sha = f.read().strip()
            if sha:
                return sha
    return None


def write_cursor(sha):
    """Write the current HEAD SHA to the cursor file."""
    with open(CURSOR_FILE, 'w') as f:
        f.write(sha + '\n')


def get_head_sha():
    """Get the current HEAD commit SHA."""
    result = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.stdout.strip()


def get_changed_agent_files(since_sha):
    """Get list of agent .md files changed since the given commit."""
    result = subprocess.run(
        ['git', 'diff', '--name-only', since_sha, 'HEAD', '--', '*.md'],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    files = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        full_path = os.path.join(REPO_ROOT, line)
        if os.path.exists(full_path) and is_agent_file(full_path):
            files.append(full_path)
    return files


def get_new_agent_files(since_sha):
    """Get agent .md files that are new (untracked or added) since cursor."""
    result = subprocess.run(
        ['git', 'diff', '--name-only', '--diff-filter=A', since_sha, 'HEAD', '--', '*.md'],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    files = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        full_path = os.path.join(REPO_ROOT, line)
        if os.path.exists(full_path) and is_agent_file(full_path):
            files.append(full_path)
    return files


# ---------------------------------------------------------------------------
# Agent file identification
# ---------------------------------------------------------------------------

def is_agent_file(filepath):
    """Check if a file is an agent .md file (not a doc/config file)."""
    if not filepath.endswith('.md'):
        return False
    rel = os.path.relpath(filepath, REPO_ROOT)
    fname = os.path.basename(filepath)
    if fname in SKIP_FILES:
        return False
    top_dir = rel.split(os.sep)[0]
    if top_dir in SKIP_DIRS:
        return False
    return True


def get_all_agent_files():
    """Walk the repo and return all agent .md files."""
    agent_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        rel_root = os.path.relpath(root, REPO_ROOT)
        top_dir = rel_root.split(os.sep)[0]
        if top_dir in SKIP_DIRS:
            continue
        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            if fname in SKIP_FILES:
                continue
            agent_files.append(os.path.join(root, fname))
    return agent_files


# ---------------------------------------------------------------------------
# Git metadata helpers
# ---------------------------------------------------------------------------

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


def get_contributors_since(filepath, since_sha):
    """Get contributors to a file since a given commit."""
    rel = os.path.relpath(filepath, REPO_ROOT)
    result = subprocess.run(
        ['git', 'log', f'{since_sha}..HEAD', '--format=%an', '--', rel],
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


# ---------------------------------------------------------------------------
# Front matter parsing and building
# ---------------------------------------------------------------------------

def parse_front_matter(content):
    """Parse existing YAML front matter. Returns (front_matter_dict, body, had_frontmatter)."""
    if not content.startswith('---'):
        return {}, content, False

    end = content.find('---', 3)
    if end == -1:
        return {}, content, False

    fm_text = content[3:end].strip()
    body = content[end + 3:].lstrip('\n')

    fm = {}
    current_key = None
    current_val_lines = []

    for line in fm_text.split('\n'):
        match = re.match(r'^(\w[\w-]*)\s*:\s*(.*)', line)
        if match:
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


def parse_contributors_field(val):
    """Parse the contributors field value into a list of handles."""
    if isinstance(val, list):
        return val
    # Handle YAML list format: lines starting with -
    contribs = []
    for line in val.split('\n'):
        line = line.strip()
        if line.startswith('- '):
            handle = line[2:].strip().strip('"').strip("'")
            if handle:
                contribs.append(handle)
    if contribs:
        return contribs
    # Handle comma-separated
    return [c.strip().strip('"').strip("'") for c in val.split(',') if c.strip()]


def build_front_matter(fm):
    """Build YAML front matter string from dict, preserving field order."""
    order = ['name', 'description', 'version', 'author', 'contributors', 'source', 'division', 'color', 'emoji', 'tools']
    lines = ['---']

    for key in order:
        if key not in fm:
            continue
        val = fm[key]
        if key == 'description' and ('\n' in val or len(val) > 100):
            if val.startswith('>\n') or val.startswith('>'):
                lines.append(f'{key}: >')
                desc = val.lstrip('>').strip()
                for dline in desc.split('\n'):
                    lines.append(f'  {dline.strip()}')
            else:
                lines.append(f'{key}: >')
                for dline in val.split('\n'):
                    lines.append(f'  {dline.strip()}')
        elif key == 'contributors':
            lines.append(f'{key}:')
            contribs = val if isinstance(val, list) else parse_contributors_field(val)
            for c in contribs:
                lines.append(f'  - "{c}"')
        elif key in ('description', 'name') and ('"' in str(val) or ':' in str(val)):
            lines.append(f'{key}: "{val}"')
        else:
            lines.append(f'{key}: {val}')

    for key in fm:
        if key not in order:
            lines.append(f'{key}: {fm[key]}')

    lines.append('---')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------

def process_file(filepath, incremental_since=None):
    """Add or update metadata on a single agent file.

    If incremental_since is set, only merge in new contributors found
    since that commit (skips full author/contributor rescan).
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fm, body, had_fm = parse_front_matter(content)

    if not had_fm:
        print(f"  SKIP (no front matter): {os.path.relpath(filepath, REPO_ROOT)}")
        return False

    changed = False

    if incremental_since and 'author' in fm:
        # Incremental mode: only update contributors with new names
        new_contributors = get_contributors_since(filepath, incremental_since)
        if new_contributors:
            existing = set(parse_contributors_field(fm.get('contributors', ''))) if fm.get('contributors') else set()
            author_handle = fm.get('author', '')
            for c in new_contributors:
                handle = to_github_handle(c)
                if handle != author_handle and handle not in existing:
                    existing.add(handle)
                    changed = True
            if existing:
                fm['contributors'] = sorted(existing)

        # Always update division in case file was moved
        new_division = get_division(filepath)
        if fm.get('division') != new_division:
            fm['division'] = new_division
            changed = True
    else:
        # Full mode: set all metadata fields
        author = get_original_author(filepath)
        contributors = get_all_contributors(filepath)
        division = get_division(filepath)
        source = get_source(filepath, author)

        author_handle = to_github_handle(author)
        contributor_handles = []
        for c in contributors:
            handle = to_github_handle(c)
            if handle != author_handle:
                contributor_handles.append(handle)

        if 'version' not in fm:
            fm['version'] = '1.0.0'
            changed = True
        if 'author' not in fm:
            fm['author'] = author_handle
            changed = True
        if 'contributors' not in fm and contributor_handles:
            fm['contributors'] = contributor_handles
            changed = True
        elif contributor_handles:
            existing = set(parse_contributors_field(fm.get('contributors', ''))) if fm.get('contributors') else set()
            for h in contributor_handles:
                if h not in existing:
                    existing.add(h)
                    changed = True
            if existing:
                fm['contributors'] = sorted(existing)
        if 'source' not in fm:
            fm['source'] = source
            changed = True
        if 'division' not in fm:
            fm['division'] = division
            changed = True
        elif fm['division'] != division:
            fm['division'] = division
            changed = True

        # If this is a first-time scan, always write to normalize format
        if incremental_since is None:
            changed = True

    if not changed:
        return False

    new_fm = build_front_matter(fm)
    new_content = new_fm + '\n\n' + body

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    full_mode = '--full' in sys.argv

    head_sha = get_head_sha()
    cursor_sha = read_cursor()

    if full_mode or not cursor_sha:
        if full_mode:
            print("Running full metadata scan (--full flag)...")
        else:
            print("No .metadata-scan-cursor found — running full scan...")

        agent_files = get_all_agent_files()
        count = 0
        for filepath in agent_files:
            if process_file(filepath, incremental_since=None):
                count += 1
                print(f"  Updated: {os.path.relpath(filepath, REPO_ROOT)}")

        write_cursor(head_sha)
        print(f"\nDone! Updated {count}/{len(agent_files)} agent files.")
        print(f"Cursor saved: {head_sha[:12]}")
    else:
        print(f"Incremental scan since {cursor_sha[:12]}...")

        # Get files changed since last scan
        changed_files = get_changed_agent_files(cursor_sha)
        new_files = get_new_agent_files(cursor_sha)

        # New files get a full scan, changed files get incremental
        all_files = set(changed_files) | set(new_files)

        if not all_files:
            print("No agent files changed since last scan.")
            write_cursor(head_sha)
            return

        count = 0
        for filepath in sorted(all_files):
            is_new = filepath in new_files
            if process_file(filepath, incremental_since=None if is_new else cursor_sha):
                count += 1
                label = "NEW" if is_new else "updated"
                print(f"  {label}: {os.path.relpath(filepath, REPO_ROOT)}")

        write_cursor(head_sha)
        print(f"\nDone! Processed {count}/{len(all_files)} changed agent files.")
        print(f"Cursor saved: {head_sha[:12]}")


if __name__ == '__main__':
    main()
