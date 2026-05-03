#!/usr/bin/env python3
"""
Validate and interactively fix a Montage config YAML file.

Usage:
    python3 tools/steps/configure.py <config-file>

Checks all required fields, pre-fills values from replica.my.cnf and
environment where possible, and prompts interactively for the rest.
"""

import configparser
import os
import re
import subprocess
import sys

# ── Environment ───────────────────────────────────────────────────────────────

TOOL = os.popen("id -un | sed 's/^tools\\.//'"  ).read().strip()
CNF_PATH = os.path.expanduser('~/replica.my.cnf')

def read_cnf():
    """Read ~/replica.my.cnf and return (user, password), or (None, None)."""
    if not os.path.exists(CNF_PATH):
        return None, None
    cfg = configparser.ConfigParser()
    cfg.read(CNF_PATH)
    section = 'client' if cfg.has_section('client') else (cfg.sections() or [None])[0]
    if not section:
        return None, None
    user = cfg.get(section, 'user', fallback=None)
    password = cfg.get(section, 'password', fallback=None)
    return user, password

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
    needs_quotes = any(c in str(value) for c in ' :/?&#@')
    formatted = f'"{value}"' if needs_quotes else str(value)
    new_line = f'{key}: {formatted}'
    new_content, count = re.subn(
        rf'^{re.escape(key)}:.*$', new_line, content, flags=re.MULTILINE
    )
    if count == 0:
        new_content = content.rstrip('\n') + f'\n{new_line}\n'
    return new_content

# ── Auto-fix: fields that are always the same on Toolforge ───────────────────

ALWAYS_SET = {
    'labs_db': 'True',
    'root_path': '/',
    'db_echo': 'False',
}

# ── Field definitions ─────────────────────────────────────────────────────────

def tail(value, n=6):
    """Return '...last_n_chars' for display without revealing full secrets."""
    return f'...{value[-n:]}' if value and len(value) > n else value

def build_fields(db_user, db_password):
    db_url_default = None
    if db_user and db_password:
        db_name = f'{db_user}__montage'
        db_url_default = (
            f'mysql+pymysql://{db_user}:{db_password}'
            f'@tools.db.svc.wikimedia.cloud/{db_name}?charset=utf8mb4'
        )

    return [
        {
            'key': 'db_url',
            'label': 'Database URL',
            'bad_values': ['sqlite://', 'tmp_montage.db'],
            'default': db_url_default,
            'source': '~/replica.my.cnf',
            'sensitive': True,
            'hint': f'mysql+pymysql://{db_user or "<user>"}:<password>@tools.db.svc.wikimedia.cloud/{db_user or "<user>"}__montage?charset=utf8mb4',
            'required': True,
        },
        {
            'key': 'cookie_secret',
            'label': 'Cookie secret',
            'bad_values': ['ReplaceThis', 'Secret'],
            'auto_generate': True,
            'sensitive': True,
            'required': True,
        },
        {
            'key': 'oauth_consumer_token',
            'label': 'OAuth consumer token (from meta.wikimedia.org)',
            'bad_values': ['see note', 'visit https', 'contact maintainers'],
            'skip_if_debug': True,
            'sensitive': True,
            'required': True,
        },
        {
            'key': 'oauth_secret_token',
            'label': 'OAuth secret token',
            'bad_values': ['see note'],
            'skip_if_debug': True,
            'sensitive': True,
            'required': True,
        },
        {
            'key': 'api_log_path',
            'label': 'API log path',
            'must_be_absolute': True,
            'default': f'/data/project/{TOOL}/montage_api.log',
            'source': 'tool account name',
            'sensitive': False,
            'required': True,
        },
        {
            'key': 'replay_log_path',
            'label': 'Replay log path',
            'must_be_absolute': True,
            'default': f'/data/project/{TOOL}/montage_replay.log',
            'source': 'tool account name',
            'sensitive': False,
            'required': False,
        },
        {
            'key': 'superuser',
            'label': 'Superuser (your Wikimedia username)',
            'bad_values': ['Slaporte'],
            'sensitive': False,
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
    if field.get('must_be_absolute') and not value.startswith('/'):
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

    # ── Pre-fill always-the-same fields silently ──────────────────────────────
    changed = False
    for key, value in ALWAYS_SET.items():
        current = read_value(content, key)
        if current is None or current.strip("'\"") != value:
            content = set_value(content, key, value)
            print(f'  AUTO-SET     {key}: {value}')
            changed = True

    # ── Read replica.my.cnf for db credentials ────────────────────────────────
    db_user, db_password = read_cnf()
    if db_user:
        print(f'  replica.my.cnf: user={db_user}')
    else:
        print(f'  WARNING: {CNF_PATH} not found — db_url cannot be pre-filled')

    debug_mode = read_value(content, 'debug') in ('True', 'true', '1')
    if debug_mode:
        print('  debug mode detected — OAuth tokens not required')

    print()

    fields = build_fields(db_user, db_password)
    issues = []

    for field in fields:
        key = field['key']
        value = read_value(content, key)

        if field.get('skip_if_debug') and debug_mode:
            print(f'  SKIP         {key}  (debug mode)')
            continue

        if is_bad(value, field):
            status = 'MISSING' if value is None else 'PLACEHOLDER'
            print(f'  {status:12s} {key}')
            field['_current'] = value
            issues.append(field)
        else:
            if field.get('sensitive'):
                display = tail(value)
            else:
                display = value if len(value) < 60 else value[:57] + '...'
            print(f'  OK           {key}: {display}')

    if not issues:
        if changed:
            with open(config_path, 'w') as f:
                f.write(content)
        print()
        print('All required fields look good.')
        return

    print()
    print(f'{len(issues)} field(s) still need manual input:')

    if not sys.stdin.isatty():
        print('Not running interactively — fix the fields manually and re-run.')
        if changed:
            with open(config_path, 'w') as f:
                f.write(content)
        sys.exit(1)

    answer = input('Fill them in now? [Y/n] ').strip().lower()
    if answer in ('n', 'no'):
        if changed:
            with open(config_path, 'w') as f:
                f.write(content)
        print('Partial changes saved. Re-run to complete.')
        sys.exit(1)

    for field in issues:
        key = field['key']
        label = field['label']
        current = field.get('_current')
        proposed = field.get('default')
        print()
        print(f'  {label}')

        sensitive = field.get('sensitive', True)

        # cookie_secret: offer to auto-generate
        if field.get('auto_generate'):
            secret = generate_secret()
            if secret:
                choice = input('  Auto-generate? [Y/n] ').strip().lower()
                if choice not in ('n', 'no'):
                    content = set_value(content, key, secret)
                    print('  Generated and saved.')
                    continue

        # Proposed value (from cnf / environment): show source + tail
        if proposed:
            source = field.get('source', 'environment')
            if sensitive:
                preview = f'from {source} ({tail(proposed)})'
            else:
                preview = proposed
            choice = input(f'  Proposed ({preview}) — Accept? [Y/n] ').strip().lower()
            if choice not in ('n', 'no'):
                content = set_value(content, key, proposed)
                print('  Saved.')
                continue

        # Show hint / example
        hint = field.get('hint')
        if hint:
            print(f'  Example: {hint}')

        # Prompt — for sensitive fields show only tail of current, for others show full
        if current and current not in ('None', ''):
            if sensitive:
                prompt = f'  Value (current: {tail(current)}): '
            else:
                prompt = f'  Value [{current}]: '
        else:
            prompt = '  Value: '

        new_value = input(prompt).strip()
        if not new_value and current:
            new_value = current  # keep current if user just pressed Enter
        if new_value and new_value != current:
            content = set_value(content, key, new_value)
            print('  Saved.')
        elif new_value == current:
            print('  Kept existing value.')
        else:
            print('  Skipped.')

    with open(config_path, 'w') as f:
        f.write(content)

    # Re-verify inline so the user can see the final state without re-running
    print()
    print('── Final check:')
    remaining = []
    for field in build_fields(db_user, db_password):
        key = field['key']
        value = read_value(content, key)
        if field.get('skip_if_debug') and debug_mode:
            continue
        if is_bad(value, field):
            print(f'  STILL MISSING  {key}')
            remaining.append(key)
        else:
            display = tail(value) if field.get('sensitive') else (value if len(value) < 60 else value[:57] + '...')
            print(f'  OK             {key}: {display}')

    print()
    if remaining:
        print(f'Still missing: {", ".join(remaining)}')
        print('Re-run this script to fill them in.')
    else:
        print(f'Config complete: {config_path}')

if __name__ == '__main__':
    main()
