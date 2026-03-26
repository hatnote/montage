# Frontend Form Validation Implementation

## Summary
Implemented comprehensive input validation for campaign and round creation forms to prevent invalid data submission and improve user experience with clear error messages.

## Files Modified

### 1. **frontend/src/i18n/en.json**
Added validation error messages:
- `montage-error-close-after-open`: "Close date and time must be after open date and time"
- `montage-error-deadline-required`: "Voting deadline is required"
- `montage-error-round-name-required`: "Round name is required"
- `montage-error-quorum-positive`: "Quorum must be a positive number"
- `montage-error-jurors-required`: "At least one juror is required for this round"
- `montage-error-threshold-required`: "Threshold must be selected"
- `montage-error-import-source-required`: "Please select an import source"
- `montage-error-category-required`: "Category is required"
- `montage-error-csv-url-required`: "CSV URL is required"
- `montage-error-file-list-required`: "File list is required"

### 2. **frontend/src/components/Campaign/NewCampaign.vue**
**Changes:**
- Added cross-field validation using Zod `.refine()` to ensure close date/time is after open date/time
- Validation happens before form submission
- Error messages display inline in form fields

**Validation Rules:**
- Campaign name is required (non-empty)
- Campaign URL is required and must be a valid URL
- Open date must be valid
- Open time must be valid (HH:mm format)
- Close date must be valid
- Close time must be valid (HH:mm format)
- At least one coordinator is required
- **Close date/time must be after open date/time** ✅

### 3. **frontend/src/components/Campaign/ViewCampaign.vue**
**Changes:**
- Added the same cross-field date validation as NewCampaign.vue
- Applied to campaign edit mode
- Same error handling and inline display

**Validation Rules:**
- Same as NewCampaign.vue for edit mode

### 4. **frontend/src/components/Round/RoundNew.vue**
**Changes:**
- Removed unused Zod import (simplified validation approach)
- Added `errors` ref to track validation errors per field
- Enhanced form fields with `:status` and `:messages` bindings for error display
- Implemented `validateRound()` function with comprehensive validation
- Updated form fields to show error states visually

**Validation Rules:**

**For All Rounds:**
- Round name is required (non-empty)
- Voting deadline is required
- Vote method must be selected
- Quorum must be a positive number
- At least one juror is required

**For First Round (roundIndex === 0):**
- Plus all rules above
- Import source must be selected
- Based on import source:
  - If category: category must be selected and non-empty
  - If CSV: CSV URL must be provided and non-empty
  - If file list: file list must be provided and non-empty

**For Subsequent Rounds (roundIndex > 0):**
- Plus all rules above (except import source)
- Threshold must be selected for progression to next round

**Form Fields Updated with Error Display:**
- ✅ Round name
- ✅ Voting deadline
- ✅ Vote method
- ✅ Quorum
- ✅ Jurors list
- ✅ Threshold (for subsequent rounds)

## Features Implemented

### 1. **Real-time Error Feedback**
- Error messages appear inline below form fields
- Error states indicated by red/error status styling (via Codex component styling)
- Clear, user-friendly error messages in English (translatable)

### 2. **Cross-Field Validation**
- Campaign: Ensures close date/time > open date/time
- Round: Validates import source data exists before submission

### 3. **Type-Safe Validation**
- NewCampaign & ViewCampaign: Uses Zod schema validation
- RoundNew: Direct validation with clear error handling
- Prevents backend errors by validating early on client-side

### 4. **Required Field Enforcement**
- All critical fields marked as required
- Validation prevents empty/null values
- Quorum converted to number before validation

## Benefits

1. **Prevents 400/500 Errors**: Early validation catches issues before sending to backend
2. **Better UX**: Users see validation errors immediately with clear messages
3. **Reduced Backend Load**: Invalid requests never reach the server
4. **Improved Data Quality**: Ensures data consistency at form submission
5. **Accessibility**: Error messages displayed with proper Codex field status styling

## Testing Recommendations

### Manual Testing:
1. **Campaign Creation:**
   - Try creating campaign with empty name → should show error
   - Try creating campaign with invalid URL → should show error
   - Try creating campaign with close date before open date → should show error
   - Try creating campaign with no coordinators → should show error

2. **Round Creation:**
   - Try creating round with empty name → should show error
   - Try creating round with no deadline → should show error
   - Try creating round with quorum = 0 or negative → should show error
   - Try creating round with no jurors → should show error
   - Try creating round with no import source → should show error (first round only)
   - Try creating round with threshold not selected → should show error (subsequent rounds only)

3. **Campaign Edit:**
   - Try editing campaign with invalid dates → should show error
   - Same validation as campaign creation

### Automated Testing:
- Add unit tests for validation functions
- Add E2E tests for form submission flows
- Test validation error messages in different locales

## Future Improvements

1. Add field-level debounced validation (validate as user types)
2. Add success feedback when all fields are valid
3. Add loading states during form submission
4. Extend validation to CSV/Google Sheet imports
5. Add validation for minimum resolution settings
6. Consider adding field-level help text with examples
7. Add support for multiple error messages per field
8. Add real-time availability check for username entries (jurors/coordinators)
