# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import sys
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import montage modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from montage.rdb import Round, Entry, RoundEntry, Campaign, User, Base

def migrate_entries(db_url, source_round_id, target_round_id):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    source_round = session.query(Round).get(source_round_id)
    target_round = session.query(Round).get(target_round_id)

    if not source_round or not target_round:
        print("Error: Source or target round not found.")
        return

    print(f"Migrating entries from {source_round.name} to {target_round.name}...")

    source_entries = session.query(RoundEntry).filter_by(round_id=source_round_id).all()
    count = 0
    for se in source_entries:
        # Check if already exists in target
        exists = session.query(RoundEntry).filter_by(round_id=target_round_id, entry_id=se.entry_id).first()
        if not exists:
            new_re = RoundEntry(entry_id=se.entry_id, round_id=target_round_id)
            session.add(new_re)
            count += 1

    session.commit()
    print(f"Successfully migrated {count} entries.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate entries between Montage rounds.')
    parser.add_argument('--db', required=True, help='Database URL')
    parser.add_argument('--source', type=int, required=True, help='Source Round ID')
    parser.add_argument('--target', type=int, required=True, help='Target Round ID')
    
    args = parser.parse_args()
    migrate_entries(args.db, args.source, args.target)
