#!/usr/bin/env python3
"""
Validate and interactively fix a Montage config YAML file.

Usage:
    python3 tools/steps/configure.py <config-file>

Checks all required fields, reports missing or placeholder values,
and optionally prompts to fix them interactively.
"""

import re
import os
import sys
import subprocess

# ── YAML helpers (no PyYAML dependency) ──────────────────────────────────────

def read_value(content, key):
    m = re.search(rf'^{re.escape(key)}:\s*(.+)$', content, re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip()
    if len(val) >= 2 and val[0] in ('"', "'") and val[-1] == val[0]:
        val = val[1:-1]
    return val

def set_value(content, key, value):
    needs_quotes = any(c in str(value) for c in ' :/?&#')
    formatted = f'"{value}"' if needs_quotes else str(value)
    new_line = f'{key}: {formatted}'
    new_content, count = re.subn(
        rf'^{re.escape(key)}:.*$', new_line, content, flags=re.MULTILINE
    )
    if count == 0:
        new_content = content.rstrip('\n') + f'\n{new_line}\n'
    return new_content

# ── Field definitions ─────────────────────────────────────────────────────────

TOOL = os.popen("id -un | sed 's/^tools\\.//'"  ).read().strip()

FIELDS = [
    {
        'key': 'db_url',
        'label': 'Database URL',
        'bad_values': ['sqlite://', 'tmp_montage.db'],
        'hint': f'mysql+pymysql://tools.{TOOL}:<password>@tools.db.svc.wikimedia.cloud/tools.{TOOL}__montage?charset=utf8mb4',
        'required': True,
    },
    {
        'key': 'cookie_secret',
        'label': 'Cookie secret',
        'bad_values': ['ReplaceThis', 'Secret'],
        'auto_generate': True,
        'required': True,
    },
    {
        'key': 'oauth_consumer_token',
        'label': 'OAuth consumer token',
        'bad_values': ['see note', 'visit https', 'contact maintainers'],
        'skip_if_debug': True,
        'required': True,
    },
    {
        'key': 'oauth_secret_token',
        'label': 'OAuth secret token',
        'bad_values': ['see note'],
        'skip_if_debug': True,
        'required': True,
    },
    {
        'key': 'api_log_path',
        'label': 'API log path',
        'bad_values': ['montage_api.log'],
        'default': f'/data/project/{TOOL}/montage_api.log',
        'required': True,
    },
    {
        'key': 'replay_log_path',
        'label': 'Replay log path',
        'bad_values': ['replay_log_path'],
        'default': f'/data/project/{TOOL}/montage_replay.log',
        'required': False,
    },
    {
        'key': 'labs_db',
        'label': 'labs_db (must be True on Toolforge)',
        'expected': 'True',
        'skip_if_debug': False,
        'required': True,
    },
    {
        'key': 'root_path',
        'label': "root_path (must be '/')",
        'expected': '/',
        'required': True,
    },
    {
        'key': 'db_echo',
        'label': 'db_echo (should be False in production)',
        'expected': 'False',
        'required': False,
    },
    {
        'key': 'superuser',
        'label': 'Superuser (your Wikimedia username)',
        'bad_values': ['Slaporte'],
        'required': False,
    },
]

# ── Validation ────────────────────────────────────────────────────────────────

def is_bad(value, field):
    if value is None:
        return True
    for bad in field.get('bad_values', []):
        if bad.lower() in value.lower():
            return True
    expected = field.get('expected')
    if expected is not None and value.strip("'\"") != expected.strip("'\""):
        return True
    return False

def generate_secret():
    result = subprocess.run(['openssl', 'rand', '-hex', '32'],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f'Usage: python3 {sys.argv[0]} <config-file>')
        sys.exit(1)

    config_path = sys.argv[1]
    if not os.path.exists(config_path):
        print(f'ERROR: {config_path} not found.')
        sys.exit(1)

    with open(config_path) as f:
        content = f.read()

    debug_mode = read_value(content, 'debug') in ('True', 'true', '1')
    if debug_mode:
        print('  (debug mode detected — OAuth tokens not required)')

    print()
    issues = []

    for field in FIELDS:
        key = field['key']
        label = field['label']
        value = read_value(content, key)

        if field.get('skip_if_debug') and debug_mode:
            print(f'  SKIP  {key}  (debug mode)')
            continue

        if is_bad(value, field):
            status = 'MISSING' if value is None else 'PLACEHOLDER'
            print(f'  {status:11s}  {key}')
            issues.append(field)
        else:
            display = value if len(value) < 40 else value[:37] + '...'
            print(f'  OK           {key}: {display}')

    if not issues:
        print()
        print('All required fields look good.')
        return

    print()
    print(f'Found {len(issues)} field(s) that need attention.')

    if not sys.stdin.isatty():
        print('Not running interactively — fix the fields manually and re-run.')
        sys.exit(1)

    answer = input('Fix them now interactively? [y/N] ').strip().lower()
    if answer not in ('y', 'yes'):
        print('No changes made.')
        sys.exit(1)

    for field in issues:
        key = field['key']
        label = field['label']
        print()
        print(f'  {label}')

        if field.get('auto_generate'):
            secret = generate_secret()
            if secret:
                use_generated = input(f'  Auto-generate? [Y/n] ').strip().lower()
                if use_generated not in ('n', 'no'):
                    content = set_value(content, key, secret)
                    print(f'  Generated and saved.')
                    continue

        hint = field.get('hint') or field.get('default') or field.get('expected', '')
        if hint:
            print(f'  Example: {hint}')

        default = field.get('default') or field.get('expected')
        prompt = f'  Value [{default}]: ' if default else '  Value: '
        new_value = input(prompt).strip()
        if not new_value and default:
            new_value = default
        if new_value:
            content = set_value(content, key, new_value)
            print(f'  Saved.')
        else:
            print(f'  Skipped.')

    with open(config_path, 'w') as f:
        f.write(content)

    print()
    print(f'Config written to {config_path}')
    print('Run this script again to verify.')

if __name__ == '__main__':
    main()
