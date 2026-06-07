from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

import re

@dataclass
class Lesson:
    title: str
    theory_path: Optional[Path] = None
    guide_path: Optional[Path] = None
    task_path: Optional[Path] = None

@dataclass
class Section:
    name: str
    lessons: List[Lesson] = field(default_factory=list)
    task_path: Optional[Path] = None
    test_path: Optional[Path] = None

@dataclass
class Course:
    name: str
    is_flat: bool = True
    sections: List[Section] = field(default_factory=list)
    lessons: List[Lesson] = field(default_factory=list)

class CourseScanner:
    def __init__(self, courses_root: Path):
        self.courses_root = Path(courses_root)

    def scan(self) -> List[Course]:
        courses = []
        if not self.courses_root.exists():
            return courses

        # Sort courses naturally
        items = sorted(self.courses_root.iterdir(), key=lambda i: self._natural_sort_key(i.name))
        for item in items:
            if item.is_dir():
                course = self._scan_course(item)
                if not course.is_flat:
                    courses.append(course)
        
        return courses

    def _natural_sort_key(self, s: str):
        """Helper to sort strings containing numbers naturally (1, 2, 10 instead of 1, 10, 2)"""
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    def _scan_course(self, course_path: Path) -> Course:
        sections = []
        is_flat = True

        # Sort potential sections naturally
        items = sorted(course_path.iterdir(), key=lambda i: self._natural_sort_key(i.name))
        for item in items:
            if item.is_dir():
                is_flat = False
                section = Section(name=item.name)
                
                # Check for section assessments
                task_path = item / "final_task.html"
                test_path = item / "test.html"
                if task_path.exists(): section.task_path = task_path
                if test_path.exists(): section.test_path = test_path
                
                section.lessons = self._get_lessons(item)
                sections.append(section)
        
        lessons = self._get_lessons(course_path) if is_flat else []

        return Course(
            name=course_path.name,
            is_flat=is_flat,
            sections=sections,
            lessons=lessons
        )

    def _get_lessons(self, path: Path) -> List[Lesson]:
        lesson_map = {}
        
        items = sorted(path.iterdir(), key=lambda i: self._natural_sort_key(i.name))
        for item in items:
            if item.is_dir():
                # Lesson Folder structure
                lesson = Lesson(title=item.name)
                t_path = item / "lesson.html"
                g_path = item / "practical_guide.html"
                k_path = item / "practical_task.html"
                
                if t_path.exists(): lesson.theory_path = t_path
                if g_path.exists(): lesson.guide_path = g_path
                if k_path.exists(): lesson.task_path = k_path
                
                if any([lesson.theory_path, lesson.guide_path, lesson.task_path]):
                    lesson_map[item.name] = lesson
                    
            elif item.is_file() and item.suffix == ".html":
                stem = item.stem
                
                # Exclude section-level assessments
                if stem in ["final_task", "test"]:
                    continue
                
                # Check for suffixes (flat structure)
                if stem.endswith("-practical_guide"):
                    base_title = stem.replace("-practical_guide", "")
                    lesson = lesson_map.setdefault(base_title, Lesson(title=base_title))
                    lesson.guide_path = item
                elif stem.endswith("-practical_task"):
                    base_title = stem.replace("-practical_task", "")
                    lesson = lesson_map.setdefault(base_title, Lesson(title=base_title))
                    lesson.task_path = item
                else:
                    base_title = stem
                    lesson = lesson_map.setdefault(base_title, Lesson(title=base_title))
                    lesson.theory_path = item
                    
        return sorted(lesson_map.values(), key=lambda l: self._natural_sort_key(l.title))
