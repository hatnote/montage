# Montage Project Log

## 2020-03-01

* Made setup.py to make montage installable (not for pypi upload!)
* Merged admin CLI changes (still need to integrate into package and make entrypoint)
* Migrated system test into tox + pytest (in prep for more tests + py3 conversion)
* Added coverage report (time of writing: 75%)
* Read up on new toolforge setup, make sure to restart with:
  `webservice --cpu 1 --mem 4 python2 restart`
* requirements.in and requirements.txt working

## TODO

* Better dev docs
