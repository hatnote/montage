# TODO

New TODOs

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
