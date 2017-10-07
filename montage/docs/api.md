# API

[TOC]

## /v1/admin
Return a list of campaigns available to the user

  - Function: [get_index](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L551) (admin_endpoints.py)
  - Method: GET


### Parameters
  - None

### Response
  - `data`: list of [`campaign details`](#campaign-details) dictionaries
  - `status`: success or failure
  - `errors`: description of the failure (if any)
    
### Errors
  - 403: not logged in
  - 404: not a coordinator on any campaigns (TODO)

## /v1/admin/add_series
Add a new series, so you can connect a group of campaigns (e.g., Wiki Loves Monuments, Wiki Loves Earth, etc)

  - Function: [add_series](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L121) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `name`
  - `description`
  - `url`
  - `status` (optional, default is active)

### Response
  - `data`: single [`series info`](#series-info) dictionary (TODO)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not an organizer

## /v1/admin/series/`<series_id:int>`/edit
Edit a series

  - Function: [edit_series](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L133) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `id` (in path)
  - `name` (optional)
  - `description` (optional)
  - `url` (optional)
  - `status` (optional)

### Response
  - `data`: single [`series info`](#series-info) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)
    
### Errors
  - 403: not an organizer
  - 404: series does not exist

## /v1/admin/add_organizer
Add a user as organizer to Montage. Organizers can create/edit a series, campaign, and more.

  - Function: [add_organizer](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L769) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `username`
  
### Response
  - `data`: (TODO: this should be standardized with a [`user info`](#user-info) dictionary)
    - `username`
    - `last_active_date`
  - `status`: success or failure
  - `errors`: description of the failure (if any)
    
### Errors
  - 403: not a maintainer
  - 404: user does not exist (TODO)

## /v1/admin/remove_organizer
Remove a user as organizer in Montage

  - Function: [remove_organizer](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L794) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `username`

### Response
  - `data`: (TODO: this should be standardized with a [`user info`](#user-info) dictionary)
    - `username`
    - `last_active_date`
  - `status`: success or failure
  - `errors`: description of the failure (if any)
    
### Errors
  - 403: not a maintainer
  - 404: user does not exist (TODO)

## /v1/admin/users
View the maintainers, organizers, and campaign coordinators

  - Function: [get_users](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py) (admin_endpoints.py)
  - Method: POST

### Parameters
None

### Response

  - `data`:
    - `maintainers`: list of [`user details`](#user-details) dictionaries
    - `organizers`: list of [`user details`](#user-details) dictionaries
    - `campaigns`:
      + `id`
      + `name`
      + `coordinators`: list of [`user details`](#user-details) dictionaries
  - `status`: success or failure
  - `errors`: description of the failure (if any) 

### Errors
  - 403: not an organizer

## /v1/admin/add_campaign
Create a new campaign

  - Function: [create_campaign](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L205) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `name`
  - `open_date` (optional, default is now)
  - `close_date` (TODO: optional, but should it be?)
  - `url`
  - `series_id` (optional, default is 0)
  - `coordinators`: list of usernames (the creating user is also included by default)

### Response
  - `data`: single [`campaign details`](#campaign-details) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a maintainer, organizer, or maintainer

## /v1/admin/campaign/`<campaign_id:int>`
Return info about a campaign

  - Function: [get_campaign](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L574) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `campaign_id` (in path)

### Response
  - `data`: single [`campaign details`](#campaign-details) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)
  
### Errors
  - 403: not a coordinator on this campaign
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/edit
Edit a campaign

  - Function: [edit_campaign](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L345) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)
  - `name` (optional)
  - `open_date` (optional)
  - `close_date` (optional)
  - `url` (TODO)
  - `series_id` (TODO)
  - `coordinators`: (TODO)

### Response
  - `data`: dictionary of the edited parameters
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator on this campaign
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/cancel
Cancel a campaign

  - Function: [cancel_campaign](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L370) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)

### Response
None

### Errors
  - 403: not a coordinator on this campaign
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/add_round
Create a new round within a campaign

  - Function: [create_round](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L407) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)
  - `name` 
  - `description` TODO: add to details/info dict
  - `directions` 
  - `quorum`
  - `vote_method`: the voting type, either:
    - `yesno` 
    - `rating` 
    - `ranking` 
  - `jurors` (list of juror usernames)
  - `deadline_date`
  - `config` (optional, default config provided TODO)

### Response
  - `data`: single [`round details`](#round-details) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/add_coordinator
Add coordinator to a campaign
  
  - Function: [add_coordinator](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L805) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)
  - `username`

### Response
  - `data`: 
    - `username`
    - `campaign_id`
    - `last_active_date`
  - `status`: success or failure
  - `errors`: description of the failure (if any)
  
### Errors
  - 403: not an organizer
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/remove_coordinator
Remove a coordinator from campaign
  
  - Function: [remove_coordinator](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L832) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)
  - `username`

### Response
  - `data`:
    - `username`
    - `campaign_id`
    - `last_active_date`
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not an organizer
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/finalize
Finalize a campaign

  - Function: [finalize_campaign](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L535) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)

### Response
  - `data`: a single [`round results summary`](#round-results-summary) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/publish
Make the report public for a finalized campaign

  - Function: [publish_report](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L153) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)

### Response
None

### Errors
  - 403: not a coordinator for this campaign
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/unpublish
Make a published report private

  - Function: [unpublish_report](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L158) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `campaign_id` (in path)

### Response
None

### Errors
  - 403: not a coordinator for this campaign
  - 404: campaign does not exist

## /v1/admin/campaign/`<campaign_id:int>`/audit
Get the audit log for a campaign

  - Function: [get_campaign_log](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L265) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `campaign_id` (in path)
  - `limit` (optional, default 100)
  - `offset` (optional, default 0)
  - `round_id` (optional)
  - `id` (optional)
  - `action` (optional)

### Response
  - `data`: list of [`audit log entry`](#audit-log-entry) dictionaries
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: campaign does not exist

## /v1/admin/round/`<round_id:int>`/import
Load entries into a round via one of four import methods

  - Function: [import_entries](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L272) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `import_method`:
    - `gistcsv`
    - `category`
    - `round`
    - `selected`
  - `gist_url` (if `import_method=gistcsv`)
  - `category` (if `import_method=category`)
  - `threshold` (if `import_method=round`)
  - `file_names` (if `import_method=selected`)

### Response
  - `data`:
    - `round_id`
    - `new_entry_count`
    - `new_round_entry_count`
    - `total_entries`
    - `disqualified`: list of [`round entry details`](#round-entry-details) for disqualified files
    - `warnings`: possible problems to alert the user
      - `empty import` (no entries)
      - `duplicate import` (no new entries)
      - `all disqualified`
  - `status`: success or failure
  - `errors`: description of the failure (if any)
  
### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/activate
Activate a round

  - Function: [activate_round](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L323) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)

### Response
  - `data`: single [`round count map`](#round-cound-map)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/pause
Pause the round

  - Function: [pause_round](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L339) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)

### Response
  - `data`: "paused"
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`
Return details about a round

  - Function: [get_round](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L611) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`: single [`round details`](#round-details) dictionary (TODO: This is using make_admin_round_details() currently, and should be standardized)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/edit
Edit a round

  - Function: [edit_round](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L425) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `name` (optional)
  - `description` (optional)
  - `directions` (optional)
  - `config` (optional)
  - `new_jurors` (optional)
  - `deadline_date` (optional)
  - `quorum` (optional)

### Response
  - `data`: dictionary of edited parameters
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/cancel
Cancel a round, which is the same as effectively deleting it

  - Function: [cancel_round](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L439) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)

### Response
  - `data`: single [`round details`](#round-details) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/preview_results
See what the results look like

  - Function: [get_round_results_preview](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L446) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`:
    - `round`: single [`round info`](#round-info) dictionary
    - `counts`: [`round count map`](#round-count-map) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/advance
Start a new round from a previous round

  - Function: [advance_round](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L480) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `threshold`
  - `next_round`
    - `jurors`
    - `name`
    - `vote_method` (may be: ranking, rating, yesno)
    - `deadline_date`
    - `quorum` (optional, default is number of jurors)
    - `description` (optional)
    - `directions` (optional)
    - `config` (optional)

### Response
  - `data`: single [`round info`](#round-info) dictionary
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/flags
Returns a list of most flagged entries in a round

  - Function: [get_flagged_entries](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L736) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`: list of [`entry details`](#entry-details) dictionaries, each with a `flaggings` key with [`flag details`](#flag-details)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/all_flags
Get a list of all flaged entries

  - Function: [get_all_flags](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L750) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)
  - `limit` (optional)
  - `offset` (optional)

### Response
  - `data`: list of [`flag details`](#flag-details)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist 

## /v1/admin/round/`<round_id:int>`/disqualified
Returns list of disqualified files

  - Function: [get_disqualified](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L761) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`: list of [`round entry details`](#round-entry-details) for disqualified files
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/autodisqualify
Disqualifies by upload date, resolution, uploader, and filetype (depending on round config settings) or request parameters (TODO: this is not clear!)

  - Function: [autodisqualify](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L674) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `dq_by_upload_date`
  - `dq_by_resolution`
  - `dq_by_uploader`
  - `dq_by_filetype`

### Response
  - `data`: list of [`round entry details`](#round-entry-details) for disqualified files
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist 

## /v1/admin/round/`<round_id:int>`/`<entry_id:int>`/disqualify
Disqualify a specified entry

  - Function: [disqualify_entry](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L108) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `entry_id` (in path)
  - `reason` (optional): an explanation from the user for the disqualification -- this will get stored in the audit logs.

### Response
None

### Errors
  - 403: not a coordinator for this campaign
  - 404: round entry does not exist

## /v1/admin/round/`<round_id:int>`/`<entry_id:int>`/requalify
Undo a disqualification, bringing it back in the round

  - Function: [requalify_entry](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L116) (admin_endpoints.py)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `entry_id` (in path)

### Response
None

### Errors
  - 403: not a coordinator for this campaign
  - 404: round entry does not exist

## /v1/admin/round/`<round_id:int>`/preview_disqualification
Get a preview of which files will be disqualified

  - Function: [preview_disqualification](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L709) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`:
    - `by_upload_date`: list of [`round entry details`](#round-entry-details)
    - `by_resolution`: list of [`round entry details`](#round-entry-details)
    - `by_uploader`: list of [`round entry details`](#round-entry-details)
    - `by_filetype`: list of [`round entry details`](#round-entry-details)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/results
Returns a dictionary of votes per user
  
  - Function: [get_results](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L633) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`: dictionary of entries with votes for each `username`. Votes that are not yet complete are marked "tbv"
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/results/download
Download the results in a csv format

  - Function: [download_results_csv](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L640)  (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
Downloads a csv file, with columns for jurors (plus an average) and rows for entries. If an average is not possible, that cell is marked "na"

(TODO: more descriptive filename)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/entries
Returns a list of entries in a round

  - Function: [get_round_entries](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L83) (admin_endpoints.py)
  - Method: GET


### Parameters
  - `round_id` (in path)

### Response
  - `data`: list of [`round entry export`](#round-entry-export) dictionaries
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/round/`<round_id:int>`/entries/download
Download the entries in csv format. This is compatible with the gistcsv import method, if you want to import a second round.

  - Function: [download_round_entries_csv](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L90) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
Downloads a csv file, with columns similar to the [MediaWiki image table](https://www.mediawiki.org/wiki/Manual:Image_table), in the [`round entry export`](#round-entry-export) format

### Errors
  - 403: not a coordinator for this campaign
  - 404: round does not exist

## /v1/admin/campaign/`<campaign_id:int>`/report
Download a structured report from a finalized campaign.

  - Function: [get_campaign_report_raw](https://github.com/hatnote/montage/blob/master/montage/admin_endpoints.py#L258) (admin_endpoints.py)
  - Method: GET

### Parameters
  - `campaign_id` (in path)

### Response 
  [TODO]

### Errors
  - 403: not a coordinator for this campaign
  - 404: campaign report does not exist

## /v1/juror 
Return details from any jurored rounds

  - Function: [get_index](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L)
  - Method: GET

### Parameters
None

### Response
  - `data`: list of [`juror round details`](#juror-round-details) for all rounds
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a juror on any rounds

## /v1/juror/campaign/`<campaign_id:int>` 
Return details on rounds in a campaign

  - Function: [get_campaign](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L)
  - Method: GET

### Parameters
  - `campaign_id` (in path)

### Response
  - `data`: list of [`juror round details`](#juror-round-details)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a juror in this campaign
  - 404: campaign does not exist

## /v1/juror/round/`<round_id:int>` 
Return details from a round

  - Function: [get_round](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`: single [`juror round details`](#juror-round-details)
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a juror in this round
  - 404: round does not exist

## /v1/juror/round/`<round_id:int>`/tasks 
Return a set of open (active) votes

  - Function: [get_tasks_from_round](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L)
  - Method: GET

### Parameters
  - `round_id` (in path)
  - `count` (optional, default 15)
  - `offset` (optional, default 0)

### Response
  - `data`: 
    - `stats`
    - `tasks`: list of [`vote details`](#vote-details) dictionaries
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a juror in this round
  - 404: no votes exist

## /v1/juror/round/`<round_id:int>`/tasks/submit 
Submit some ratings (or yesno votes) and rankings 

  - Function: [submit_ratings](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L308)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `ratings`: list of `{vote_id: <vote_id>, value: <value>, review: <review string>}`
    - Note: `review` is optional
    - Note: for rating and yesno type rounds, <value> must be between 0 and 1.0, for ranking style rounds, it cannot exceed the number of round entries
### Response
None

### Errors
  - 403: not a juror on this round
  - 404: vote(s) do not exist

## /v1/juror/round/`<round_id:int>`/ratings 
Return submitted ratings or yesno votes from a juror

  - Function: [get_ratings_from_round](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L)
  - Method: GET

### Parameters
  - `round_id` (in path)
  - `order_by` (optional): may be either `date` (default) or `value`
  - `sort` (optional): may be either `asc` (ascending, the default) or `desc` (descending)
  - `count` (optional): default is 15
  - `offset` (optional)

### Response
  - `data`: list of vote [`vote details`](#vote-details) dictionaries
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a juror for this round
  - 404: ratings do not exist

## /v1/juror/round/`<round_id:int>`/rankings 
Return submitted rankings

  - Function: [get_rankings_from_round](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L)
  - Method: GET

### Parameters
  - `round_id` (in path)

### Response
  - `data`: list of vote [`vote details`](#vote-details) dictionaries
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a juror for this round
  - 404: rankings do not exist

## /v1/juror/round/`<round_id:int>`/`<entry_id:int>`/fave 
Submit a fave

  - Function: [submit_fave](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L412)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `entry_id` (in path)

### Response
None

### Errors
  - 403: not a juror for this round
  - 404: round entry do not exist

## /v1/juror/round/`<round_id:int>`/`<entry_id:int>`/unfave 
Remove a fave

  - Function: [remove_fave](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L417)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `entry_id` (in path)

### Response
None

### Errors
  - 403: not a juror for this round
  - 404: round entry do not exist

## /v1/juror/round/`<round_id:int>`/`<entry_id:int>`/flag 
Submit a flag to tell a coordinator that you do not think this entry belongs in this round (ie, it's not eligible or appropriate for some reason)

  - Function: [submit_flag](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L422)
  - Method: POST

### Parameters
  - `round_id` (in path)
  - `entry_id` (in path)
  - `reason` (optional)

### Response
None

### Errors
  - 403: not a juror for this round
  - 404: round entry do not exist

## /v1/juror/faves
Returns a list of fave'd entries

  - Function: [get_faves](https://github.com/hatnote/montage/blob/master/montage/juror_endpoints.py#L)
  - Method: GET

### Parameters
  - `limit` (optional, default 10)
  - `offset` (optional, default 0)

### Response
  - `data`: list of [`entry details`](#entry-details) dictionaries, along with a `fav_date` for each
  - `status`: success or failure
  - `errors`: description of the failure (if any)

### Errors
  - 403: not a juror for this round
  - 404: no faves exist


# Response schemas
In Montage, objects may have an abbreviated form (info) and a complete form (details). There are a few minor exceptions (e.g., an entry may optionally include the uploader) noted at the endpoint.

## series info
Abbreviated information about a series of campaigns:

  - `id`
  - `name`
  - `url`
  - `description`
  - `status`

## campaign info
Abbreviated information about a campaign:

  - `id`: campaign id
  - `name`: user friendly campaign name
  - `url_name`: slugified campaign name
  - `open_date`: start date for eligible uploads for a campaign
  - `close_date`: end date for eligible uploads for a campaign

## campaign details
Complete information about a campaign:

  - `id`: campaign id
  - `name`: user friendly campaign name
  - `url_name`: slugified campaign name
  - `open_date`: start date for eligible uploads for a campaign
  - `close_date`: end date for eligible uploads for a campaign
  - `rounds`: list of [`round info`](#round-info) dictionaries
  - `coordinators`: list of [`user info`](#user-info) dictionaries
  - `active round`: the [`round info`](#round-info) dictionary for the active round
  
## round info
Abbreviated information about a round for a coordinator:

  - `id`: round id
  - `name`: user friendly round name
  - `directions`: jury facing instructions
  - `canonical_url_name`: sluggified round name
  - `vote_method`: the voting type, either:
    - `yesno` 
    - `rating` 
    - `ranking` 
  - `open_date`: the start date for voting in the round
  - `deadline_date`: the end date for voting in the round
  - `close_date`: the date the round was finalized
  - `jurors`: list of [`juror info`](#juror-info) dictionaries
  - `status`: the current state of the round, either:
    - `active` (currently accepting votes)
    - `paused` (a round is temporarily not accepting votes)
    - `cancelled` (basically, it's deleted)
    - `finalized` (all done)
  - `config`: a dictionary of various settings for the round
  - `is_closable`: this is true if the round has all the votes necessary to advance to the next round. For ranking rounds, you cannot preview results until all the ballots are submitted.

## round details
Complete information about a round for a coordinator (similar to [`juror round details`](#juror-round-details): 

  - `id`: round id
  - `name`: user friendly round name
  - `directions`: jury facing instructions
  - `canonical_url_name`: sluggified round name
  - `vote_method`: the voting type, either:
    - `yesno` 
    - `rating` 
    - `ranking` 
  - `open_date`: the start date for voting in the round
  - `deadline_date`: the end date for voting in the round
  - `close_date`: the date the round was finalized
  - `jurors`: list of [`juror info`](#juror-info) dictionaries
  - `status`: the current state of the round, either:
    - `active` (currently accepting votes)
    - `paused` (a round is temporarily not accepting votes)
    - `cancelled` (basically, it's deleted)
    - `finalized` (all done)
  - `config`: a dictionary of various settings for the round
  - `quorum`: the number of jurors that should see each entry
  - `total_round_entries`: number of entries in the round
  - `stats`:
    - `total_round_entries`: number of entries in the round
    - `total_tasks`: number of non-cancelled votes
    - `total_open_tasks`: number of active votes
    - `percent_tasks_open`: percentage of active votes to non-cancelled votes
    - `total_cancelled_tasks`: number of cancelled votes
    - `total_disqualified_entries`: number of disqualified entries (for any reason)
    - `total_uploaders`: number of unique uploaders for non-disqualified entries
  - `juror_details`: list of [`juror details`](#juror-details) dictionaries
  - `is_closable`: this is true if the round has all the votes necessary to advance to the next round. For ranking rounds, you cannot preview results until all the ballots are submitted.

## round count map
A short set of round stats:

  - `total_round_entries`: number of entries in the round
  - `total_tasks`: number of non-cancelled votes
  - `total_open_tasks`: number of active votes
  - `percent_tasks_open`: percentage of active votes to non-cancelled votes
  - `total_cancelled_tasks`: number of cancelled votes
  - `total_disqualified_entries`: number of disqualified entries (for any reason)
  - `total_uploaders`: number of unique uploaders for non-disqualified entries

## juror round details
Complete information about a round for a juror (similar to [`round details`](#round-details) for coordinators):

  - `id`: round id
  - `directions`: round directions
  - `name`: user friendly round name
  - `canonical_url_name`: slugified round name
  - `vote_method`: the voting type, either:
    - `yesno` 
    - `rating` 
    - `ranking` 
  - `open_date`: the start date for voting in the round
  - `deadline_date`: the end date for voting in the round
  - `close_date`: the date the round was finalized
  - `status`: the current state of the round, either:
    - `active` (currently accepting votes)
    - `paused` (a round is temporarily not accepting votes)
    - `cancelled` (basically, it's deleted)
    - `finalized` (all done)
  - `config`: a dictionary of various settings for the round
  - `total_tasks`: number of non-cancelled votes for this juror
  - `total_open_tasks`: number of active votes for this juror
  - `percent_tasks_open`: percentage of active votes to non-cancelled votes
  - `campaign`: single [`campaign info`](#campaign-info) dictionary
  - `ballot`: a dictionary of rating/count pairs

## user info
Abbreviated information about a user:

  - `id`: user id (same as Wikimedia CentralAuth)
  - `username`: user name (same as Wikimedia CentralAuth)
  - `is_organizer`: true or false
  - `is_maintainer`: true or false
  `
## user details
Complete information about a user:

  - `id`: user id (same as Wikimedia CentralAuth)
  - `username`: user name (same as Wikimedia CentralAuth)
  - `is_organizer`: true or false
  - `is_maintainer`: true or false
  - `last_active_date`
  - `created_by`

## juror info
Abbreviated information about a juror in a round:

  - `id`: user id
  - `username`: user name
  - `is_active`: true or false

## juror details
Complete information about a juror in a round:

  - `id`: user id
  - `username`: user name
  - `is_active`: true or false
  - `stats`:
    - `total_tasks`: number of non-cancelled votes
    - `total_open_tasks`: number of active votes
    - `percent_tasks_open`: percent of active votes to non-cancelled votes
    - `total_cancelled_tasks`: number of canceled votes (probably due to entry disqualification)

## entry info
Abbreviated info about an entry

  - `id`: entry id

## entry details
Complete information about an entry (TODO: add descriptions)

  - `id`: entry id
  - `upload_date`: 
  - `mime_major`: 
  - `mime_minor`: 
  - `name`: 
  - `height`: 
  - `width`: 
  - `url`: 
  - `url_sm`: 
  - `url_med`: 
  - `resolution`: 

## entry ranking details
Complete information about the entry ranking information at the end of a round:

  - `ranking`: the rank of a entry
  - `entry`: [`entry details`](#entry-details) dictionary
  - `ranking_map`: (what is this? TODO)
  - `juror_review_map`: dictionary of reviews per juror
  - `juror_ranking_map`: dictionary of ranks per juror

## entry export
Information about entries in import/export format, based on the MediaWiki schema (TODO: add descriptions)

  - `img_name`:
  - `img_major_mime`:
  - `img_minor_mime`:
  - `img_width`:
  - `img_height`:
  - `img_user`:
  - `img_user_text`:
  - `img_timestamp`:

## round entry details
Complete information about an entry in a round:

  - `entry`:  [`entry details`](#entry-details) dictionary for this entry
  - `dq_reason`: reason for disqualification from this round
  - `dq_user_id`: the user id who disqualified the entry from this round

## round entry export
Information about entries in import/export format, plus some round information:

  - `img_name`
  - `img_major_mime`
  - `img_minor_mime`
  - `img_width`
  - `img_height`
  - `img_user`
  - `img_user_text`
  - `img_timestamp`
  - `source_method`: why the entry is in this round
  - `source_params`: details that correspond to the for the `source_method`

## flag details
Complete information about a flag: 

  - `round`: round id
  - `entry_id`: entry id
  - `entry_name`: entry name
  - `user`: username of who submitted the flag
  - `reason`: reason provided by the user who submitted the flag
  - `date`: date the flag was submitted

## vote info
Abbreviated information about a vote:

  - `id`: vote id
  - `name`: name of the entry
  - `user`: username of the juror assigned to this task
  - `value`: value of the vote
  - `round_id`: round id
  - `review`: a description of the reason for the vote, provided by the user

## vote details
Complete information about a vote:

  - `id`: vote id
  - `name`: name of the entry
  - `user`: username of the juror assigned to this task
  - `value`: value of the vote
  - `round_id`: round id
  - `review`: a description of the reason for the vote, provided by the user
  - `entry`: `entry details` dictionary
  - `date`: date the vote was modified (in ISO 8601 format)

## round results summary
Information about the end of a campaign:

  - `campaign_id`: campaign id
  - `campaign_name`: user friendly campaign name
  - `date`: date the summary was created
  - `version`: format version

## audit log entry
A row from the audit log:

  - `id`: audit log entry id
  - `user_id`: responsible user's id
  - `campaign_id`: campaign id associated with the action
  - `round_id`: round id associated with the action
  - `round_entry_id`: round entry id associated with the action
  - `role`: responsible user's role (organizer, coordinator, etc)
  - `action`: name of action
  - `message`: description of action
  - `create_date`: date of action
