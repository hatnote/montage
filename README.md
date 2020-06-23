![Logo](https://i.imgur.com/EZD3p9r.png)

## Montage
*Photo evaluation tool for and by Wiki Loves competitions*

Round-based photo evaluation is a crucial step in the "Wiki Loves"
series of photography competitions. Montage provides a configurable
workflow that adapts to the conventions of all groups.

* [montage on Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:Montage)
* [montage on Phabricator](https://phabricator.wikimedia.org/project/view/2287/)


## Testing

`pip install tox` into your virtualenv, then `tox`.

## Deployment

Ensure you have the necessary libraries by running `pip install -r requirements-dev.txt`
in a virtualenv of your choosing.

1. Ensure all changes are committed
2. Run the tests (`tox`)
3. Deploy to the dev instance with `fab deploy`. Ensure the script
   runs successfully.
   1. Check that the [the dev site](https://montage-dev.toolforge.org/meta/)
   came back up fine.
   2. Log in and test things out.
   3. Check the [montage-dev sentry (devlabs)](https://sentry.io/organizations/hatnote/issues/?environment=devlabs&project=3532775)
4. Use [the audit log](https://tools.wmflabs.org/montage/v1/logs/audit)
   to check that the production instance isn't in active use.
5. Deploy to the production instance with `fab deploy:tool=montage`
   1. Check that the [the production site](https://tools.wmflabs.org/montage/meta/)
      came back up fine.
   2. Log in and test things out.
   3. Check the [montage sentry (prod)](https://sentry.io/organizations/hatnote/issues/?environment=prod&project=3532775)

Some tips (at the time of writing):

* `fab deploy` without arguments will deploy `master` to `montage-dev`.
  * To change this, use a command of this format:
    `fab deploy:branch=other-branch,tool=montage-beta`
  * It will fail with a helpful message if your branch is not sync'd
    with origin. Push those commits!
* If you see a huge golang stack trace from `fab deploy`, it's likely
  [this bug](https://phabricator.wikimedia.org/T219070). These seem to
  fix themselves, come back later if you can, otherwise check out the
  thread for details on using `GOMAXPROCS`.
* All this only deploys the backend for now.
