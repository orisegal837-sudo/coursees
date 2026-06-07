from pathlib import Path
from typing import List
from course_scanner import Course, Section, Lesson

class LayoutGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.style = """
:root {
    --bg-base: #030712;
    --panel-bg: rgba(17, 24, 39, 0.7);
    --panel-border: rgba(255, 255, 255, 0.08);
    --panel-hover: rgba(31, 41, 55, 0.85);
    --text-main: #f9fafb;
    --text-muted: #9ca3af;
    --accent-primary: #8b5cf6;
    --accent-secondary: #14b8a6;
    --shadow-sm: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
    --shadow-glow: 0 0 30px rgba(139, 92, 246, 0.25);
    --radius-xl: 24px;
    --radius-lg: 16px;
    --radius-md: 12px;
    --radius-sm: 8px;
    --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: var(--font-sans);
    background-color: var(--bg-base);
    color: var(--text-main);
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
    line-height: 1.6;
}

.bg-mesh {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: -1;
    background: 
        radial-gradient(circle at 15% 50%, rgba(76, 29, 149, 0.15), transparent 40%),
        radial-gradient(circle at 85% 30%, rgba(15, 118, 110, 0.15), transparent 40%),
        radial-gradient(circle at 50% 80%, rgba(17, 24, 39, 0.9), transparent 60%);
    background-size: 150% 150%;
    animation: gradientMove 20s ease-in-out infinite alternate;
}

@keyframes gradientMove {
    0% { background-position: 0% 0%; }
    100% { background-position: 100% 100%; }
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 60px 24px;
}

h1 {
    font-size: 3.5rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin-bottom: 1rem;
    background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: slideDown 0.6s ease-out forwards;
}

p.subtitle {
    color: var(--text-muted);
    font-size: 1.25rem;
    margin-bottom: 4rem;
    max-width: 600px;
    animation: slideDown 0.8s ease-out forwards;
}

@keyframes slideDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

.course-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 32px;
}

.course-card {
    background: var(--panel-bg);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius-xl);
    padding: 32px;
    text-decoration: none;
    color: inherit;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    animation: fadeIn 0.8s ease-out forwards;
    opacity: 0;
    transform: translateY(20px);
}

@keyframes fadeIn {
    to { opacity: 1; transform: translateY(0); }
}

.course-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(120deg, transparent, rgba(255,255,255,0.03), transparent);
    transform: translateX(-100%);
    transition: transform 0.6s;
}

.course-card:hover {
    transform: translateY(-8px) scale(1.02);
    border-color: rgba(139, 92, 246, 0.5);
    box-shadow: var(--shadow-lg), var(--shadow-glow);
    background: var(--panel-hover);
}

.course-card:hover::before {
    transform: translateX(100%);
}

.course-card h3 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 16px;
    color: #fff;
    line-height: 1.3;
}

.course-card .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 24px;
}

.meta-tag {
    background: rgba(255, 255, 255, 0.05);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-muted);
    border: 1px solid rgba(255,255,255,0.05);
    transition: all 0.2s ease;
}

.course-card:hover .meta-tag {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
}

.back-link {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--accent-secondary);
    text-decoration: none;
    font-weight: 600;
    margin-bottom: 32px;
    transition: all 0.3s ease;
    padding: 10px 20px;
    border-radius: 30px;
    background: rgba(20, 184, 166, 0.1);
    border: 1px solid rgba(20, 184, 166, 0.2);
}

.back-link:hover {
    background: rgba(20, 184, 166, 0.2);
    border-color: rgba(20, 184, 166, 0.4);
    transform: translateX(-4px);
    box-shadow: 0 4px 12px rgba(20, 184, 166, 0.15);
}

.curriculum-container {
    display: flex;
    flex-direction: column;
    gap: 24px;
    margin-top: 20px;
}

details.section-container {
    background: var(--panel-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    transition: all 0.3s ease;
}

details.section-container[open] {
    border-color: rgba(139, 92, 246, 0.4);
    box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}

summary.section-header {
    padding: 24px;
    font-size: 1.25rem;
    font-weight: 600;
    cursor: pointer;
    list-style: none;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255,255,255,0.02);
    transition: background 0.2s ease;
}

summary.section-header:hover {
    background: rgba(255,255,255,0.05);
}

summary.section-header::after {
    content: '+';
    font-size: 1.8rem;
    font-weight: 300;
    color: var(--accent-primary);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    line-height: 1;
}

details[open] summary.section-header::after {
    transform: rotate(45deg);
    color: var(--text-main);
}

summary::-webkit-details-marker {
    display: none;
}

.lesson-list {
    padding: 0;
    border-top: 1px solid var(--panel-border);
    animation: slideDownFade 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideDownFade {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

.lesson-item {
    padding: 20px 24px;
    border-bottom: 1px solid var(--panel-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: background 0.2s ease;
}

.lesson-item:last-child {
    border-bottom: none;
}

.lesson-item:hover {
    background: rgba(255,255,255,0.03);
}

.lesson-title {
    font-weight: 500;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    gap: 16px;
    color: var(--text-main);
}

.lesson-title::before {
    content: '';
    display: block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-muted);
    transition: background 0.3s;
}

.lesson-item:hover .lesson-title::before {
    background: var(--accent-primary);
    box-shadow: 0 0 10px var(--accent-primary);
}

.btn-group {
    display: flex;
    gap: 12px;
}

.btn {
    padding: 8px 18px;
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    display: inline-flex;
    align-items: center;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    backdrop-filter: blur(4px);
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    filter: brightness(1.2);
}

.btn:active {
    transform: translateY(0);
}

.btn-theory { background: rgba(139, 92, 246, 0.15); color: #c4b5fd; border: 1px solid rgba(139, 92, 246, 0.3); }
.btn-theory:hover { background: rgba(139, 92, 246, 0.25); border-color: rgba(139, 92, 246, 0.6); }

.btn-guide { background: rgba(20, 184, 166, 0.15); color: #5eead4; border: 1px solid rgba(20, 184, 166, 0.3); }
.btn-guide:hover { background: rgba(20, 184, 166, 0.25); border-color: rgba(20, 184, 166, 0.6); }

.btn-task { background: rgba(245, 158, 11, 0.15); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.3); }
.btn-task:hover { background: rgba(245, 158, 11, 0.25); border-color: rgba(245, 158, 11, 0.6); }

.btn-test { background: rgba(239, 68, 68, 0.15); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); }
.btn-test:hover { background: rgba(239, 68, 68, 0.25); border-color: rgba(239, 68, 68, 0.6); }
"""

    def generate_dashboard(self, courses: List[Course]):
        cards_html = ""
        for i, course in enumerate(courses):
            lesson_count = self._count_lessons(course)
            task_count = self._count_tasks(course)
            test_count = self._count_tests(course)
            
            meta_html = f'<span class="meta-tag">{len(course.sections)} Sections</span>'
            meta_html += f'<span class="meta-tag">{lesson_count} Lessons</span>'
            if task_count > 0:
                meta_html += f'<span class="meta-tag">{task_count} Task{"s" if task_count > 1 else ""}</span>'
            if test_count > 0:
                meta_html += f'<span class="meta-tag">{test_count} Test{"s" if test_count > 1 else ""}</span>'
                
            # Add inline animation delay for stagger effect
            delay = i * 0.1
            
            cards_html += f"""
            <a href="{course.name}_curriculum.html" class="course-card" style="animation-delay: {delay}s">
                <div>
                    <h3>{course.name.replace('_', ' ').title()}</h3>
                    <div class="meta">{meta_html}</div>
                </div>
            </a>
            """

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Course Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>{self.style}</style>
</head>
<body>
    <div class="bg-mesh"></div>
    <div class="container">
        <h1>Learning Dashboard</h1>
        <p class="subtitle">Explore and continue your learning journey across all courses.</p>
        <div class="course-grid">
            {cards_html}
        </div>
    </div>
</body>
</html>
"""
        (self.output_dir / "index.html").write_text(html, encoding="utf-8")

    def generate_curriculum(self, course: Course):
        content_html = ""
        for i, section in enumerate(course.sections):
            content_html += f"""
            <details class="section-container" {"open" if i == 0 else ""}>
                <summary class="section-header">
                    <span>{section.name.replace('_', ' ').title()}</span>
                </summary>
                <div class="lesson-list">
                    {self._render_lessons(section.lessons)}
                    {self._render_section_assessments(section)}
                </div>
            </details>
            """

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{course.name.replace('_', ' ').title()} Curriculum</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>{self.style}</style>
</head>
<body>
    <div class="bg-mesh"></div>
    <div class="container">
        <a href="index.html" class="back-link">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
            Back to Dashboard
        </a>
        <h1>{course.name.replace('_', ' ').title()}</h1>
        <div class="curriculum-container">
            {content_html}
        </div>
    </div>
</body>
</html>
"""
        (self.output_dir / f"{course.name}_curriculum.html").write_text(html, encoding="utf-8")

    def _render_lessons(self, lessons: List[Lesson]) -> str:
        html = ""
        for lesson in lessons:
            btns = ""
            if lesson.theory_path:
                rel_path = lesson.theory_path.as_posix()
                btns += f'<a href="{rel_path}" class="btn btn-theory">Theory</a>'
            if lesson.guide_path:
                rel_path = lesson.guide_path.as_posix()
                btns += f'<a href="{rel_path}" class="btn btn-guide">Guide</a>'
            if lesson.task_path:
                rel_path = lesson.task_path.as_posix()
                btns += f'<a href="{rel_path}" class="btn btn-task">Task</a>'
            
            html += f"""
            <div class="lesson-item">
                <span class="lesson-title">{lesson.title.replace('_', ' ').replace('-', ' ').title()}</span>
                <div class="btn-group">
                    {btns}
                </div>
            </div>
            """
        return html

    def _render_section_assessments(self, section: Section) -> str:
        html = ""
        if section.task_path:
            rel_path = section.task_path.as_posix()
            html += f"""
            <div class="lesson-item">
                <span class="lesson-title">Section Task</span>
                <div class="btn-group">
                    <a href="{rel_path}" class="btn btn-task">Task</a>
                </div>
            </div>
            """
        if section.test_path:
            rel_path = section.test_path.as_posix()
            html += f"""
            <div class="lesson-item">
                <span class="lesson-title">Section Test</span>
                <div class="btn-group">
                    <a href="{rel_path}" class="btn btn-test">Test</a>
                </div>
            </div>
            """
        return html

    def _count_lessons(self, course: Course) -> int:
        return sum(len(s.lessons) for s in course.sections)

    def _count_tasks(self, course: Course) -> int:
        return sum(1 for s in course.sections if s.task_path)

    def _count_tests(self, course: Course) -> int:
        return sum(1 for s in course.sections if s.test_path)
