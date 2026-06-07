from pathlib import Path
from course_scanner import CourseScanner
from layout_generator import LayoutGenerator

def main():
    # Configuration
    root_dir = Path(".")
    courses_dir = root_dir / "courses"
    output_dir = root_dir
    
    print(f"--- Course Dashboard Generator ---")
    
    # 1. Scan
    print(f"Scanning {courses_dir}...")
    scanner = CourseScanner(courses_dir)
    courses = scanner.scan()
    
    if not courses:
        print("No courses found in the courses/ directory.")
        return

    print(f"Found {len(courses)} courses.")
    for c in courses:
        type_str = "flat" if c.is_flat else "nested"
        print(f" - {c.name} ({type_str})")

    # 2. Generate
    print(f"Generating UI files in {output_dir}...")
    generator = LayoutGenerator(output_dir)
    
    # Main Dashboard
    generator.generate_dashboard(courses)
    print(" - Created index.html")
    
    # Individual Curriculums
    for course in courses:
        generator.generate_curriculum(course)
        print(f" - Created {course.name}_curriculum.html")

    print("\nSuccess! Open index.html in your browser to view the dashboard.")

if __name__ == "__main__":
    main()
