# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import

import os

import pytest
import responses
from pytest import raises

from montage.loaders import get_entries_from_gsheet, make_entry

from .conftest import (
    FIXTURE_FILE_INFOS,
    FIXTURE_FULL_CSV,
    FIXTURE_FILENAME_CSV,
    TOOLFORGE_FILE_URL,
    REUPLOAD_FILE_INFO,
)

RESULTS = 'https://docs.google.com/spreadsheets/d/1RDlpT23SV_JB1mIz0OA-iuc3MNdNVLbaK_LtWAC7vzg/edit?usp=sharing'
FILENAME_LIST = 'https://docs.google.com/spreadsheets/d/1Nqj-JsX3L5qLp5ITTAcAFYouglbs5OpnFwP6zSFpa0M/edit?usp=sharing'
GENERIC_CSV = 'https://docs.google.com/spreadsheets/d/1WzHFg_bhvNthRMwNmxnk010KJ8fwuyCrby29MvHUzH8/edit#gid=550467819'
FORBIDDEN_SHEET = 'https://docs.google.com/spreadsheets/d/1tza92brMKkZBTykw3iS6X9ij1D4_kvIYAiUlq1Yi7Fs/edit'

# Pre-compute the actual fetch URLs that loaders.py constructs from the
# doc IDs embedded in the spreadsheet URLs above.
_RESULTS_CSV_URL = 'https://docs.google.com/spreadsheets/d/1RDlpT23SV_JB1mIz0OA-iuc3MNdNVLbaK_LtWAC7vzg/gviz/tq?tqx=out:csv'
_FILENAME_CSV_URL = 'https://docs.google.com/spreadsheets/d/1Nqj-JsX3L5qLp5ITTAcAFYouglbs5OpnFwP6zSFpa0M/gviz/tq?tqx=out:csv'
_GENERIC_CSV_URL = 'https://docs.google.com/spreadsheets/d/1WzHFg_bhvNthRMwNmxnk010KJ8fwuyCrby29MvHUzH8/gviz/tq?tqx=out:csv'
_FORBIDDEN_CSV_URL = 'https://docs.google.com/spreadsheets/d/1tza92brMKkZBTykw3iS6X9ij1D4_kvIYAiUlq1Yi7Fs/gviz/tq?tqx=out:csv'


@responses.activate
def test_load_results():
    """Full CSV with all required columns -- entries created directly."""
    responses.add(
        responses.GET,
        _RESULTS_CSV_URL,
        body=FIXTURE_FULL_CSV,
        status=200,
        content_type='text/csv',
    )
    imgs, warnings = get_entries_from_gsheet(RESULTS, source='remote')
    assert len(imgs) == len(FIXTURE_FILE_INFOS)


@responses.activate
def test_load_filenames():
    """Partial CSV with only 'filename' column -- triggers Toolforge lookup."""
    responses.add(
        responses.GET,
        _FILENAME_CSV_URL,
        body=FIXTURE_FILENAME_CSV,
        status=200,
        content_type='text/csv',
    )
    # The filename-only CSV triggers load_partial_csv -> load_name_list
    # -> get_by_filename_remote -> POST to Toolforge /file endpoint.
    responses.add(
        responses.POST,
        TOOLFORGE_FILE_URL,
        json={'file_infos': FIXTURE_FILE_INFOS, 'no_info': []},
        status=200,
    )
    imgs, warnings = get_entries_from_gsheet(FILENAME_LIST, source='remote')
    assert len(imgs) == len(FIXTURE_FILE_INFOS)


@responses.activate
def test_load_csv():
    """Generic full CSV -- same path as test_load_results."""
    responses.add(
        responses.GET,
        _GENERIC_CSV_URL,
        body=FIXTURE_FULL_CSV,
        status=200,
        content_type='text/csv',
    )
    imgs, warnings = get_entries_from_gsheet(GENERIC_CSV, source='remote')
    assert len(imgs) == len(FIXTURE_FILE_INFOS)


@responses.activate
def test_no_persmission():
    """Non-CSV content-type signals a permission / sharing error."""
    responses.add(
        responses.GET,
        _FORBIDDEN_CSV_URL,
        body='<html><body>Sign in</body></html>',
        status=200,
        content_type='text/html',
    )
    with raises(ValueError):
        get_entries_from_gsheet(FORBIDDEN_SHEET, source='remote')


def test_make_entry_reupload():
    """make_entry() correctly handles a reuploaded file."""
    entry = make_entry(REUPLOAD_FILE_INFO)
    assert entry.flags['reupload'] is True
    assert entry.flags['reupload_user_id'] == '2222'
    assert entry.file_id == 88888


@pytest.mark.xfail(
    os.environ.get('TOOLFORGE') != '1',
    reason='Requires live wikireplica (Toolforge); set TOOLFORGE=1 to run',
)
def test_get_files_parity():
    """New file/filerevision query returns same filenames as old image/oldimage query."""
    from montage.labs import get_files, get_files_legacy
    category = 'Images_from_Wiki_Loves_Monuments_2015_in_France'
    new = {r['img_name'] for r in get_files(category)}
    old = {r['img_name'] for r in get_files_legacy(category)}
    assert new == old
