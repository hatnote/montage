# Form Validation Testing Guide

This guide provides step-by-step instructions for testing the newly implemented form validation features in Montage.

## Setup

1. Start the Montage frontend development server:
   ```bash
   cd frontend
   npm install  # if needed
   npm run dev
   ```

2. Navigate to the application in your browser (usually http://localhost:5173)

3. Log in with your Wikimedia account

## Test Cases

### Section 1: Campaign Creation (NewCampaignView)

#### Test 1.1: Campaign Name Validation
**Steps:**
1. Navigate to "Create new campaign" page
2. Leave "Campaign name" field empty
3. Try to click "Create campaign" button

**Expected Result:**
- Error message appears: "Campaign name is required"
- Field shows error state (red border/styling)
- Form does not submit

#### Test 1.2: Campaign URL Validation
**Steps:**
1. Fill in campaign name: "Test Campaign"
2. Leave campaign URL empty
3. Click "Create campaign"

**Expected Result:**
- Error message appears: "Campaign URL is required"
- Field shows error state
- Form does not submit

#### Test 1.3: Invalid Campaign URL
**Steps:**
1. Fill in campaign name: "Test Campaign"
2. Enter invalid URL: "not a url"
3. Click "Create campaign"

**Expected Result:**
- Error message appears: "Invalid URL"
- Field shows error state
- Form does not submit

#### Test 1.4: Date/Time Format Validation
**Steps:**
1. Fill in campaign name: "Test Campaign"
2. Fill in valid URL: "https://example.com"
3. Leave "Open date" field empty
4. Click "Create campaign"

**Expected Result:**
- Error message appears: "Open date is required"
- Field shows error state
- Form does not submit

#### Test 1.5: Time Format Validation
**Steps:**
1. Fill in campaign name: "Test Campaign"
2. Fill in valid URL: "https://example.com"
3. Select valid open date (e.g., 2026-03-17)
4. Manually enter invalid open time (e.g., "25:00")
5. Click "Create campaign"

**Expected Result:**
- Error message appears: "Open time is required"
- Form does not submit

#### Test 1.6: Date Range Validation (Close > Open) ⭐ CRITICAL
**Steps:**
1. Fill all required fields with valid data:
   - Name: "Test Campaign"
   - URL: "https://example.com"
   - Open date: 2026-03-20
   - Open time: 10:00
2. Set close date: 2026-03-15 (BEFORE open date)
3. Set close time: 14:00
4. Add at least one coordinator
5. Click "Create campaign"

**Expected Result:**
- Error message appears: "Close date and time must be after open date and time"
- Error appears on "Close date" field
- Form does not submit
- Error clears when you change close date to be after open date

#### Test 1.7: Coordinator Selection Validation
**Steps:**
1. Fill all required fields with valid data
2. Leave "Campaign Coordinators" empty (no users selected)
3. Click "Create campaign"

**Expected Result:**
- Error message appears: "At least one coordinator is required"
- Field shows error state
- Form does not submit

#### Test 1.8: Successful Campaign Creation
**Steps:**
1. Fill all fields with valid data:
   - Name: "Validation Test Campaign"
   - URL: "https://example.com/test"
   - Open date: 2026-03-20
   - Open time: 10:00
   - Close date: 2026-03-25
   - Close time: 18:00
   - Coordinator: Select your username
2. Click "Create campaign"

**Expected Result:**
- Success toast appears: "Campaign added successfully"
- Redirected to campaign details page
- New campaign appears in campaign list

---

### Section 2: Campaign Editing (CampaignView)

#### Test 2.1: Edit Campaign with Invalid Dates
**Steps:**
1. Navigate to an existing campaign
2. Click "Edit campaign" button
3. Change close date to be BEFORE open date
4. Click "Save"

**Expected Result:**
- Error message appears: "Close date and time must be after open date and time"
- Changes are not saved
- Campaign details remain unchanged

#### Test 2.2: Edit Campaign with Valid Data
**Steps:**
1. Navigate to an existing campaign
2. Click "Edit campaign" button
3. Change campaign name: "Updated Campaign Name"
4. Verify dates are in valid order
5. Click "Save"

**Expected Result:**
- Success toast appears
- Campaign name updates
- Edit mode closes
- New name shows on campaign page

---

### Section 3: Round Creation (RoundNew) - First Round ⭐ MOST IMPORTANT

#### Test 3.1: Round Name Validation
**Steps:**
1. Navigate to a campaign (with 0 rounds)
2. Click "Add Round" button
3. Leave "Round name" field empty
4. Click "Add Round" button at bottom

**Expected Result:**
- Error message appears: "Round name is required"
- Field shows error state
- Form does not submit

#### Test 3.2: Deadline Validation
**Steps:**
1. Fill in round name: "Test Round"
2. Leave "Voting deadline" empty
3. Click "Add Round"

**Expected Result:**
- Error message appears: "Voting deadline is required"
- Field shows error state
- Form does not submit

#### Test 3.3: Quorum Validation (Positive Number)
**Steps:**
1. Fill in round name: "Test Round"
2. Select deadline: 2026-03-25
3. Select vote method: "Yes/No"
4. Change quorum to 0 (or negative)
5. Click "Add Round"

**Expected Result:**
- Error message appears: "Quorum must be a positive number"
- Field shows error state
- Form does not submit

#### Test 3.4: Juror Selection Validation
**Steps:**
1. Fill valid: name, deadline, vote method, quorum (1)
2. Leave "Jurors" empty (no jurors selected)
3. Click "Add Round"

**Expected Result:**
- Error message appears: "At least one juror is required for this round"
- Field shows error state
- Form does not submit

#### Test 3.5: Import Source - Category Validation
**Steps:**
1. Set "Source" radio button to "Category on Wikimedia Commons"
2. Leave category field empty
3. Fill all other required fields validly
4. Click "Add Round"

**Expected Result:**
- Error appears (may be generic or specific to import source)
- Form does not submit

#### Test 3.6: Import Source - CSV URL Validation
**Steps:**
1. Set "Source" to "File List URL" (CSV)
2. Leave CSV URL empty
3. Fill all other required fields validly
4. Click "Add Round"

**Expected Result:**
- Error appears for missing CSV URL
- Form does not submit

#### Test 3.7: Import Source - File List Validation
**Steps:**
1. Set "Source" to "File List"
2. Leave file list empty
3. Fill all other required fields validly
4. Click "Add Round"

**Expected Result:**
- Error appears for missing file list
- Form does not submit

#### Test 3.8: Successful First Round Creation
**Steps:**
1. Fill all fields:
   - Round name: "Round 1"
   - Deadline: 2026-03-25
   - Vote method: "Yes/No"
   - Source: "Category"
   - Category: Select a category
   - Quorum: 2
   - Jurors: Select at least 2 users
   - Show stats: Yes or No
   - Directions: (optional)
2. Click "Add Round"

**Expected Result:**
- Success toast: "Round added successfully"
- Round appears in campaign rounds list
- Round card shows name, vote method icon, and details

---

### Section 4: Round Creation - Subsequent Rounds

#### Test 4.1: Second Round without Threshold Selection ⭐ CRITICAL
**Steps:**
1. Navigate to campaign with 1 completed round
2. Click "Add Round" button
3. Fill all fields validly:
   - Round name: "Round 2"
   - Deadline: 2026-03-30
   - Vote method: "Rating"
   - Quorum: 2
   - Jurors: Select users
4. Leave "Threshold" dropdown as default (no selection)
5. Click "Add Round"

**Expected Result:**
- Error message appears: "Threshold must be selected"
- Field shows error state
- Form does not submit

#### Test 4.2: Successful Second Round Creation
**Steps:**
1. Same as Test 4.1 but:
2. Select a threshold from the dropdown (e.g., "0.75")
3. Click "Add Round"

**Expected Result:**
- Success toast: "Round added successfully"
- New round appears in campaign
- Can proceed to add more rounds or finalize campaign

---

### Section 5: Real-time Error Clearing

#### Test 5.1: Error Clears When Fixed
**Steps:**
1. Start creating a campaign
2. Leave campaign name empty and try to submit → error appears
3. Fill in campaign name field
4. Try to submit again

**Expected Result:**
- Previous error message clears
- New validation runs (may show different error or succeed)
- Error state is cleared from field

#### Test 5.2: Multiple Errors Clear
**Steps:**
1. Start creating a campaign
2. Leave name AND coordinator empty, try to submit
3. See both errors appear
4. Fill in name field
5. Try to submit

**Expected Result:**
- Name error clears
- Coordinator error still shows
- Only applicable errors remain

---

## Advanced Test Cases

### Test A.1: Keyboard Navigation
**Steps:**
1. Open campaign creation form
2. Press Tab to move through form fields
3. Trigger validation errors on required fields
4. Verify error messages are announced for accessibility

**Expected Result:**
- Tab order is logical
- Errors are accessible to screen readers
- All fields are reachable via keyboard

### Test A.2: Cross-browser Testing
**Steps:**
- Test on:
  - Chrome/Chromium
  - Firefox
  - Safari (if available)
  - Edge

**Expected Result:**
- Validation works consistently across browsers
- Error styling is consistent
- No JavaScript errors in console

### Test A.3: Mobile/Responsive Testing
**Steps:**
1. Open development tools → device toolbar
2. Test forms on mobile sizes (iPhone, iPad, Android)
3. Try to submit with invalid data
4. Verify error messages are readable

**Expected Result:**
- Forms are usable on mobile
- Error messages are clearly visible
- No text overflow or layout issues

---

## Automated Testing (Optional)

If Cypress E2E tests are available:

```bash
cd frontend
npm run test:e2e
```

Test files should include validation scenarios for:
- Campaign creation with invalid inputs
- Round creation with missing required fields
- Date range validation
- Threshold selection for subsequent rounds

---

## Bug Report Template

If you find an issue during testing:

**Title:** [Component] Validation not working for [field name]

**Description:**
- What step triggers the bug?
- What was expected to happen?
- What actually happened?
- Screenshots/video?

**Environment:**
- Browser & version
- OS
- Screenshot of browser console errors (if any)

**Repro Steps:**
1. Go to [page]
2. Fill in...
3. Click...
4. Observe...

---

## Success Criteria Checklist

- [ ] All required field validations work
- [ ] Cross-field validations work (date ranges)
- [ ] Import source validations work
- [ ] Error messages are clear and helpful
- [ ] Errors clear when fields are fixed
- [ ] Form does not submit with invalid data
- [ ] Form submits successfully with valid data
- [ ] No console JavaScript errors
- [ ] Works on mobile browsers
- [ ] Accessible with keyboard navigation
