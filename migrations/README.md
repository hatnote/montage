# Alembic adoption strategy

*(April 2020)*

* Create db management CLI
  * Create DB
    * Should do nothing if db already exists
  * Migrate DB
    * Should autocreate db if it doesn't exist
    * --no-autocreate / --fail-if-no-db
  * Check DB
    * --stamp mark as up to date?
  * Drop DB

Because we have different environments in different states, we need to
figure out how to get them all synced. Luckily, they're all on the
same git history, so we can just start at the oldest, get the git
commit, check it out locally, and create the migrations from
there. (Might be able to make use of conditional or multihead
migrations here)

If an environment is up to date with master (passes check db), then
stamp it.

1. Add naming scheme
    * Had to add names to Boolean fields (because they're constraints,
      not a natively-supported column type in sqlite/mysql)


## Questions

* Can alembic be used to check DB before startup?
