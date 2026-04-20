#!/bin/bash
# Run test_beta_mariadb.py — reads db_url from config.beta.yaml automatically.
# Script: ~/www/python/src/tools/test_beta_mariadb.py
# Issue:  hatnote/montage#514
set -e
source ~/www/python/venv/bin/activate
CAT="Images_from_Wiki_Loves_Monuments_2015_in_France"
python3 ~/www/python/src/tools/test_beta_mariadb.py --category "$CAT"
