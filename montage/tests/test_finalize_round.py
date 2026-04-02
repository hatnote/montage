# -*- coding: utf-8 -*-

"""
Integration tests for round finalization endpoint (/admin/round/<id>/finalize).

Tests cover:
- Ranking round finalization (result_summary creation)
- Rating/YesNo round finalization with threshold validation
- Threshold validation errors (missing, non-numeric, out of range)

Fixtures (montage_app, api_client) are provided by conftest.py.
"""

from __future__ import print_function
from __future__ import absolute_import

from montage.tests.test_web_basic import submit_ratings


def test_finalize_ranking_round(api_client):
    """finalize_round with ranking vote method returns result_summary_id."""
    fetch = api_client.fetch

    resp = fetch('get default series', '/series')
    series_id = resp['data'][0]['id']

    resp = fetch('organizer: create campaign',
                 '/admin/add_campaign',
                 {'name': 'Finalize Ranking Test Campaign',
                  'coordinators': [u'LilyOfTheWest'],
                  'close_date': '2025-10-01 17:00:00',
                  'url': 'http://hatnote.com',
                  'series_id': series_id},
                 as_user='LilyOfTheWest')
    campaign_id = resp['data']['id']

    resp = fetch('coordinator: add ranking round',
                 '/admin/campaign/%s/add_round' % campaign_id,
                 {'name': 'Test ranking round',
                  'vote_method': 'ranking',
                  'quorum': 2,
                  'deadline_date': '2025-10-20T00:00:00',
                  'jurors': [u'Slaporte', u'Effeietsanders']},
                 as_user='LilyOfTheWest')
    round_id = resp['data']['id']

    fetch('coordinator: import entries',
          '/admin/round/%s/import' % round_id,
          {'import_method': 'category',
           'category': 'Images_from_Wiki_Loves_Monuments_2015_in_Albania'},
          as_user='LilyOfTheWest')

    fetch('coordinator: activate round',
          '/admin/round/%s/activate' % round_id,
          {'post': True}, as_user='LilyOfTheWest')

    submit_ratings(api_client, round_id, coord_user='LilyOfTheWest')

    resp = fetch('coordinator: finalize ranking round',
                 '/admin/round/%s/finalize' % round_id,
                 {'post': True}, as_user='LilyOfTheWest')

    assert resp['status'] == 'success'
    assert isinstance(resp['data']['result_summary_id'], int)


def test_finalize_rating_round_with_threshold(api_client):
    """finalize_round with rating vote method and valid threshold returns advancing_count."""
    fetch = api_client.fetch

    resp = fetch('get default series', '/series')
    series_id = resp['data'][0]['id']

    resp = fetch('organizer: create campaign',
                 '/admin/add_campaign',
                 {'name': 'Finalize Rating Test Campaign',
                  'coordinators': [u'LilyOfTheWest'],
                  'close_date': '2025-10-01 17:00:00',
                  'url': 'http://hatnote.com',
                  'series_id': series_id},
                 as_user='LilyOfTheWest')
    campaign_id = resp['data']['id']

    resp = fetch('coordinator: add rating round',
                 '/admin/campaign/%s/add_round' % campaign_id,
                 {'name': 'Test rating round',
                  'vote_method': 'rating',
                  'quorum': 2,
                  'deadline_date': '2025-10-20T00:00:00',
                  'jurors': [u'Slaporte', u'Effeietsanders']},
                 as_user='LilyOfTheWest')
    round_id = resp['data']['id']

    fetch('coordinator: import entries',
          '/admin/round/%s/import' % round_id,
          {'import_method': 'category',
           'category': 'Images_from_Wiki_Loves_Monuments_2015_in_Albania'},
          as_user='LilyOfTheWest')

    fetch('coordinator: activate round',
          '/admin/round/%s/activate' % round_id,
          {'post': True}, as_user='LilyOfTheWest')

    submit_ratings(api_client, round_id, coord_user='LilyOfTheWest')

    resp = fetch('coordinator: finalize rating round',
                 '/admin/round/%s/finalize' % round_id,
                 {'threshold': 0.5}, as_user='LilyOfTheWest')

    assert resp['status'] == 'success'
    assert isinstance(resp['data']['advancing_count'], int)
    assert resp['data']['threshold'] == 0.5


def test_finalize_yesno_round_with_threshold(api_client):
    """finalize_round with yesno vote method and valid threshold returns advancing_count."""
    fetch = api_client.fetch

    resp = fetch('get default series', '/series')
    series_id = resp['data'][0]['id']

    resp = fetch('organizer: create campaign',
                 '/admin/add_campaign',
                 {'name': 'Finalize YesNo Test Campaign',
                  'coordinators': [u'LilyOfTheWest'],
                  'close_date': '2025-10-01 17:00:00',
                  'url': 'http://hatnote.com',
                  'series_id': series_id},
                 as_user='LilyOfTheWest')
    campaign_id = resp['data']['id']

    resp = fetch('coordinator: add yesno round',
                 '/admin/campaign/%s/add_round' % campaign_id,
                 {'name': 'Test yesno round',
                  'vote_method': 'yesno',
                  'quorum': 2,
                  'deadline_date': '2025-10-20T00:00:00',
                  'jurors': [u'Slaporte', u'Effeietsanders']},
                 as_user='LilyOfTheWest')
    round_id = resp['data']['id']

    fetch('coordinator: import entries',
          '/admin/round/%s/import' % round_id,
          {'import_method': 'category',
           'category': 'Images_from_Wiki_Loves_Monuments_2015_in_albania'},
          as_user='LilyOfTheWest')

    fetch('coordinator: activate round',
          '/admin/round/%s/activate' % round_id,
          {'post': True}, as_user='LilyOfTheWest')

    submit_ratings(api_client, round_id, coord_user='LilyOfTheWest')

    resp = fetch('coordinator: finalize yesno round',
                 '/admin/round/%s/finalize' % round_id,
                 {'threshold': 0.5}, as_user='LilyOfTheWest')

    assert resp['status'] == 'success'
    assert isinstance(resp['data']['advancing_count'], int)
    assert resp['data']['threshold'] == 0.5


def _setup_active_round(fetch, vote_method):
    """Helper: create campaign, add a round of given vote_method, import entries, activate."""
    resp = fetch('get default series', '/series')
    series_id = resp['data'][0]['id']

    resp = fetch('organizer: create campaign',
                 '/admin/add_campaign',
                 {'name': 'Threshold Validation Campaign (%s)' % vote_method,
                  'coordinators': [u'LilyOfTheWest'],
                  'close_date': '2025-10-01 17:00:00',
                  'url': 'http://hatnote.com',
                  'series_id': series_id},
                 as_user='LilyOfTheWest')
    campaign_id = resp['data']['id']

    resp = fetch('coordinator: add round',
                 '/admin/campaign/%s/add_round' % campaign_id,
                 {'name': 'Test %s round' % vote_method,
                  'vote_method': vote_method,
                  'quorum': 2,
                  'deadline_date': '2025-10-20T00:00:00',
                  'jurors': [u'Slaporte', u'Effeietsanders']},
                 as_user='LilyOfTheWest')
    round_id = resp['data']['id']

    fetch('coordinator: import entries',
          '/admin/round/%s/import' % round_id,
          {'import_method': 'category',
           'category': 'Images_from_Wiki_Loves_Monuments_2015_in_Albania'},
          as_user='LilyOfTheWest')

    fetch('coordinator: activate round',
          '/admin/round/%s/activate' % round_id,
          {'post': True}, as_user='LilyOfTheWest')

    return round_id


def test_finalize_round_missing_threshold(api_client):
    """finalize_round without threshold raises InvalidAction (400) for rating/yesno rounds."""
    fetch = api_client.fetch
    round_id = _setup_active_round(fetch, 'yesno')

    resp = fetch('coordinator: try finalize without threshold',
                 '/admin/round/%s/finalize' % round_id,
                 {}, as_user='LilyOfTheWest', error_code=400)

    assert resp['status'] == 'failure'
    assert 'threshold is required' in resp['errors']


def test_finalize_round_non_numeric_threshold(api_client):
    """finalize_round with a non-numeric threshold raises InvalidAction (400)."""
    fetch = api_client.fetch
    round_id = _setup_active_round(fetch, 'rating')

    resp = fetch('coordinator: try finalize with string threshold',
                 '/admin/round/%s/finalize' % round_id,
                 {'threshold': 'abc'}, as_user='LilyOfTheWest', error_code=400)

    assert resp['status'] == 'failure'
    assert 'threshold must be a number' in resp['errors']

    resp = fetch('coordinator: try finalize with empty string threshold',
                 '/admin/round/%s/finalize' % round_id,
                 {'threshold': ''}, as_user='LilyOfTheWest', error_code=400)

    assert resp['status'] == 'failure'
    assert 'threshold must be a number' in resp['errors']


def test_finalize_round_threshold_out_of_range(api_client):
    """finalize_round with threshold outside [0.0, 1.0] raises InvalidAction (400)."""
    fetch = api_client.fetch
    round_id = _setup_active_round(fetch, 'yesno')

    resp = fetch('coordinator: try finalize with threshold above 1.0',
                 '/admin/round/%s/finalize' % round_id,
                 {'threshold': 1.5}, as_user='LilyOfTheWest', error_code=400)

    assert resp['status'] == 'failure'
    assert 'threshold must be between 0.0 and 1.0' in resp['errors']

    resp = fetch('coordinator: try finalize with negative threshold',
                 '/admin/round/%s/finalize' % round_id,
                 {'threshold': -0.5}, as_user='LilyOfTheWest', error_code=400)

    assert resp['status'] == 'failure'
    assert 'threshold must be between 0.0 and 1.0' in resp['errors']
