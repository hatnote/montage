# Design notes

This tool lets administrators create a campaign. Each campaign is
composed of a series of rounds (usually 3). Judges are invited to each
round to rate photos along a common voting method. At the end of the
round, the top-rated photos enter the next round of the
competition. The final round produces a ranked list of winning photos.

## Views

The two main areas of the tool are for admins
(creating/editing/closing rounds), judges (participating in rounds).

### Campaign admin

Admins can see a list of the campaigns they are associated with. Each
campaign links to its round admin page.

### Round admin

Admins can see a list of the rounds associated with a campaign they
are associated with, and rounds are divided among active and
inactive. Each round shows the type of ranking, the number of photos,
number of jury members. Active rounds show the percentage
complete. Inactive rounds show the total number of selected photos.

Admins can create a round, or edit an existing round.

### Round details

Admins can see the details for a selected round when creating or
editing:

 - Name
 - Status (active, inactive, or closed)
 - Type (up/down votes, rating, ranking)
 - (The quorum for each image, for up/down and rating votes)
 - Images (imported from a Commons category, a previous round, or a
   CSV of filenames)
 - Jury members (list of Wikimedia usernames)
   - Note: Due to the way votes are assigned, the jury membership is
     only editable when a round is set as inactive.

### Round closing

Admins can close out a round to select images. The round closing
interface allows admins to choose how the round will close, by either
specifying the number of images to select or the cutoff for
selection. The page will show the number of images and number of
authors will go to the next round. Once a round is marked as complete,
there will be an option to download a list, create a follow up round,
or see more details on the result.

### Round vote details

Admins can see a list of all of each vote in a round in a campaign
they are associated with. The votes are also downloadable as a CSV.

### Import dialog

When creating a round, admins can choose how to import files. They can
provide a list of commons categories, including an optional filter
based on the resolution of an image. Before finalizing the import, it
will show the number of images that will be imported.

### Campaign overview

Jurors can see a list of the campaigns with rounds they are
associated with. Each campaign links to the round overview page.

### Round overview

Jurors can see a list of rounds they are associated with. Each active
round links to the voting dashboard for that round. The round displays
their progress, and the round's due date.

### Voting

Jurors can see the next task in a round they are associated with. For
up/down and rating type rounds, the interface includes a
high-resolution version of the image, along with limited metadata (the
image's resolution), and the juror can select up/down or a star
rating. The juror also has the option of skipping a task, and getting
another task from their queue.

For ranking type rounds, the interface shows a rankable list of images
with limited metadata (the image's resolution). The juror can arrange
the photos in an order and then submit the round.

The juror can also see their overall progress and the due date.

Jurors have an option to enable a low-bandwidth version, which
displays reduced resolution versions of images.

### Health

The tool shows some simple stats that let you verify it's all in
working order.

##Other notes

 - [Commons:Jury tools/WLM jury tool
requirements](https://commons.wikimedia.org/wiki/Commons:Jury_tools/WLM_jury_tool_requirements)

## Montage User Roles

Montage has a simple permission scheme tailored to the tasks of
contest organization and judging.

* Maintainers - Creators/operators/maintainers of Montage
    * Add Organizers
* Organizers
    * Create campaigns
    * Add coordinators to campaigns they created
    * All actions available to coordinators.
* Coordinators
    * Create/cancel/close a round
    * Add/remove jurors
    * Mark jurors active/inactive
    * Initiate a task reassignment
    * Download results and audit logs
* Jurors
    * Rate and rank photos to which they are assigned
    * See their own progress

Maintainers can technically do anything, as they have database access
to the system, however they are intended to only add organizers.

# Vote allocation

## Static versus dynamic

As of writing, Montage is designed for vote pre-allocation. That is,
on round initiation, voting tasks are preassigned to jury members.

One design that's been debated is dynamic task assignment. The early
design of Montage didn't support this for the following reasons:

* Implementation complexity and potential performance issues
* Potentially unfair results due to one or more jury members having
  more time/initiative, leading to them voting more than other jurors

Preallocation is simpler, ensures an even distribution of votes, sets
a clear expectation of work for juror and coordinator, ultimately
leaving the coordinator in charge.

A future version of Montage might want to support dynamic dispensing
of votes. The current schema could support it, but the user_id would
be left blank. Then, for each batch of votes, it's a matter of finding
RoundEntries that have not been voted on by the current user. It may
be possible to do this efficiently.

The important feature, which I am about to implement, is allocation
weighting. That is, coordinators should be able to set a minimum and
maximum amount of work expected from each juror. (The version I am
about to implement is still pre-allocated, so the minimum and maximum
are the same value.)
