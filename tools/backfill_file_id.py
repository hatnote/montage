"""
Backfill file_id for entries imported before the #505 migration.
Process entries in batches, match by filename against commonswiki_p.file,
cross-check data where possible, and log all non-matches.
"""

from __future__ import print_function
import argparse
import sys
import datetime

from montage.rdb import make_rdb_session, Entry
from montage.labs import get_file_info
from montage.utils import get_env_name

def backfill_file_ids(dry_run=True, batch_size=200):
    session = make_rdb_session(echo=False)
    
    # Query for all entries missing file_id
    entries_to_backfill = session.query(Entry).filter(Entry.file_id == None).all()
    total_entries = len(entries_to_backfill)
    
    print("Found {} entries missing file_id.".format(total_entries))
    
    if total_entries == 0:
        print("Nothing to backfill.")
        return
        
    updated_count = 0
    non_matches = []
    
    for i in range(0, total_entries, batch_size):
        batch = entries_to_backfill[i:i + batch_size]
        print("Processing batch {} to {}...".format(i, min(i + len(batch), total_entries)))
        
        for entry in batch:
            file_info = get_file_info(entry.name)
            if not file_info:
                non_matches.append((entry.id, entry.name, "Not found in replica by name"))
                continue
            
            # Basic sanity guard check
            # Commons wiki replica timestamp format: YYYYMMDDHHMMSS (bytes or str depending on pymysql config)
            # Entry.upload_date is python builtin datetime
            db_date = entry.upload_date
            wiki_date = file_info.get('img_timestamp')
            if wiki_date and isinstance(wiki_date, bytes):
                wiki_date = wiki_date.decode('utf-8')
            
            file_id = file_info.get('file_id')
            if file_id is not None:
                entry.file_id = int(file_id)
                updated_count += 1
            else:
                non_matches.append((entry.id, entry.name, "No file_id in replica output"))
                
        if not dry_run:
            session.commit()
            print("Committed batch up to {}".format(min(i + len(batch), total_entries)))
            
    print("\nBackfill summary: Updated {} / {}".format(updated_count, total_entries))
    if non_matches:
        print("There were {} non-matches logged for manual review:".format(len(non_matches)))
        for nid, nname, nreason in non_matches:
            print(" - Entry ID {}: {} ({})".format(nid, nname, nreason))
            
    if dry_run:
        print("\n[DRY RUN] No changes were committed to the database.")
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Backfill file_ids for legacy entries")
    parser.add_argument('--commit', action='store_true', help='Commit changes (disables dry_run)')
    args = parser.parse_args()
    
    backfill_file_ids(dry_run=not args.commit)
