# TODO

New TODOs
* Add maintainer view for a round's DQed entries
* Translate "score" on threshold selection back into appropriate
  units. For instance, on yesno rounds with quorum of 4, instead of
  >0.5, say "at least two yeses". Similarly, but not quite the same,
  instead of >=0.75, say "an average score of at least 4 stars."
* Ranking round limit to 100 (`create_ranking_round` not used?)
* Eliminate task table, switch to status column
* Be able to deactivate coordinators
* friggin indexes
* Randomize ranking round task order

## Final report format

* Campaign details
  * Campaign title
  * Open and close dates
  * Total number of submissions
  * Coordinator names
  * Juror names
* Winning entries
  * Rank
  * Title, uploader, upload date, description
  * Juror ranks
  * Juror comments
* Round timeline (for each round:)
  * Round type
  * Open date
  * Close date
  * Number of entries
  * Number of jurors
  * Number of votes
  * Distribution
  * Final threshold
  * Quorum
* Report creation
  * "Organized with Montage"
  * Render date
  * (render duration in html comment)

## TMP

```
user = session.query(User).first()
cdao = CoordinatorDAO(rdb_session=session, user=user)
campaign = cdao.get_campaign(1)
cdao.get_campaign_report(campaign)

```
# TODOs from DEV.md

A bit of space for dev bookkeeping.

## Backend

* Check for resource existence instead of raising 500s (e.g., campaign endpoints)
* Logging and timing
* Locking
* Add indexes
* Switch request_dict to Werkzeug MultiDict for BadRequest behavior
* fix `one_or_none` getters
...

* DAO.add_juror doesn't add jurors really
* lookup round + check round permissions
* endpoint should return progress info (/admin/round/<id>, /admin)
* Campaign + first Round as single step?
* Blacklisted user disqualification
* Load dates (?)
* create round from previous round

... [stephen on the train]

* Endpoint to view reviews
* Handle NONE user in UserDAO
* check entry existance before getting from db or remote source
* what should happen when someone closes a round with open votes?
*

## Frontend

* Make URLs configurable for different backend paths (e.g., Labs versus localhost)
* Interfaces for closing rounds
* Where to show directions in interface? ("show these directions next time"/cookie)

Ratings closing round interface:

* Specify threshold (1, 2, 3, 4, 5 stars, etc.)


## Cron job

* Look up open rounds
* Look up round sources with open rounds
* Ignore "round" and "selection" methods
* For gists, redownload the gist and add_round_entries as need be
* For categories, recheck the db and add_round_entries as need be
* For removed entries, do nothing (current behavior) or disqualify

## Research data collection opt-in

* Set by coordinator on campaign (on creation)
* Seen by users on campaign tile
* Anonymized csv voting download
  * Row per vote in CSV + Round column
* Endpoint for setting/unsetting value
  * Only settable from start/before votes?
  * Unsetting may be useful
* Inherent in coordinator opt-in language: "By checking this you
  assert that all jurors have been informed/consented that anonymized
  voting data will may be used for research."
