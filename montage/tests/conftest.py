# -*- coding: utf-8 -*-
"""
Shared test fixtures.

Mocks all external HTTP calls (Toolforge API, Google Sheets, Wikimedia
API) so tests run without network access.  The ``responses`` library
intercepts at the ``requests`` adapter level; any unmocked call raises
``ConnectionError`` (passthrough=False, the default).
"""

from __future__ import absolute_import

import json
import re
import os
import pytest

import responses as responses_lib

from urllib.parse import parse_qs, urlparse
from sqlalchemy import create_engine
from boltons.fileutils import mkdir_p
from montage import utils
from montage.app import create_app, STATIC_PATH
from montage.rdb import Base
from montage.tests.test_web_basic import MontageTestClient

# ---------------------------------------------------------------------------
# URLs exactly as constructed by montage code
# ---------------------------------------------------------------------------
TOOLFORGE_CATEGORY_URL = 'https://montage.toolforge.org/v1/utils//category'
TOOLFORGE_FILE_URL = 'https://montage.toolforge.org/v1/utils//file'

# Matches any Google Sheets CSV-export URL regardless of doc ID.
GSHEET_CSV_URL_RE = re.compile(
    r'https://docs\.google\.com/spreadsheets/d/.+/gviz/tq\?tqx=out:csv'
)

# Matches any Wikimedia API user-lookup call.
MW_API_URL_RE = re.compile(
    r'https://commons\.wikimedia\.org/w/api\.php\?.*'
)

# ---------------------------------------------------------------------------
# Fixture data -- 20 synthetic entries with resolution > 2 megapixels.
# Enough entries to survive disqualification AND give every juror >=2
# tasks regardless of random.shuffle ordering during task allocation.
# ---------------------------------------------------------------------------


def _generate_file_infos(n):
    """Build *n* unique file-info dicts with high resolution."""
    infos = []
    for i in range(n):
        infos.append({
            'img_name': 'Test_WLM_2015_image_%03d.jpg' % (i + 1),
            'img_major_mime': 'image',
            'img_minor_mime': 'jpeg',
            'img_width': '3264',
            'img_height': '2448',  # 3264*2448 = 7,990,272 > 2M
            'img_user': '5193613',
            'img_user_text': 'Khoshamadgou',
            # All timestamps after campaign open_date (2015-09-01)
            'img_timestamp': '201509060%05d' % (20000 + i),
        })
    return infos


FIXTURE_FILE_INFOS = _generate_file_infos(20)

# Entry returned for the single-filename import in test_web_basic.py
SELECTED_FILE_INFO = {
    'img_name': u'Reynisfjara, Su\u00f0urland, Islandia, 2014-08-17, DD 164.JPG',
    'img_major_mime': 'image',
    'img_minor_mime': 'jpeg',
    'img_width': '4928',
    'img_height': '3280',
    'img_user': '12345',
    'img_user_text': 'TestUploader',
    'img_timestamp': '20140817120000',
}

CSV_FULL_COLS = [
    'img_name', 'img_major_mime', 'img_minor_mime',
    'img_width', 'img_height', 'img_user',
    'img_user_text', 'img_timestamp',
]


def build_full_csv(file_infos=None):
    """Build a CSV string with all required columns from file_info dicts."""
    if file_infos is None:
        file_infos = FIXTURE_FILE_INFOS
    lines = [','.join(CSV_FULL_COLS)]
    for fi in file_infos:
        lines.append(','.join(str(fi[c]) for c in CSV_FULL_COLS))
    return '\n'.join(lines) + '\n'


def build_filename_csv(file_infos=None):
    """Build a CSV string with only a 'filename' column."""
    if file_infos is None:
        file_infos = FIXTURE_FILE_INFOS
    lines = ['filename']
    for fi in file_infos:
        lines.append(fi['img_name'])
    return '\n'.join(lines) + '\n'


FIXTURE_FULL_CSV = build_full_csv()
FIXTURE_FILENAME_CSV = build_filename_csv()


# ---------------------------------------------------------------------------
# Disable pdb in error handler -- devtest sets debug_errors=True which
# calls pdb.post_mortem() on unhandled exceptions.  Under pytest's output
# capture this crashes with OSError.  Patching pdb to no-ops is safe
# because no test relies on interactive debugging.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _disable_pdb(monkeypatch):
    monkeypatch.setattr('pdb.set_trace', lambda *a, **kw: None)
    monkeypatch.setattr('pdb.post_mortem', lambda *a, **kw: None)

# ---------------------------------------------------------------------------
# Wikimedia API callback -- returns a plausible user record for any username
# ---------------------------------------------------------------------------
def _wikimedia_user_callback(request):
    """Return a mock globalallusers response matching the requested username."""
    parsed = urlparse(request.url)
    params = parse_qs(parsed.query)
    username = params.get('agufrom', ['Unknown'])[0]
    # Deterministic fake user ID derived from username
    user_id = abs(hash(username)) % 10**8
    body = json.dumps({
        'query': {
            'globalallusers': [
                {'name': username, 'id': str(user_id)}
            ]
        }
    })
    return (200, {}, body)


# ---------------------------------------------------------------------------
# Fixture: mock_external_apis
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_external_apis():
    """Activate ``responses`` and register mocks for every external endpoint.

    Covers:
    - Toolforge category lookup  (POST /v1/utils//category)
    - Toolforge file lookup      (POST /v1/utils//file)
    - Google Sheets CSV export   (GET  docs.google.com/spreadsheets/...)
    - Wikimedia user lookup       (GET  commons.wikimedia.org/w/api.php)

    Any request to an unregistered URL raises ``ConnectionError``,
    ensuring no live HTTP traffic leaks from tests.
    """
    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        # -- Toolforge category endpoint --
        rsps.add(
            responses_lib.POST,
            TOOLFORGE_CATEGORY_URL,
            json={'file_infos': FIXTURE_FILE_INFOS, 'no_info': []},
            status=200,
        )

        # -- Toolforge file-lookup endpoint --
        # Returns both fixture entries and the single "selected" entry so
        # that both bulk-filename and single-filename imports succeed.
        rsps.add(
            responses_lib.POST,
            TOOLFORGE_FILE_URL,
            json={
                'file_infos': FIXTURE_FILE_INFOS + [SELECTED_FILE_INFO],
                'no_info': [],
            },
            status=200,
        )

        # -- Google Sheets CSV export (any doc ID) --
        rsps.add(
            responses_lib.GET,
            GSHEET_CSV_URL_RE,
            body=FIXTURE_FULL_CSV,
            status=200,
            content_type='text/csv',
        )

        # -- Wikimedia user-lookup API --
        # Called by get_mw_userid() when creating new users.
        rsps.add_callback(
            responses_lib.GET,
            MW_API_URL_RE,
            callback=_wikimedia_user_callback,
        )

        yield rsps

@pytest.fixture
def montage_app(tmpdir):
    config = utils.load_env_config(env_name='devtest')
    config['db_url'] = config['db_url'].replace('///', '///' + str(tmpdir) + '/')
    engine = create_engine(config['db_url'])
    Base.metadata.create_all(engine)

    index_path = STATIC_PATH + '/index.html'
    if not os.path.exists(index_path):
        mkdir_p(STATIC_PATH)
        with open(index_path, 'w') as f:
            f.write('<html><body>just for tests</body></html>')

    return create_app('devtest', config=config)


@pytest.fixture
def api_client(montage_app):
    client = MontageTestClient(montage_app, base_path='/v1')
    client.set_session_cookie(montage_app.resources['config']['dev_local_cookie_value'])
    return client
