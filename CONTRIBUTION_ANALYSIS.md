# Montage Project Contribution Analysis

## Overview

**Montage** is a Vue.js + Python/Clastic photo evaluation tool for Wiki Loves competitions. It manages campaign coordination and juror voting workflows with different round types (rating, ranking, yes/no).

### Current Work Status

**Recent Contributions:**
- **PR #404**: Frontend validation display + backend ranking round fix (100-submit cap)
- **PR #410**: Round creation preemptive checks validation (addressing issue #103)

---

## Key Stability Issues & Areas for Contribution

### 1. **Input Validation Gaps**

**Frontend Issues:**
- [[frontend/src/components/](frontend/src/components/)] Components lack consistent validation feedback
- Round creation form doesn't validate conflicting parameters before submission
- Campaign date inputs need cross-field validation (end_date > start_date)
- Voter input fields lack real-time validation for rating/ranking rounds
- File upload inputs (CSV imports) have minimal validation before sending to backend

**Backend Issues:**
- [[montage/admin_endpoints.py](montage/admin_endpoints.py)] Most POST endpoints lack input parameter validation
- `create_round()` function doesn't validate threshold_map structure before persisting
- No validation of vote values against VALID_RATINGS/VALID_YESNO before storage
- Missing null/empty checks in DAO methods (e.g., `add_juror()`)

**Impact**: Prevents 400/500 errors and null value bugs. Improves UX with early feedback.

---

### 2. **Error Handling Deficiencies**

**Frontend:**
- [[frontend/src/services/api.js](frontend/src/services/api.js)] Generic error toast instead of detailed backend messages
- Vote submission errors during fast voting don't show which entries failed (issue #206)
- Network failures during CSV import/round creation lack user feedback
- Missing retry logic for transient failures

**Backend:**
- [[montage/mw/__init__.py](montage/mw/__init__.py#L50-L90)] TODO comment: need to autoswitch HTTP status codes based on response_dict['status']
- Generic 500 errors for missing resources (issue #400 context) instead of proper 404/403
- `check_entry_existence()` calls [[montage/rdb.py](montage/rdb.py)] but no centralized error handling
- Vote submission with >100 entries returns unclear error

**Impact**: Better user experience, easier debugging, proper HTTP semantics.

---

### 3. **Test Coverage Gaps**

**Missing Test Paths:**
- No tests for round creation edge cases (conflicting threshold values, invalid vote methods)
- Vote submission with fast clicking (race condition in issue #206)
- CSV import with invalid/partial data ([[montage/loaders.py](montage/loaders.py#L77-L200)]) - only has warnings, no tests
- API contract violations (e.g., ranking round >100 entries)
- Concurrent vote updates from multiple jurors
- Permission checks (coordinator access to campaigns/rounds)

**Existing Tests:**
- [[montage/tests/test_web_basic.py](montage/tests/test_web_basic.py)] - Basic routing only
- [[montage/tests/test_loaders.py](montage/tests/test_loaders.py)] - Loader validation only
- [[frontend/cypress/e2e/](frontend/cypress/e2e/)] - Campaign/login E2E tests exist but incomplete

**Impact**: Catches regressions, documents expected behavior, prevents ticket repeats.

---

### 4. **API Contract Definition Issues**

**Unclear Contracts:**
- `POST /admin/add_series` response data marked TODO - should match `series_info` schema
- `POST /admin/add_organizer` response TODO - inconsistent with other user endpoints
- Vote statistics endpoint (`/juror/round/<id>/votes-stats`) lacks documented response shape
- [[montage/docs/api.md](montage/docs/api.md#L20-L50)] Multiple TODOs for standardizing response shapes
- No OpenAPI/JSON schema for validation

**Database Schema Issues:**
- [[montage/check_rdb.py](montage/check_rdb.py#L18-L60)] Relationships not verified at startup
- Missing foreign key constraints in some tables
- No documented cascade delete behavior

**Impact**: Prevents frontend/backend mismatches, enables API testing, improves developer experience.

---

## Specific Issues from GSoC Requirements

| Issue | Status | Area | Priority |
|-------|--------|------|----------|
| #400 | PR #404 in review | Round 100-vote validation | High |
| #103 | PR #410 in review | Round creation validation | High |
| #206 | Open | Fast voting race condition | Medium |
| #325 | Open | Vote statistics display | Medium |
| #322 | Open | Edit vote loading | Medium |
| #155 | Open | Author/upload date from file v1 | Low |

---

## Recommended Contribution Path

### Phase 1: Foundation (Low-hanging fruit)
1. **Add input validation** to frontend form components (round creation, campaign dates)
2. **Improve error messages** - Replace generic toasts with backend error details
3. **Write integration tests** for CSV import edge cases

### Phase 2: Core Stability
4. **Add backend validation** for POST endpoint parameters
5. **Fix fast-voting race condition** (issue #206) with proper locking/atomicity
6. **Define API contracts** - Document response schemas for all endpoints

### Phase 3: Polish
7. **Add comprehensive test suite** for permission checks
8. **Improve voting statistics display** (issue #325) with error state handling
9. **Fix edit vote loading** (issue #322) with proper async state management

---

## Code Quality Quick Wins

**Backend TODOs to Address:**
- Line 58 in `mw/__init__.py`: Autoswitch HTTP status codes
- Line 366-368 in `rdb.py`: Verify count_map logic  
- Multiple "TODO" markers in API docs for standardization

**Frontend TODOs:**
- Configurable backend URLs for different deploy environments
- Cookie-based "show directions" preference
- Threshold unit translation (e.g., ">0.5" → "at least 2 votes")

---

## Development Environment Notes

- **Backend**: Python 3, Clastic framework, SQLAlchemy ORM
- **Frontend**: Vue 3, Vite, Axios, Cypress E2E tests
- **Database**: MySQL via Toolforge
- **Key Dependencies**: SQLAlchemy, Werkzeug, PyMySQL
- **Testing**: Tox, pytest (backend), Cypress (frontend)
