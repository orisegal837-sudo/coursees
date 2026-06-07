# PRD: Section-Level Assessment Support

## Problem Statement

Currently, the course platform only supports "Theory", "Guide", and "Task" items at the individual **Lesson** level. There is no built-in way to provide assessments (Tasks or Tests) that apply to an entire **Section**. This makes it difficult to design courses that have overarching practical projects or final evaluations for a specific module of learning.

## Solution

The solution is to extend the existing `CourseScanner` and `LayoutGenerator` to recognize and render section-level assessments. These will be identified by the presence of `section_task.html` and `section_test.html` files within a section folder. In the UI, these will be rendered as distinct items at the end of the lesson list for that section, providing a clear progression from individual lesson learning to section-level evaluation.

## User Stories

1. As a student, I want to see a task at the end of a section, so that I can practice all the skills taught in that section through a comprehensive project.
2. As a student, I want to take a test at the end of a section, so that I can verify my mastery of the section's overall objectives.
3. As a student, I want section tests to be visually distinct (e.g., using a red button), so that I can easily identify formal evaluations.
4. As a course creator, I want to simply add `section_task.html` to a section directory and have it automatically appear in the UI, so that I can easily add assessments without updating code or configuration.
5. As a course creator, I want the system to ignore section-level assessment files when generating the lesson list, so that they don't appear as redundant "Lessons".
6. As a student, I want the section assessments to appear at the end of the lesson list, so that there is a logical flow from study to final evaluation.

## Implementation Decisions

- **Data Model:** The `Section` dataclass will be modified to include optional fields for `task_path` and `test_path`.
- **Scanner Extension:** `CourseScanner` will be updated to check for `section_task.html` and `section_test.html` within each section directory during its scan.
- **Lesson Filtering:** The lesson discovery logic in `CourseScanner` will be updated to explicitly skip these section-level assessment files to prevent them from being listed as standard lessons.
- **UI Styling:** A new `.btn-test` CSS class will be added to the layout generator with a red background (#ef4444) to distinguish tests from tasks and guides.
- **UI Rendering:** The `LayoutGenerator` will be updated to render a new "Section Assessment" row at the end of each section's lesson list if a task or test is present.

## Testing Decisions

- **Scanning Accuracy:** Unit tests for `course_scanner.py` will verify that `section_task.html` and `section_test.html` are correctly detected and attached to the `Section` object, and that they are *not* included in the `lessons` list.
- **Rendering Correctness:** Unit tests for `layout_generator.py` will verify that the HTML output correctly includes the new buttons with the proper labels, paths, and CSS classes when section assessments are present in the data model.
- **End-to-End Workflow:** Integration tests for `manage_ui.py` will verify that a full scan and generate cycle on a mock directory structure produces the expected `index.html` and curriculum files with functional links.
- **Test Quality:** Tests will focus on external behavior (ensuring the correct files are found and the correct HTML is produced) rather than internal helper methods.

## Out of Scope

- Support for lesson-level tests (currently only Theory, Guide, and Task are supported at that level).
- Automated grading or result tracking (assessments remain static HTML links).
- Backend persistence of student progress or test scores.

## Further Notes

- This implementation prioritizes simplicity by using file naming conventions over complex configuration files.
- The red color for tests (#ef4444) was chosen to provide strong visual feedback of a high-stakes evaluation.
