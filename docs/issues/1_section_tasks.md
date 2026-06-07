## What to build
Implement support for section-level tasks. This includes updating the data model, extending the scanner to detect `section_task.html` (while filtering it from lessons), rendering the "Section Task" button in the curriculum UI, and adding comprehensive tests.

## Acceptance criteria
- [ ] `Section` dataclass has `task_path: Optional[Path]`
- [ ] `CourseScanner` detects `section_task.html` and assigns it to `section.task_path`
- [ ] `section_task.html` does NOT appear as a regular lesson in the UI
- [ ] `LayoutGenerator` renders a "Section Task" row at the end of the lesson list
- [ ] Unit tests for `CourseScanner` and `LayoutGenerator` pass
- [ ] Integration test in `manage_ui.py` workflow passes

## Blocked by
None - can start immediately
