# Prompt for Fixing the Image Compression API

## Task Description

You are a senior software engineer tasked with fixing a Flask image compression API that has critical memory overflow issues. The current implementation in `issue_project/` contains intentional bugs that cause `MemoryError` crashes when processing large images.

## Your Mission

**Create a fixed version of this project in a NEW directory** `issue_project_fixed/` with all issues resolved. DO NOT modify the original project.

## Current Project Structure

```
issue_project/
├── src\
│   ├── __init__.py
│   └── app.py                 # Contains memory overflow bugs
├── tests\
│   ├── __init__.py
│   ├── test_image_api.py      # Integration tests (2 currently failing)
│   └── test_memory_handling.py # Unit tests (4 currently failing)
├── data\
│   └── .gitkeep
├── requirements.txt
├── .gitignore
├── README.md
├── KNOWN_ISSUE.md             # Detailed issue documentation
└── FIX_PROMPT.md              # This file
```

## Required Fixed Project Structure

Create the following structure in `issue_project_fixed/`:

```
issue_project_fixed/
├── src\
│   ├── __init__.py
│   └── app.py                 # FIXED version with all issues resolved
├── tests\
│   ├── __init__.py
│   ├── test_image_api.py      # Updated tests - ALL should PASS
│   └── test_memory_handling.py # Updated tests - ALL should PASS
├── data\
│   └── .gitkeep
├── requirements.txt           # Same or updated dependencies
├── .gitignore                 # Same as original
├── README.md                  # Updated to reflect fixed version
└── FIXES_APPLIED.md           # NEW: Document what you fixed and how
```

## Issues to Fix

Review the original project and identify all issues documented in `KNOWN_ISSUE.md`. The main problems are:

1. **Missing upload size limit** - Flask configuration issue
2. **No pre-processing file size validation** - Missing validation before image processing
3. **Inadequate exception handling** - MemoryError not properly caught and handled
4. **Missing error responses** - No user-friendly error messages for oversized files

## Requirements

### 1. Code Fixes
- Fix all memory-related issues in `src\app.py`
- Implement proper file size validation
- Add appropriate exception handling
- Configure Flask security settings correctly
- Ensure the API returns proper HTTP status codes (413, 400) for errors
- Add helpful error messages for users

### 2. Test Updates
- Update all tests in `tests\test_image_api.py` to work with the fixed implementation
- Update all tests in `tests\test_memory_handling.py` to work with the fixed implementation
- Remove `@pytest.mark.xfail` decorators - all tests should PASS
- Update test assertions to match the new correct behavior
- Ensure all tests validate the fixes properly

### 3. Documentation
- Create `README.md` explaining the fixed version
- Create `FIXES_APPLIED.md` documenting:
  - What issues were found
  - How each issue was fixed
  - Code changes made (file, line numbers, before/after)
  - Test results showing all tests pass
  - Any additional improvements made

### 4. Validation
- All tests must pass when running `pytest -v`
- The API should handle large file uploads gracefully
- No MemoryError crashes
- Proper HTTP status codes returned
- Clear error messages for users

## Constraints

- Use the same technology stack (Flask, Pillow, pytest)
- Keep the code simple and readable
- Maintain backward compatibility for valid requests
- Follow Python best practices
- Add comments explaining security/safety measures

## Deliverables Checklist

- [ ] New directory created: `issue_project_fixed/`
- [ ] Fixed `src\app.py` with all issues resolved
- [ ] Updated `tests\test_image_api.py` with passing tests
- [ ] Updated `tests\test_memory_handling.py` with passing tests
- [ ] All dependencies in `requirements.txt`
- [ ] Updated `README.md` for the fixed version
- [ ] New `FIXES_APPLIED.md` documenting all changes
- [ ] All tests pass: `pytest -v` shows 0 failures
- [ ] Code is well-commented and production-ready

## Testing Instructions

After creating the fixed version, verify:

```powershell
cd issue_project_fixed

# Install dependencies
pip install -r requirements.txt

# Run all tests - should show 0 failures
pytest -v

# Expected output: All tests PASSED
```

## Success Criteria

Your fix is complete when:
1. ✅ All tests pass without `xfail` markers
2. ✅ Large file uploads return HTTP 413 with clear error messages
3. ✅ No MemoryError exceptions occur
4. ✅ Service remains stable under large file uploads
5. ✅ Documentation clearly explains all fixes applied

## Additional Notes

- Study the original `KNOWN_ISSUE.md` for detailed problem analysis
- Review the failing tests to understand expected behavior
- Implement fixes incrementally and test each change
- Consider edge cases and security implications
- Make the code production-ready, not just test-passing

---

**Remember**: Create all files in `issue_project_fixed/`, not in the original project directory.
