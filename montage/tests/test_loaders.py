# -*- coding: utf-8 -*-

from __future__ import print_function

from pytest import raises

from montage.loaders import get_entries_from_gsheet

RESULTS = 'https://docs.google.com/spreadsheets/d/1RDlpT23SV_JB1mIz0OA-iuc3MNdNVLbaK_LtWAC7vzg/edit?usp=sharing'
FILENAME_LIST = 'https://docs.google.com/spreadsheets/d/1Nqj-JsX3L5qLp5ITTAcAFYouglbs5OpnFwP6zSFpa0M/edit?usp=sharing'
GENERIC_CSV = 'https://docs.google.com/spreadsheets/d/1WzHFg_bhvNthRMwNmxnk010KJ8fwuyCrby29MvHUzH8/edit#gid=550467819'
FORBIDDEN_SHEET = 'https://docs.google.com/spreadsheets/d/1tza92brMKkZBTykw3iS6X9ij1D4_kvIYAiUlq1Yi7Fs/edit'

def test_load_results():
    imgs, warnings = get_entries_from_gsheet(RESULTS, source='remote')
    assert len(imgs) == 331

def test_load_filenames():
    imgs, warnings = get_entries_from_gsheet(FILENAME_LIST, source='remote') 
    assert len(imgs) == 89

def test_load_csv():
    imgs, warnings = get_entries_from_gsheet(GENERIC_CSV, source='remote') 
    assert len(imgs) == 93

def test_no_persmission():
    with raises(ValueError):
        imgs, warnings = get_entries_from_gsheet(FORBIDDEN_SHEET, source='remote')
