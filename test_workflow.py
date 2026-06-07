import asyncio
import os
from dotenv import load_dotenv
from content_agent import ContentAgent, PracticalGuide, PracticalTask, Lesson
from agents.mcp import MCPServerStdio

load_dotenv(override=True)

async def test_section_workflow(section_name: str, lesson_names: list[str], main_goal: str, prior_knowledge: list[str]):
    """
    Tests the workflow:
    1. Look for sources
    2. Create a lesson
    3. Decide whether to create a practical guide (based on lesson.is_practical)
    4. Generate a task
    """
    agent = ContentAgent()
    
    current_prior_knowledge = prior_knowledge.copy()
    env = os.environ.copy()
    search_params = {
        'command': 'npx.cmd',
        'args': ["-y", "open-websearch"],
        'env': env
    }
    
    search_server = MCPServerStdio(name='search server', params=search_params, client_session_timeout_seconds=30)
    print(f"\n=== Testing Section: {section_name} ===")
    
    for i, lesson_name in enumerate(lesson_names):
        print(f"\n--- Lesson {i+1}: {lesson_name} ---")
        
        # 1. Look for sources
        print(f"Step 1: Looking for sources for '{lesson_name}'...")
        # Using search_links_agent + extract_multiple_urls which is the pattern in content_agent.py
        links = await agent.search_links_agent(lesson_name,search_server)
        if not links or not links.links:
            print("Warning: No links found, using empty articles list.")
            articles = []
        else:
            print(f"Found {len(links.links)} links. Fetching content...")
            articles = await agent.extract_multiple_urls(links)
        
        # 2. Create a lesson
        print(f"Step 2: Generating lesson content...")
        lesson_data = await agent.generate_lesson(
            articles=articles,
            prior_knowledge=current_prior_knowledge,
            lesson_name=lesson_name,
            course_name=main_goal,
            section_name=section_name
        )
        print(f"Lesson generated. is_practical: {lesson_data.is_practical}")
        
        # 3 & 4. Decide on practical guide and generate task
        # Extract new knowledge once to use for both task generation (if regular) and prior knowledge update
        new_knowledge = await agent.topics_extraction(current_prior_knowledge, lesson_data.content)
        
        if lesson_data.is_practical:
            print(f"Step 3: Generating practical guide...")
            guide_dict = await agent.practical_guide(lesson_data.content)
            guide = PracticalGuide(**guide_dict)
            print(guide)
            print(f"Step 4: Generating task from practical guide...")
            task = await agent.practical_guide_task(guide)
            print(f"Practical Task Generated: {task.title}")
        else:
            print(f"Step 3: No practical guide requested. Generating regular task...")
            
            print(f"Step 4: Generating regular task...")
            task_text = await agent.lesson_task_generator(
                lesson_name=lesson_name,
                lesson_content=lesson_data.content,
                new_knowledge=new_knowledge,
                course_goal=main_goal
            )
            print(f"Regular Task Generated (truncated): {task_text[:100]}...")
        
        # Update prior knowledge for the next lesson in the loop
        current_prior_knowledge.extend(new_knowledge)

async def main():
    # Example data for a single section with 3 lessons
    section_name = "Agentic AI Architectures"
    lesson_names = [
        "ReAct: Synergizing Reasoning and Acting in LLMs",
        "Plan-and-Execute Patterns for Complex Tasks",
        "Reflection and Self-Correction Loops"
    ]
    main_goal = "Become a Python Agentic AI Engineer"
    prior_knowledge = ["Basic Python", "Introduction to LLMs"]
    
    await test_section_workflow(section_name, lesson_names, main_goal, prior_knowledge)

if __name__ == "__main__":
    asyncio.run(main())
