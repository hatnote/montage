# Montage Project Log

## 2020-03-01

* Made setup.py to make montage installable (not for pypi upload!)
* Merged admin CLI changes (still need to integrate into package and make entrypoint)
* Migrated system test into tox + pytest (in prep for more tests + py3 conversion)
* Added coverage report (time of writing: 75%)
* Read up on new toolforge setup, make sure to restart with:
  `webservice --cpu 1 --mem 4000Mi python2 restart`
* requirements.in and requirements.txt working
* Added CI and coverage
  * https://travis-ci.org/hatnote/montage
  * https://codecov.io/gh/hatnote/montage

## TODO

### 2020 Technical Roadmap

* Admin tools refactor
  * Integrate admin tools into montage package
  * Make montage installable
* Switch to in-process integration tests + unit tests instead of big
  system test.
* Python 3 migration
  * Upgrade dependencies
  * Add tests + coverage
  * Update syntax
* Migrate to k8s
* Deploy script?
* Sentry integration?
* Dynamic assignment
* Archiving?
* Better dev docs
