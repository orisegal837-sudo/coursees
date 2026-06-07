import asyncio
import os
from dotenv import load_dotenv
from content_agent import ContentAgent

load_dotenv(override=True)

async def test_generate_lesson():
    """
    Tests the generate_lesson function directly from ContentAgent.
    """
    print("=== Testing generate_lesson ===")
    
    agent = ContentAgent()
    
    # Dummy inputs for testing
    articles = [
        "Python variables are like boxes. You can put things in them and name the boxes.",
        "A string is a sequence of characters enclosed in quotes.",
        "Integers are whole numbers without a fractional part."
    ]
    prior_knowledge = ["Basic computer literacy", "How to turn on a PC"]
    lesson_name = "Variables and Data Types in Python"
    course_name = "Introduction to Python Programming"
    section_name = "Python Basics"
    
    print(f"Calling generate_lesson with:")
    print(f"Lesson: {lesson_name}")
    print(f"Course: {course_name}")
    print(f"Section: {section_name}")
    print("Generating lesson... (this might take a few seconds)")
    
    try:
        lesson_output = await agent.generate_lesson(
            articles=articles,
            prior_knowledge=prior_knowledge,
            lesson_name=lesson_name,
            course_name=course_name,
            section_name=section_name
        )
        
        print("\n=== Lesson Generation Successful! ===")
        print(f"Subtitle: {lesson_output.subtitle}")
        print(f"Is Practical: {lesson_output.is_practical}")
        print("\n--- Page 1 ---")
        print(lesson_output.page_1)
        print("\n--- Page 2 ---")
        print(lesson_output.page_2)
        print("\n--- Page 3 ---")
        print(lesson_output.page_3)
        print("\n--- Page 4 ---")
        print(lesson_output.page_4)
        
    except Exception as e:
        print(f"\nError during lesson generation: {e}")

if __name__ == "__main__":
    asyncio.run(test_generate_lesson())
