# -*- coding: utf-8 -*-
"""
Regression tests for bugs fixed in recent PRs.

Each test class is named after the issue it covers, making it easy
to trace a test failure back to the original bug report.
"""

from __future__ import absolute_import
from __future__ import print_function

import io
import datetime

import pytest
import responses

from montage.loaders import get_entries_from_gsheet
from montage.rdb import (
    Base, User, Campaign, Round, RoundEntry, Entry, Favorite,
    ACTIVE_STATUS, CANCELLED_STATUS,
)
from montage.utils import get_threshold_map

from .conftest import (
    FIXTURE_FILE_INFOS,
    FIXTURE_FULL_CSV,
    FIXTURE_FILENAME_CSV,
    TOOLFORGE_FILE_URL,
    build_filename_csv,
)

# ---------------------------------------------------------------------------
# Issue #531 -- download_round_entries_csv IndexError on empty round
# ---------------------------------------------------------------------------

class TestDownloadEntriesCsvEmptyRound:
    """
    Regression test for #531.

    Before the fix, `download_round_entries_csv` called `entry_infos[0].keys()`
    which raised IndexError when the round had zero entries.
    """

    def test_to_export_dict_keys_are_stable(self):
        """The fallback field list must match what Entry.to_export_dict() returns."""
        from montage.rdb import Entry
        # Build a minimal Entry instance (no DB required for this check)
        e = Entry.__new__(Entry)
        e.id = 1
        e.name = 'Test_image.jpg'
        e.mime_major = 'image'
        e.mime_minor = 'jpeg'
        e.width = 1024
        e.height = 768
        e.upload_user_id = 42
        e.upload_user_text = 'TestUser'
        e.upload_date = datetime.datetime(2020, 1, 1)

        keys = set(e.to_export_dict().keys())
        expected = {'img_id', 'img_name', 'img_major_mime', 'img_minor_mime',
                    'img_width', 'img_height', 'img_user', 'img_user_text', 'img_timestamp'}
        assert keys == expected, (
            'Entry.to_export_dict() keys changed -- update the fallback in '
            'download_round_entries_csv too (see #531)'
        )


# ---------------------------------------------------------------------------
# Issue #526/#527 -- fave/unfave cross-campaign collision
# ---------------------------------------------------------------------------

class TestFaveCrossCampaignCollision:
    """
    Regression tests for #526 and #527.

    Before the fix, fave() looked up existing Favorites only by
    (entry_id, user) -- ignoring campaign_id.  If the same image
    appeared in two campaigns, the wrong fave record was activated.

    unfave() used .one() which raised NoResultFound if the fave was
    never created (e.g. due to a previous collision).
    """

    def test_fave_query_scopes_campaign_id(self):
        """
        Verify the fave() method filters on campaign_id.

        We inspect the source to confirm `campaign_id` is in the filter_by
        call.  This is intentionally a documentation-style test -- if
        someone removes the campaign_id filter in the future, this test
        will fail and force them to justify the change.
        """
        import inspect
        from montage.rdb import JurorDAO
        src = inspect.getsource(JurorDAO.fave)
        assert 'campaign_id' in src, (
            'JurorDAO.fave() must filter Favorites by campaign_id '
            'to prevent cross-campaign collisions (see #526)'
        )

    def test_unfave_uses_one_or_none(self):
        """
        Verify unfave() uses .one_or_none() instead of .one().

        .one() raises NoResultFound if no matching row exists; .one_or_none()
        returns None and allows a graceful no-op (see #527).
        """
        import inspect
        from montage.rdb import JurorDAO
        src = inspect.getsource(JurorDAO.unfave)
        assert '.one()' not in src, (
            'JurorDAO.unfave() must use .one_or_none() not .one() '
            'to avoid NoResultFound on missing faves (see #527)'
        )
        assert '.one_or_none()' in src


# ---------------------------------------------------------------------------
# Issue #523 -- active pdb.set_trace() in production code
# ---------------------------------------------------------------------------

class TestNoPdbInProductionCode:
    """
    Regression test for #523.

    Active `pdb.set_trace()` calls in non-test code will freeze a
    production server.  This test scans the relevant modules and fails
    if any live breakpoints are found.
    """

    MODULES_TO_CHECK = [
        'montage.mw',
        'montage.labs',
        'montage.admin_endpoints',
        'montage.rdb',
    ]

    def _get_source(self, module_name):
        import importlib
        import inspect
        mod = importlib.import_module(module_name)
        return inspect.getsource(mod)

    def test_no_active_pdb_set_trace(self):
        for module_name in self.MODULES_TO_CHECK:
            src = self._get_source(module_name)
            # allow commented-out ones (# import pdb; pdb.set_trace())
            # but catch any un-commented live call
            live_lines = [
                line for line in src.split('\n')
                if 'pdb.set_trace()' in line and not line.lstrip().startswith('#')
            ]
            assert not live_lines, (
                'Found active pdb.set_trace() in %s (see #523):\n  %s'
                % (module_name, '\n  '.join(live_lines))
            )

    def test_no_bare_except(self):
        """bare `except:` swallows KeyboardInterrupt and SystemExit."""
        import importlib
        import inspect
        mod = importlib.import_module('montage.admin_endpoints')
        src = inspect.getsource(mod)
        bare = [
            line for line in src.split('\n')
            if line.lstrip().startswith('except:')
        ]
        assert not bare, (
            'Found bare except: in montage.admin_endpoints (see #523):\n  %s'
            % '\n  '.join(bare)
        )


# ---------------------------------------------------------------------------
# Issue #542 -- slugify crash when rnd.name is None
# ---------------------------------------------------------------------------

class TestSlugifyNullSafety:
    """
    Regression test for #542.

    download_results_csv called slugify(rnd.name) without guarding
    against None.  slugify(None) raises AttributeError.
    """

    def test_slugify_null_guard_present(self):
        """download_results_csv must not call slugify directly on rnd.name."""
        import inspect
        from montage import admin_endpoints
        src = inspect.getsource(admin_endpoints.download_results_csv)
        # The old code: slugify(rnd.name, ...)
        # The fixed code: round_name = rnd.name or 'unnamed-round'; slugify(round_name, ...)
        assert 'slugify(rnd.name' not in src, (
            'download_results_csv calls slugify(rnd.name, ...) directly. '
            'Add a null-guard: round_name = rnd.name or "unnamed-round" (see #542)'
        )
        assert 'rnd.name or' in src, (
            'download_results_csv missing null-guard for rnd.name (see #542)'
        )


# ---------------------------------------------------------------------------
# Issue #517 -- load_partial_csv fallback passing wrong type
# ---------------------------------------------------------------------------

class TestLoadPartialCsvFallback:
    """
    Regression test for #517.

    The fallback path in get_entries_from_gsheet called
    load_partial_csv(resp) passing a raw requests.Response, not a
    DictReader.  This always caused TypeError, making the fallback
    permanently broken.
    """

    @responses.activate
    def test_partial_csv_fallback_resolves_via_name_list(self):
        """
        A filename-only Google Sheet should succeed via the load_partial_csv
        -> load_name_list path (not fall through to an error).
        """
        gsheet_url = 'https://docs.google.com/spreadsheets/d/1Nqj-JsX3L5qLp5ITTAcAFYouglbs5OpnFwP6zSFpa0M/edit?usp=sharing'
        csv_url = 'https://docs.google.com/spreadsheets/d/1Nqj-JsX3L5qLp5ITTAcAFYouglbs5OpnFwP6zSFpa0M/gviz/tq?tqx=out:csv'

        responses.add(
            responses.GET,
            csv_url,
            body=FIXTURE_FILENAME_CSV,
            status=200,
            content_type='text/csv',
        )
        responses.add(
            responses.POST,
            TOOLFORGE_FILE_URL,
            json={'file_infos': FIXTURE_FILE_INFOS, 'no_info': []},
            status=200,
        )

        imgs, warnings = get_entries_from_gsheet(gsheet_url, source='remote')
        assert len(imgs) == len(FIXTURE_FILE_INFOS)
        assert isinstance(imgs, list)

    def test_load_partial_csv_source_not_passed_response_directly(self):
        """
        Verify the fix is in place: load_partial_csv must be called with
        a DictReader (not the raw Response object).
        """
        import inspect
        from montage import loaders
        src = inspect.getsource(loaders.get_entries_from_gsheet)
        assert 'load_partial_csv(resp)' not in src, (
            'get_entries_from_gsheet passes raw Response to load_partial_csv '
            '-- wrap it in a DictReader first (see #517)'
        )
