## What to build
Implement support for section-level tests. This includes extending the scanner to detect `section_test.html`, adding a new red button style (`.btn-test`) to the UI, rendering the "Section Test" button in the curriculum UI, and adding comprehensive tests.

## Acceptance criteria
- [ ] `Section` dataclass has `test_path: Optional[Path]`
- [ ] `CourseScanner` detects `section_test.html` and assigns it to `section.test_path`
- [ ] `section_test.html` does NOT appear as a regular lesson in the UI
- [ ] `LayoutGenerator` includes `.btn-test` CSS with background `#ef4444`
- [ ] `LayoutGenerator` renders a "Section Test" button at the end of the lesson list
- [ ] Unit and integration tests cover the new test-specific logic

## Blocked by
- 1_section_tasks.md (for UI placement logic)
