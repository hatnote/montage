# Running Montage

*This document is a work in progress, as Montage is itself incomplete
 at the time of writing.*

## Setting up Montage

Montage can be run locally for development, backed by a
SQLite database.

[Install virtualenv and virtualenvwrapper](http://docs.python-guide.org/en/latest/dev/virtualenvs/),
then create a new virtualenv with something like `mkvirtualenv
montage`. Then, with the virtualenv activated:

1. Install dependencies: `pip install -r requirements.txt`
2. Some initial data can be loaded by running `python run_data_test.py`
3. The application can be started with `python montage/server.py`

Almost all endpoints (except for OAuth and `/static/`) return JSON as
long as the proper Accept header is set (done by most libraries) or
`format=json` is passed in the query string.

### Building the interface

To build the front-end app, go to `/client/` and install dependencies:

```
npm install
```

Then run the app:

```
npm run start
```

# TODO

A bit of space for dev bookkeeping.

## Backend

* Closing behaviors
    * Compute ranking winners
* Permissions cleanup for admin endpoints
     * e.g., organizer checks
* Check for resource existence instead of raising 500s (e.g., campaign endpoints)
* Logging and timing
* Locking
* Undo rating submit
* Add indexes
* Switch request_dict to Werkzeug MultiDict for BadRequest behavior
* fix `one_or_none` getters
...

* DAO.add_juror doesn't add jurors really
* category import
* lookup round + check round permissions
* endpoint should return progress info (/admin/round/<id>, /admin)
* Campaign + first Round as single step?
* Blacklisted user disqualification
* Load dates (?)
* create round from previous round

## Frontend

* Make URLs configurable for different backend paths (e.g., Labs versus localhost)
* Submit ratings
* Submit rankings
* Interfaces for closing rounds
* Undo rating submit
* Where to show directions in interface? ("show these directions next time"/cookie)

Ratings closing round interface:

* Specify threshold (1, 2, 3, 4, 5 stars, etc.)

# Workflow

A rough draft of Montage's workflow:

## Details

* Maintainers add organizers (by wiki username)
* Organizers have permissions to create campaigns and add other
  coordinators to campaigns created by them.
* Coordinators (and organizers) create a round within a campaign, and
  manually assign jurors, by wiki username, to each round
* The first round can import from CSV and categories
* Early rounds are known as elimination rounds, where coordinators can
  choose between Yes/No or Five-Star rating system, with
  configurable quorum values (number of jurors who must rate each
  entry before it is considered rated)
* When all voting tasks are complete, a new round can be created with
  the results of a previous round. This closes the round, enabling
  downloading of results and votes.
* Coordinators can rebalance remaining rating tasks (through a
  reassignment flow) to help meet deadlines. Jurors can be
  added/removed for purposes of the reassignment.
* For rounds with star ranking systems, the closing criterion is
  configurable at the end of the round. Coordinators can choose how
  many stars are necessary to qualify for the next round.
* After the elimination rounds, entries go through one (or more?)
  ranking rounds. A ranking round can only be initiated once an
  elimination round results in fewer than, e.g., 50 entries. (exact
  number configurable by admins, per limits of montage's UI)
* Ranking rounds require all added jurors to vote.
* A campaign cannot be finalized and considered successful without at
  least one ranking round.

## Summary

* Montage administrators add coordinators
* Coordinators create campaigns
* Coordinators add jurors and images to an initial round, typically an
  elimination round, using a pass/nopass or star-based rating system.
* Jurors complete all of their assigned voting tasks
* Coordinators create new elimination rounds, carrying over from
  previous rounds, until fewer than 50 images remain
* Once there are fewer than 50 images, coordinators can create a
  ranking-based round (order-based voting)
* When at least one ranking-based round is complete, coordinators may
  close out the campaign and download the final results.

## Notes on closing

Generally speaking, compared to some alternatives, Montage streamlines
many steps into cohesive actions that are designed to be less
error-prone. Nowhere is this more apparent than during closing. There
are three round types and while they share some behaviors, behind the
scenes, there are some differences.

### General closing

A round cannot be closed until all assigned tasks are completed by
jurors. Once tasks are completed, campaign coordinators will see the
option to complete the round.

TODO: need to document how concurrent-closing race conditions are mitigated.

The coordinator closing the round is presented with an interface to
choose the round closing criteria. The criteria will vary by type of
round.

If the criteria selected brings the advancing set of images under a
certain global threshold, the campaign can be closed (separate
interfaces for this?)

### YesNo rounds

The coordinator is presented with a histogram of responses. A "no"
vote is computed as 0.0 and a "yes" vote is computed as 1.0.

The coordinator must be made to understand how many images will
advance based on their selection of threshold.

An ideal first round would be YesNo with a quorum of 2, with a
threshold of 0.5, meaning that if any image had at least one juror
that saw merit, it would go to the next round.

### Rating rounds

Similar to YesNo rounds, the coordinator again sees a histogram of
juror responses. 1-star ratings are 0.0, 2-star are 0.25, and so on,
until 5-star ratings, worth 1.0. (Should this be 0.2-1.0 instead?)

### Ranking rounds

No histogram is displayed, but rather the coordinator must pick an X
for "Top X". The international round needs at least ten. Data-wise we
will have the ability to recompute a ranked list for all entries into
a ranked round.

Note that there is not much sense in a round after a ranked round. The
nature of ranking is such that runoffs are not necessary. The only
possible use would be to have a different set of jurors, but that
sounds pretty out of order.

## Other

* Each round can have CSV of its inputs (images) dumped at any point,
  as well as a CSV of all votes, once it is complete (a new round is
  created or the campaign is finalized).
* Coordinators can initiate a reassignment for any open round
  (add/remove jurors, change quorum value)
* Only one round per campaign is open at a time
* Coordinators can control multiple campaigns
* While a round is open a juror can edit their votes

## Later

* Ranking rounds can include nominations for special prizes (better
  run as a separate campaign that pulls from the round of another
  campaign?)

## Audience

Montage is targeted at new groups adopting the Wiki Loves * contest process.

## Design features

* Avoids having multiple simultaneous active rounds per campaign
* Avoids error-prone download/upload CSV approach
