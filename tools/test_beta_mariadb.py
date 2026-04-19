#!/usr/bin/env python3
"""
Verify schema state and query performance for the file_id migration (#505).

Run this BEFORE and AFTER running migrate_prod_db.sql to produce comparable
numbers. Output is designed to be pasted directly into hatnote/montage#514.

Usage (from inside toolforge webservice python3.13 shell):
    source ~/www/python/venv/bin/activate
    python3 ~/www/python/src/tools/test_beta_mariadb.py \
        --db_url "mysql+pymysql://<user>:<pass>@tools.db.svc.wikimedia.cloud/<db>?charset=utf8mb4" \
        --category "Images_from_Wiki_Loves_Monuments_2015_in_France"
"""
import argparse
import os
import sys
import time

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)
sys.path.insert(0, PROJ_PATH)


def check_schema(db_url):
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url, echo=False)
    with engine.connect() as conn:
        version = conn.execute(text('SELECT VERSION()')).scalar()

        col = conn.execute(text(
            "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "  AND TABLE_NAME = 'entries' "
            "  AND COLUMN_NAME = 'file_id'"
        )).fetchone()

        idx = conn.execute(text(
            "SELECT INDEX_NAME FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "  AND TABLE_NAME = 'entries' "
            "  AND INDEX_NAME = 'ix_entries_file_id'"
        )).fetchone()

        total = conn.execute(text('SELECT COUNT(*) FROM entries')).scalar()
        with_file_id = conn.execute(text('SELECT COUNT(file_id) FROM entries')).scalar()

    return {
        'mariadb_version': version,
        'file_id_column': col,
        'file_id_index': idx,
        'total_entries': total,
        'entries_with_file_id': with_file_id,
    }


def check_performance(category):
    from montage.labs import get_files
    start = time.time()
    results = get_files(category)
    elapsed = time.time() - start
    nulls = [r for r in results if r.get('file_id') is None]
    return {
        'category': category,
        'file_count': len(results),
        'elapsed_seconds': round(elapsed, 2),
        'null_file_ids': len(nulls),
        'null_examples': [r['img_name'] for r in nulls[:5]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--db_url', default=None, help='SQLAlchemy DB URL (default: read from config)')
    parser.add_argument('--category', default='Images_from_Wiki_Loves_Monuments_2015_in_France', help='Commons category to query (no File: prefix)')
    args = parser.parse_args()

    db_url = args.db_url
    if not db_url:
        from montage.utils import load_env_config
        config = load_env_config()
        db_url = config['db_url']

    print('=' * 60)
    print('Montage beta MariaDB verification — hatnote/montage#514')
    print('=' * 60)
    print('DB URL:', db_url.split('@')[-1])  # print host/db only, not credentials

    print('\n## Schema state\n')
    try:
        s = check_schema(db_url)
        print('MariaDB version :', s['mariadb_version'])
        if s['file_id_column']:
            col = s['file_id_column']
            print('file_id column  : PRESENT  (%s, nullable=%s)' % (col[1], col[2]))
        else:
            print('file_id column  : ABSENT')
        if s['file_id_index']:
            print('file_id index   : PRESENT  (ix_entries_file_id)')
        else:
            print('file_id index   : ABSENT')
        print('Total entries   :', s['total_entries'])
        print('With file_id    :', s['entries_with_file_id'])
        if s['total_entries'] > 0:
            pct = 100 * s['entries_with_file_id'] // s['total_entries']
            print('Coverage        : %d%%' % pct)
    except Exception as e:
        print('ERROR checking schema:', e)

    print('\n## Query performance\n')
    try:
        p = check_performance(args.category)
        print('Category        :', p['category'])
        print('Files returned  :', p['file_count'])
        print('Elapsed         : %.2f seconds' % p['elapsed_seconds'])
        print('Null file_ids   :', p['null_file_ids'])
        if p['null_examples']:
            print('Null examples   :', p['null_examples'])
        if p['elapsed_seconds'] > 30:
            print('\nWARNING: query exceeded 30s — correlated subquery may need optimisation.')
    except Exception as e:
        print('ERROR running get_files():', e)

    print('\n' + '=' * 60)


if __name__ == '__main__':
    main()
