"""Finalizing a campaign: POST /admin/campaign/<id>/finalize (#644)."""

from montage.tests.test_import_entries import (  # noqa: F401 (fixtures)
    montage_app, api_client, coord_client, make_file_infos, mock_category,
    new_round, import_category, db_query, COORD, OPEN_DATE)

JURORS = ['Slaporte', 'MahmoudHashemi', 'Effeietsanders']


def _post(client, desc, url, **kw):
    return client.fetch(desc, url, {'post': True}, as_user=COORD, **kw)


def _one(app, sql, **params):
    return db_query(app, sql, **params)[0]


def _summaries(app, cid):
    return _one(app, 'SELECT COUNT(*) AS n FROM results_summaries'
                     ' WHERE campaign_id = :cid', cid=cid)['n']


def _campaign_status(app, cid):
    return _one(app, 'SELECT status FROM campaigns WHERE id = :cid', cid=cid)['status']


def _ranking_campaign(client, mock_external_apis, name):
    """A campaign with one active ranking round of 3 files and one ballot in."""
    series_id = client.fetch('get default series', '/series')['data'][0]['id']
    cid = client.fetch('organizer: create campaign', '/admin/add_campaign',
                       {'name': name, 'coordinators': [COORD],
                        'open_date': OPEN_DATE.isoformat(),
                        'close_date': '2016-01-01T00:00:00',
                        'url': 'http://hatnote.com', 'series_id': series_id},
                       as_user=COORD)['data']['id']
    rid = client.fetch('coordinator: create ranking round',
                       '/admin/campaign/%s/add_round' % cid,
                       {'name': name + ' r1', 'vote_method': 'ranking',
                        'deadline_date': '2016-10-15T00:00:00', 'jurors': JURORS},
                       as_user=COORD)['data']['id']
    mock_category(mock_external_apis, make_file_infos(name, 3))
    import_category(client, rid)
    _post(client, 'coordinator: activate round', '/admin/round/%s/activate' % rid)
    tasks = client.fetch('juror: tasks', '/juror/round/%s/tasks' % rid,
                         as_user=JURORS[0])['data']['tasks']
    client.fetch('juror: submit ballot', '/juror/round/%s/tasks/submit' % rid,
                 {'ratings': [{'task_id': t['id'], 'value': i}
                              for i, t in enumerate(tasks)]},
                 as_user=JURORS[0])
    return cid, rid


def test_finalize_after_ranking_round_finalized_with_its_own_button(
        montage_app, coord_client, mock_external_apis):
    # #644: finalizing the ranking round with the round's own button
    # used to leave the campaign impossible to finalize
    cid, rid = _ranking_campaign(coord_client, mock_external_apis, 'fb')
    _post(coord_client, 'coordinator: finalize ranking round', '/admin/round/%s/finalize' % rid)
    round_close = _one(montage_app, 'SELECT close_date FROM rounds WHERE id = :rid',
                       rid=rid)['close_date']

    resp = _post(coord_client, 'coordinator: finalize campaign',
                 '/admin/campaign/%s/finalize' % cid)
    assert resp['status'] == 'success'
    assert _campaign_status(montage_app, cid) == 'finalized'
    assert _summaries(montage_app, cid) == 1
    # the round keeps the close date it was finalized with
    assert _one(montage_app, 'SELECT close_date FROM rounds WHERE id = :rid',
                rid=rid)['close_date'] == round_close

    report = coord_client.fetch('coordinator: campaign report',
                                '/admin/campaign/%s/report' % cid, as_user=COORD)
    assert len(report['data']['winners']) == 3


def test_finalize_twice_refused(montage_app, coord_client, mock_external_apis):
    cid, rid = _ranking_campaign(coord_client, mock_external_apis, 'ft')
    _post(coord_client, 'coordinator: finalize campaign', '/admin/campaign/%s/finalize' % cid)

    resp = _post(coord_client, 'coordinator: finalize campaign again',
                 '/admin/campaign/%s/finalize' % cid, error_code=400)
    assert b'already finalized' in resp.get_data()
    assert _summaries(montage_app, cid) == 1


def test_reopen_and_finalize_again_keeps_one_summary(
        montage_app, coord_client, mock_external_apis):
    cid, rid = _ranking_campaign(coord_client, mock_external_apis, 'fr')
    _post(coord_client, 'coordinator: finalize campaign', '/admin/campaign/%s/finalize' % cid)
    _post(coord_client, 'coordinator: reopen campaign', '/admin/campaign/%s/reopen' % cid)

    _post(coord_client, 'coordinator: finalize campaign again',
          '/admin/campaign/%s/finalize' % cid)
    assert _campaign_status(montage_app, cid) == 'finalized'
    assert _summaries(montage_app, cid) == 1
    coord_client.fetch('coordinator: campaign report',
                       '/admin/campaign/%s/report' % cid, as_user=COORD)


def test_finalize_refused_when_last_round_is_yesno(
        montage_app, coord_client, mock_external_apis):
    # finalizing stores results, which need a ranking round; a campaign
    # that ends on a yes/no round is archived instead
    rid = new_round(coord_client, 'fy')
    mock_category(mock_external_apis, make_file_infos('fy', 3))
    import_category(coord_client, rid)
    cid = _one(montage_app, 'SELECT campaign_id FROM rounds WHERE id = :rid',
               rid=rid)['campaign_id']
    _post(coord_client, 'coordinator: activate round', '/admin/round/%s/activate' % rid)
    _post(coord_client, 'coordinator: finalize round', '/admin/round/%s/finalize' % rid)

    resp = _post(coord_client, 'coordinator: finalize campaign',
                 '/admin/campaign/%s/finalize' % cid, error_code=400)
    assert b'archive it instead' in resp.get_data()
    assert _campaign_status(montage_app, cid) == 'active'
    assert _summaries(montage_app, cid) == 0
