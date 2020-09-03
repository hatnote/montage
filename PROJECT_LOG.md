# Montage Project Log

## 2020-03-08

Kicked off new FE for admins, based on Svelte.

* View campaign list
* View individual campaign
* Create campaign

### Remaining items

- [ ] Separate bundle.js and bundle.css
- [ ] Babel backport to IE 11 perhaps: https://blog.az.sg/posts/svelte-and-ie11/
  - [ ] Lodewijk says tell them to use the supported browser (coordinators at least)
- [ ] Other rollup improvements: https://medium.com/@camille_hdl/rollup-based-dev-environment-for-javascript-part-1-eab8523c8ee6

#### Svelte components

- [ ] Sentry integration for the frontend
- [ ] Refine campaign list
  - [ ] Link to active round on campaign list
- [ ] Refine single campaign page (add a bit of round detail)
  - [ ] Edit functionality
  - [ ] Style?
  - [ ] Show jurors
  - [ ] Show description (?)
  - [ ] # of files (?) 
  - [ ] Active/inactive styling
- [ ] Refine round page
  - [ ] Edit functionality
  - [ ] Style?
  - [ ] Button to download all entries, all reviews, all votes (?)
  - [ ] If closed: Results summary
  - [ ] Should there be a summary of the campaign, somewhere on this page?
- [ ] Create round
  - [ ] Create initial round
  - [ ] Advance round (same component as above)
- [ ] Show campaigns by series
  - [ ] Add a column
  - [ ] Backfill series (take country into account)
- [ ] Campaign opendate/closedate should be in UTC or AoE
  - [ ] Backend expects hour
- [ ] Create view page
- [ ] Create entry list page, re disqualify and requalify images
  - [ ] Need a paginated datatable component
- [ ] User page (?)

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
