#!/usr/bin/env python3
"""Check which wikireplica hostname is reachable from this environment."""
import os, pymysql

HOSTS = ['commonswiki.labsdb', 'commonswiki.analytics.db.svc.wikimedia.cloud']
CNFPATH = os.path.expanduser('~/replica.my.cnf')

for host in HOSTS:
    try:
        c = pymysql.connect(read_default_file=CNFPATH, host=host, db='commonswiki_p', connect_timeout=5)
        c.cursor().execute('SELECT 1')
        c.close()
        print(host, '-> OK')
    except Exception as e:
        print(host, '-> FAILED:', e)
