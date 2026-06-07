import pytest
from pathlib import Path
from course_scanner import CourseScanner, Section, Lesson, Course
from layout_generator import LayoutGenerator

def test_section_task_detection(tmp_path):
    # Setup: Create a mock course structure with a section task
    course_dir = tmp_path / "courses" / "my_course"
    section_dir = course_dir / "01_intro"
    section_dir.mkdir(parents=True)
    
    task_file = section_dir / "final_task.html"
    task_file.write_text("<h1>Section Task</h1>")
    
    lesson_file = section_dir / "lesson1.html"
    lesson_file.write_text("<h1>Lesson 1</h1>")
    
    # Execution
    scanner = CourseScanner(tmp_path / "courses")
    courses = scanner.scan()
    
    # Verification
    assert len(courses) == 1
    course = courses[0]
    assert len(course.sections) == 1
    section = course.sections[0]
    
    # Behavior 1: Task path is correctly set
    assert section.task_path == task_file
    
    # Behavior 2: Task file is NOT in lessons
    lesson_titles = [l.title for l in section.lessons]
    assert "final_task" not in lesson_titles
    assert len(section.lessons) == 1
    assert section.lessons[0].title == "lesson1"

def test_section_task_rendering(tmp_path):
    # Setup
    section = Section(name="intro")
    section.task_path = Path("courses/my_course/intro/final_task.html")
    section.lessons = [Lesson(title="lesson1", theory_path=Path("courses/my_course/intro/lesson1.html"))]
    
    course = Course(name="my_course", sections=[section])
    
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Execution
    generator = LayoutGenerator(output_dir)
    generator.generate_curriculum(course)
    
    # Verification
    curriculum_file = output_dir / "my_course_curriculum.html"
    assert curriculum_file.exists()
    content = curriculum_file.read_text(encoding="utf-8")
    
    # Behavior 3: Section Task button is rendered
    assert "Section Task" in content
    assert 'href="courses/my_course/intro/final_task.html"' in content
    assert 'class="btn btn-task"' in content

def test_section_test_styling(tmp_path):
    # Setup
    section = Section(name="intro")
    section.test_path = Path("courses/my_course/intro/test.html")
    course = Course(name="my_course", sections=[section])
    
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Execution
    generator = LayoutGenerator(output_dir)
    generator.generate_curriculum(course)
    
    # Verification
    curriculum_file = output_dir / "my_course_curriculum.html"
    content = curriculum_file.read_text(encoding="utf-8")
    
    # Behavior 4: Section Test button is rendered with specific class
    assert "Section Test" in content
    assert 'class="btn btn-test"' in content
    
    # Behavior 5: CSS for btn-test exists and is red
    assert ".btn-test { background: #ef4444; color: white; }" in content

def test_dashboard_assessment_counts(tmp_path):
    # Setup
    section1 = Section(name="intro", task_path=Path("task1.html"))
    section2 = Section(name="adv", test_path=Path("test1.html"))
    course = Course(name="my_course", sections=[section1, section2])
    
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Execution
    generator = LayoutGenerator(output_dir)
    generator.generate_dashboard([course])
    
    # Verification
    dashboard_file = output_dir / "index.html"
    content = dashboard_file.read_text(encoding="utf-8")
    
    # Behavior 6: Assessment counts are rendered on the dashboard card
    assert "1 Task" in content
    assert "1 Test" in content
    assert "2 Sections" in content
