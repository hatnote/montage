# Montage: A Comprehensive Guide for Campaign Organizers

Welcome to Montage! This guide addresses common questions and best practices for campaign coordinators and organizers.

## Table of Contents
1. [Advanced Importing](#advanced-importing)
2. [Multi-Media Support](#multi-media-support)
3. [EXIF and Metadata](#exif-and-metadata)
4. [Juror Communication](#juror-communication)
5. [Troubleshooting Login](#troubleshooting-login)

---

## Advanced Importing

### Category Redirects
Montage now automatically follows category redirects on Wikimedia Commons. If your campaign category has been moved or renamed, you can use either the old or the new category name during import; Montage will resolve it to the correct target.

### Pre-Disqualification
You can pre-disqualify images during a CSV or Spreadsheet import by adding a `dq_reason` column. Montage will skip these images and record your reason for the jurors.

### Following File Redirects
Individual file redirects are also handled. If a file in your list was renamed on Commons, Montage will automatically resolve the link to the latest version of the file.

---

## Multi-Media Support

Montage is no longer just for images!
- **Audio:** Jurors can play `.ogg`, `.mp3`, and other supported audio formats directly in the voting interface.
- **Video:** Jurors can play `.webm`, `.ogv`, and other video formats.
- **Controls:** Playback controls (Play, Pause, Volume) are integrated into the juror UI.

---

## EXIF and Metadata

### Camera Model Tracking
For campaigns like Wiki Loves Sudan that need to distinguish between mobile and DSLR entries, Montage now displays the **Camera Model** in the juror sidebar. This information is extracted directly from the file's EXIF data during import.

---

## Juror Communication

### Notes to Coordinator
Jurors can now leave optional notes for you directly while voting. If a juror spots a copyright issue, a low-quality file, or has a question, they can record it in the "Notes to Coordinator" field in their sidebar.

---

## Troubleshooting Login

If your jurors are having trouble logging in:
1. **Clear Cookies:** Ask them to clear their browser cache and cookies for `montage.toolforge.org`.
2. **Meta-Wiki:** Ensure the juror is logged into their Wikimedia account on Meta-Wiki.
3. **Third-Party Cookies:** Check if the browser is blocking third-party cookies, which can interfere with the OAuth flow.

---

*This guide was generated as part of the GSoC 2026 Architectural Hardening initiative.*
