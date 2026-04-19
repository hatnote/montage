#!/usr/bin/env python3
"""Check which wikireplica hostname is reachable from this environment."""
import pymysql

HOSTS = ['commonswiki.labsdb', 'commonswiki.analytics.db.svc.wikimedia.cloud']

for host in HOSTS:
    try:
        c = pymysql.connect(read_default_file='/root/replica.my.cnf', host=host, db='commonswiki_p', connect_timeout=5)
        c.cursor().execute('SELECT 1')
        c.close()
        print(host, '-> OK')
    except Exception as e:
        print(host, '-> FAILED:', e)
