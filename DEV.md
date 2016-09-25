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

# TODO

A bit of space for dev bookkeeping.

## Backend

* Tasks are generated but are not readable/completable through the API

## Frontend

* Pretty much all of it! :)

# Workflow

A rough draft of Montage's workflow:

## Details

* Admins add coordinators (by wiki username)
* Coordinators have permissions to create campaigns and add other
  coordinators to specific campaigns
* Coordinators create a round within a campaign, and manually assign
  jurors, by wiki username, to each round
* The first round can import from CSV and categories
* Early rounds are known as elimination rounds, where coordinators can
  choose between thumbs up/down or five star rating system, with
  configurable quorum values (number of jurors who must rate each
  entry before it is considered rated)
* When all vote quorums are met, a new round can be created with the
  results of a previous round. This closes the round, enabling
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
* If we see mysql connection issues, consider: http://docs.sqlalchemy.org/en/latest/core/pooling.html#disconnect-handling-pessimistic

## Audience

Montage is targeted at new groups adopting the Wiki Loves * contest process.

## Design features

* Avoids having multiple simultaneous active rounds per campaign
* Avoids error-prone download/upload CSV approach
