from math import trunc
from typing import Any
from mcp.types import Content
from openai import AsyncOpenAI 
from pydantic import BaseModel,Field
import asyncio
from dotenv import load_dotenv 
from agents import Agent, HostedMCPTool, Runner, WebSearchTool
from agents.mcp import MCPServerStdio
import os
from pydantic import BaseModel
import ast
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
) 
import re
import aiohttp
from bs4 import BeautifulSoup
from tasks import  create_guide_html, create_task_html ,create_lesson_html, create_test_html
from urls import extract_multiple_urls, get_urls



INVALID_CHARS = r'[<>:"/\\|?*]'
def sanitize_name(name: str, max_len: int = 240) -> str:
    name = re.sub(INVALID_CHARS, '_', name)
    name = name.rstrip(' .')  # Windows disallows trailing space/dot
    return name[:max_len] if name else 'untitled'

MAX_CONCURRENT_SEARCHES = 1
search_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

def clean_and_truncate_article(raw_text: str, max_words: int = 1500) -> str:
    """
    Cleans raw web data by stripping HTML tags, removing excessive whitespace,
    and truncating the result to a safe word limit.
    """
    if not isinstance(raw_text, str):
        raw_text = str(raw_text)
    clean_text = re.sub(r'<[^>]+>', ' ', raw_text)
    clean_text = re.sub(r'\s+', ' ', clean_text)
    clean_text = ''.join(char for char in clean_text if char.isprintable())

    # 4. Truncate to a safe word count
    words = clean_text.strip().split(' ')
    if len(words) > max_words:
        # Keep only up to the max_words limit
        words = words[:max_words]
        return " ".join(words) + "... [Content Truncated]"
    return " ".join(words)

class Answer(BaseModel):
    """Represents a single answer option for a test question."""
    answer:str 
    is_correct: bool = Field("Defines whether the option is the answer to the question.")
class Question(BaseModel):
    """Represents a multiple-choice question with a list of options."""
    question: str = Field("The question")
    answers:list[Answer] = Field("The options of answers for the questions. ONE is correct ")
    note: str | None = Field(default=None, description="A note or explanation to be shown after an answer is selected.")
class Test(BaseModel):
    """Represents a full test consisting of a list of questions."""
    questions: list[Question] = Field("A list of questions, for the test. ")

class Lesson(BaseModel):
    subtitle:str
    page_1: str = Field(description="First part of the lesson.")
    page_2: str = Field(description="Second part of the lesson.")
    page_3: str = Field(description="Third part of the lesson.")
    page_4: str = Field(default=None, description="Optional fourth part of the lesson: summary.") 
    is_practical : bool 


class Topics(BaseModel):
    """Represents a list of extracted educational topics."""
    topics:list[str]

class LinkList(BaseModel):
    """Represents a list of extracted URLs."""
    links: list[str] = Field(description="A list of relevant URLs found during the search.")

class PracticalTask(BaseModel):
    """Represents a practical task based on a practical guide."""
    title: str = Field(description="A catchy, clear title for the assignment.")
    learning_objective: str = Field(description="A one-sentence summary of what the student will achieve.")
    givens: str = Field(description="The starting materials, data, constraints, or starter code provided to the student.")
    instructions: list[str] = Field(description="Clear, step-by-step directions on how to complete the task.")
    criteria: list[str] = Field(description="2-3 bullet points explaining what a successful completion of this task looks like.")

class PracticalGuide(BaseModel):
    """Represents a practical guide divided into 3-4 pages."""
    page_1: str = Field(description="First part of the guide: The Objective and Prerequisites.")
    page_2: str = Field(description="Second part of the guide: Initial steps of implementation.")
    page_3: str = Field(description="Third part of the guide: Further steps or advanced implementation.")
    page_4: str | None = Field(default=None, description="Optional fourth part of the guide: Final steps or summary.")

# if there is an error in in_graph_env.py, it is because there was supposed to be a import gym.space line and you removed it and replaced it with gymnasium, you will need to import it again in a smarter way. 
#logging.basicConfig(level=logging.DEBUG, force = True)
        

load_dotenv(override=True)
def parse_html_content(html_content: str) -> str:
    """Parses HTML and extracts text, removing unwanted tags."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for unwanted_tag in soup(['script', 'style', 'noscript','nav','footer', 'header']):
        unwanted_tag.decompose()
    return soup.get_text(separator=' ', strip=True)

class ContentAgent:
    """Agent for generating educational content, tasks, and assessments."""
    def __init__(self) -> None:
        """Initializes the ContentAgent with model and client settings."""
        print("entered init")
        self.model = 'gpt-5.4-mini'
        print("selected model")
        self.client = AsyncOpenAI(max_retries = 5)
        print("defined a client")
            

    async def content_agent(self, curriculum: dict, prior_knowledge: list[str] = []):
        """The dictionary is created here. The content of the lessons is also created here. """
        prior_knowledge_copy = prior_knowledge.copy()
        main_goal = curriculum['main goal']
        tasks = []
        system_message = f"""You are a specialist teacher. Your job is to create a lesson based on the materials for the lesson. 
        The lesson should be in sync with the context of the lesson which is the end goal of the student: {curriculum['main goal']}
        You will also be given a list of subjects that were already learned. Your lesson must not regard these subjects as if they are new to the student.
        You can of course mention them for a reminder if they are required for the understanding of the lesson.
        Also you will be given a list of sources which you need to base your lesson upon.
        You don't need to specify to the student what he already knows. it is not important at all. don't mention the Prerequisites .
        Important: You may not add any sort of task to the lesson. 
          """
        lessons_to_fetch = []
        for section in curriculum.get('sections', []):
            for lesson in section.get('lessons', []):
                lessons_to_fetch.append(lesson)
        print(f"Lessons to fetch: {lessons_to_fetch}")
        # Pass topics="" to avoid TypeError
        coroutines = [asyncio.to_thread(get_urls,lesson['name'],5) for lesson in lessons_to_fetch] 
        print(coroutines)
        course_articles = await asyncio.gather(*coroutines)
        print(f"completed gathering articles")
        lesson_idx = 0
        for j, section in enumerate(curriculum.get('sections', [])):
            section_name = sanitize_name(section['name'])
            section_new_knowledge = []
            section_path = f'section_{j+1}'
            for i,lesson in enumerate(section.get('lessons', [])):
                lesson_name = sanitize_name(lesson['name'])
                articles = course_articles[lesson_idx]
                leeson_path = f'lesson_{i+1}'
                lesson_content = await self.generate_lesson(articles, prior_knowledge_copy,lesson_name, main_goal,section_name)
                new_topics = await self.topics_extraction(prior_knowledge_copy,lesson_content)
                lesson['content'] = "\n".join([lesson_content.page_1,lesson_content.page_2,lesson_content.page_3,lesson_content.page_4])
                lesson_path =  os.path.join("courses",main_goal,section_path, leeson_path,"lesson.html")
                lesson['lesson path'] = lesson_path
                create_lesson_html(lesson_content,lesson_path,lesson_name)
                if lesson_content.is_practical:
                    practical_guide =  await self.practical_guide(lesson_content)
                    lesson['practical guide'] = practical_guide
                    guide_path = os.path.join("courses",main_goal,section_path,leeson_path,"practical_guide.html")
                    create_guide_html(practical_guide, path =  guide_path)
                    lesson['practical guide path'] =  guide_path
                    task_path = os.path.join("courses",main_goal,section_path,leeson_path,"practical_task.html")
                    task_content =  await self.practical_guide_task(practical_guide)
                    lesson['task content'] = task_content
                    create_task_html(task_content, task_path)
                section_new_knowledge.extend(new_topics)
                prior_knowledge_copy.extend(new_topics)
            test,task = await self.task_test_genearator(lessons = section['lessons'], new_knowledge = section_new_knowledge, section = section_name, section_type = 'practical') #placeholder 
            tasks.extend([task,test])
            section['task-test'] = [task,test]
            section_task_path = os.path.join("courses",main_goal,section_path,'final_task.html')
            section['task path'] = section_task_path
            section_test_path = os.path.join("courses",main_goal,section_path,'test.html')
            section['test'] = section_test_path
            create_task_html(task,section_task_path)
            create_test_html(test, section_test_path)
        return curriculum

    async def lesson_topics(self, lesson_name:str,course_goal:str, prior_knowledge:str): 
        """Generates the topics the lesson will talk about """
        system_message = """ROLE -> You are a specialist lesson designer. you will be given a name of lesson and the course name. 
        You need to generate a list of topics that the lesson will talk about.
        
        Context -> [Lesson Name]: The name of the lesson. This is the main general subject of the lesson. 
        [Course Goal]: The goal of the course. The overall content should be in sync with the course.
        [Prior Knowledge]: A list of knowledge which the student already has. You need to make sire the topics won't overlap. 

        Rules -> 
        - The topics must be in sync with the lesson name and should strive for staying in context of the [Course Goal]. 
        - The topics must not overlap the topics in the [Prior Knowledge]. 

        Output -> 
        Output ONLY the topics. 
        """ 
        user_message = f"Please generate topics for the lesson. [Lesson Name]: {lesson_name}, [Course Goal]: {course_goal}, [Prior Knowledge]: {prior_knowledge}"
        response = await self.client.responses.parse(
                    model = self.model,
                    input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
                text_format= Topics
                )
        topics = response.output_parsed.topics
        return topics

    async def generate_lesson(self, articles: list, prior_knowledge: list, lesson_name: str, course_name: str, section_name: str):
    
    # 1. STATIC SYSTEM PROMPT (The Rules, Persona, and Format)
        system_message = """You are an expert instructional designer and specialist lesson creator. Your objective is to craft highly effective, engaging, and targeted educational content.

        ### INSTRUCTIONS
        1.  Mainstream Focus: Teach established, mainstream concepts. Strictly avoid esoteric or fringe material unless necessary to explain the core subject.
        2.  Source Utilization: Synthesize insights from the provided Source Articles if they enhance the core subject.
        3.  Knowledge Scaffolding: Acknowledge the student's Prior Knowledge to build logical bridges, but strictly skip reteaching concepts they already know. Focus on new material.
        4.  Tone: Maintain a clear, encouraging, and highly educational tone.

        ### OUTPUT FORMAT

        You must respond ONLY with a valid JSON object containing exactly 6 keys.
        You may use markdown.  
                {
            subtitle: a brief description of what will be learned
            split the lesson to 4: "page_1",page_2,page_3,page_4. page_4 will be the summary of the lesson. "",
            "practical": decide wether there should be a practical guide following the lesson.  The requirements for practical: the student can complete implement the lesson with only the internet, computer, papaer and a pen.
            If the student wont be able to implement the knowledge with the equpment mentioned above, the lesson is not practical. 
            By practical, the intention is an implementation of the knowledge that was learned in the course. 
        }
        """
        
        # 2. DYNAMIC USER PROMPT (The Variables Passed by the User/System)
        user_message = f"""Please generate a lesson based on the following data:
        * Course Name: {course_name}
        * Section Name: {section_name}
        * Lesson Name: {lesson_name}
        * Prior Knowledge: {prior_knowledge}
        * Source Articles: {articles}
        """
        response = await self.client.responses.parse(
                model = self.model,
                input = [{'role':'system','content' : system_message },
                    {'role':'user','content' : user_message }],
                    text_format = Lesson 
            )

        return response.output_parsed

    async def practical_guide(self,lesson:str):
        system_prompt = """**Role & Objective:**
    You are an Expert Implementation Coach and Technical Writer. Your goal is to bridge the gap between theory and practice. Whenever you receive the text of a "Lesson," your task is to generate a comprehensive, step-by-step **Practical Implementation Guide**. This guide must take the abstract concepts taught in the lesson and translate them into actionable, real-world steps that a user can immediately apply.

    **Core Guidelines:**
    *   **Action-Oriented:** Focus on *how* to do it, not just *what* it is. Use strong action verbs.
    *   **Clarity & Scannability:** Use clear headings, bullet points, numbered lists, and bold text to make the guide easy to follow.
    *   **Contextual Relevance:** Ensure the examples and steps directly reflect the core themes of the provided lesson.
    *   **No Fluff:** Do not summarize the lesson unless briefly necessary to establish context. Dive straight into the application.

    **Required Structure for the Practical Guide:**
    Divide the guide into 3 to 4 distinct parts, each mapped to a page (page_1, page_2, page_3, and optionally page_4).
    
    The guide should cover:
    1.  **The Objective & Prerequisites**: What the user will achieve and what they need. The prerequesities should only be technichal like libraries, or access to a certain api provider or website. 
    The prerequesities have to be specific and not general. The prerequesities should only contain tools from the internet, not physical equipment. 
    2.  **Step-by-Step Implementation**: Broken down into logical phases.
    
    Each step must include:
    *   **The Action**: What exactly to do.
    *   **The "Why"**: A brief note on why this step matters.
    *   **The "How" (Example)**: A concrete, real-world example or template.

    **Input Format:**
    The user will provide the lesson content. Generate the guide according to this structure.
    """
        user_message = f"Please generate a practical guide for this lesson: {lesson}"
        response = await self.client.responses.parse(
                model = self.model,
                input = [{'role':'system','content' : system_prompt },
                    {'role':'user','content' : user_message }],
                    text_format = PracticalGuide
            )
        return response.output_parsed

    async def practical_guide_task(self, guide: PracticalGuide):
        """Generates a final practical challenge based on the provided practical guide."""
        system_prompt= """Role: You are a pragmatic, highly structured Senior Instructional Designer. Your job is to create hands-on tasks that force students to apply new concepts within strict, realistic constraints.

Context: 
[Course Goal]: {course_goal}
[Lesson Name]: {lesson_name}
[Lesson Content]: {lesson_content}
[New Knowledge]: {new_knowledge}

Target Audience Baseline: 
The student understands the theory they just read, but they lack practical experience. If you ask them an open-ended question, they will freeze or provide a generic, useless answer. They need strict boundaries, starting materials, and a clear goal to push against.

Objective: 
Generate an applied, scenario-driven task strictly based on the [New Knowledge], aligned with the broader [Course Goal]. 

Requirements:
1. The "Givens": Do not give the student a blank slate. You MUST provide the starting reality in the `givens` dictionary. Depending on the inferred subject, this must include things like starter code, a raw dataset, a demanding client brief, strict constraints, a budget, or a specific scenario to resolve. 
2. Micro-Focus: The `instructions` must isolate the specific [New Knowledge]. Tell them what actions to take using the `givens`. Do not test them on outside concepts.
3. Concrete Success: The `criteria` must be observable and objective. Avoid vague criteria like "shows understanding." State exactly what the final output should look like or do.

Output Format:
You MUST respond with a strictly valid JSON object matching the following schema. Do not output markdown code blocks or any other text outside the JSON.

{
  "title": "A catchy, clear title for the assignment.",
  "learning_objective": "A one-sentence summary of what the student will achieve.",
  "givens": {
    "Scenario / Client Brief": "The exact context or problem statement.",
    "Data / Starter Code / Budget": "The specific materials or strict constraints they must work with. Provide the actual code/data/text here. You dont have to fill. "
  },
  "instructions": [
    "Step 1: Specific action to take using the givens.",
    "Step 2: Specific action focusing on X."
  ],
  "criteria": [
    "Objective, observable outcome 1",
    "Objective, observable outcome 2"
  ]
}
"""
        user_message = f"Please generate a final challenge based on this practical guide: {guide.model_dump(exclude_none=True)}"
        response = await self.client.responses.parse(
            model = self.model,
            input = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            text_format = PracticalTask
        )
        return response.output_parsed

    async def task_test_genearator(self,lessons:list[str], new_knowledge:list[str],section:str,section_type:str = 'practical'): #need to change the prompt
        """Generates a practical task or a theoretical test based on the section type."""
        system_message = """Role: > You are an expert Instructional Designer and Educational Task Creator. You specialize in designing practical, engaging, and highly relevant assignments that perfectly align with lesson objectives and help students solidify new concepts.

Context: > You will be provided with three inputs:
[Section Name]: The name of the section which the task will be generated for.

[Lessons Summaries]: A list of the lessons that were recently taught.

[New Knowledge]: A list of the specific new concepts, skills, or knowledge points extracted from those lessons (generated by another agent).

Objective: 
Generate an applied, scenario-driven task strictly based on the [New Knowledge], grounded in the context of the [Lesson Summaries]. 

Requirements:
1. The "Givens": Do not give the student a blank slate. You MUST provide the starting reality in the `givens` dictionary. Depending on the inferred subject, this must include things like starter code, a raw dataset, a demanding client brief, strict constraints, a budget, or a specific scenario to resolve. 
2. Focused Application: The `instructions` must isolate the specific [New Knowledge] while naturally weaving in the core elements of the [Lesson Summaries]. Tell them exactly what actions to take using the `givens`. Ensure the difficulty is perfectly suited for a student who has just learned this material. Do not test them on overly advanced or out-of-scope concepts.
3. Concrete Success: The `criteria` must be observable and objective. Avoid vague criteria like "shows understanding." State exactly what the final output should look like or do to prove successful completion.

Output Format:
You MUST respond with a strictly valid JSON object matching the following schema. Do not output markdown code blocks or any other text outside the JSON.

{
  "title": "A catchy, clear title for the assignment.",
  "learning_objective": "A one-sentence summary of what the student will achieve.",
  "givens": {
    "Scenario / Client Brief": "The exact context or problem statement.",
    "Data / Starter Code / Budget": "The specific materials or strict constraints they must work with. Provide the actual code/data/text here. You do not have to fill every variable if not applicable."
  },
  "instructions": [
    "Step 1: Specific action to take using the givens.",
    "Step 2: Specific action focusing on the New Knowledge."
  ],
  "criteria": [
    "Objective, observable outcome 1",
    "Objective, observable outcome 2"
  ]
}
"""
        user_message = f"Please generate a task for this section: {section}, The lessons of the section are: {lessons} The new knowledge from this section is : {new_knowledge}"
        response = await self.client.responses.parse(
            model = self.model, 
        input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
                text_format = PracticalTask
        )
        task = response.output_parsed
        system_message = """Role -> You are an expert Test Designer. You excel at creating educational questions that pinpoint the understanding of the learned materials.
            Context -> You will be provided with three inputs: 

            [Section Name]: The name of the section which the tests will be generated for. The general subject  which the lessons are oriented to its understanding. 
            [lessons summaries]: A list of the lessons that were recently taught.
            [New Knowledge]: A list of the specific new concepts, skills, or knowledge points extracted from those lessons (generated by another agent).

            Requirements-> 
            Goal: The goal of the test is to help the student deepen his understanding of the lessons. 
            Difficulty of questions.: Please remember that the student has just learned this topic and it's goal is not to test him, but to help him understand better.
            Make the test appropriate for someone who regards this knowledge as new. It means that you should ask questions beyond what was learned in the courses.  
            Type of options: It is important that the options which are not true will not be obvious.  Make them the same level of complexity and probability. 

            Output Format ->
            Questions: a list of 10 questions:
                Question: The question the user will answer. 
                Answers: a list of four answers.
                    Answer: The string of the answer. 
                    is correct: a bool variable that says if an answer is the correct one 
                                """
        user_message = f"Please generate a test for this section: {section}, The lessons of the section are: {lessons} The new knowledge from this section is : {new_knowledge}"
        response = await self.client.responses.parse(
            model = self.model,
            input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
                text_format = Test
        )
        test = response.output_parsed
        return test,task


    
    async def topics_extraction(self,prior_knowledge:list[str], lesson_content:str):
        """Extracts new educational topics from a given lesson text."""
        system_message = f"""You are a professional text analyzer. Your job is to extract out of a given a text what new topics that were learned in the lesson. 
        You need to make sure that you dont pick topics that already exist in this list: {prior_knowledge} """
        user_message = f"""*the lesson* : {lesson_content} """
        response = await self.client.responses.parse(
                    model = self.model,
                    input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
                text_format= Topics
                )
        new_topics = response.output_parsed.topics
        return new_topics
        
   
    @retry(
    wait=wait_random_exponential(multiplier=1, max=10), 
    stop=stop_after_attempt(5)
)
    async def search_links_agent(self, query: str,):
        print(f"DEBUG: [search_links_agent] Starting search for query: '{query}'")
        async with search_semaphore:
            print(f"DEBUG: [search_links_agent] Acquired semaphore for query: '{query}'")
            """Searches for links related to a query without fetching content."""
            instructions = """You are a link researcher. 
            Your task is to search for the given query and return a list of relevant URLs. 
            Provide only links that are from educational or informative websites. Aim to refrain from Q&A.
            DO NOT fetch the content of the pages. Just provide the links.
            """
            env = os.environ.copy()
            search_params = {
                'command': 'npx.cmd',
                'args': ["-y", "open-websearch"],
                'env': env
            }
            # 3. Create a fresh, isolated server instance FOR THIS AGENT ONLY
            print(f"DEBUG: [search_links_agent] Initializing MCPServerStdio for query: '{query}'")
            local_search_server = MCPServerStdio(
                name=f'search_server_{query}', 
                params=search_params, 
                client_session_timeout_seconds=30
            )
            print(f"DEBUG: [search_links_agent] Starting MCPServerStdio for query: '{query}'")
            async with local_search_server:
                print(f"DEBUG: [search_links_agent] MCPServerStdio is up. Creating Agent for query: '{query}'")
                agent = Agent(
                    name='link_search_agent',
                    model='gpt-4o-mini',
                    instructions=instructions,
                    mcp_servers=[local_search_server],
                    output_type=LinkList
                )
            
                print(f"DEBUG: [search_links_agent] Running Agent for query: '{query}'")
                result = await Runner.run(agent, input=f"Search for links related to: {query}", max_turns=10)
                print(f"DEBUG: [search_links_agent] Agent finished for query: '{query}'")
        return result.final_output


    async def extract_page(self, session: aiohttp.ClientSession, url: str):
        """Worker function: Fetches a single URL and extracts ALL readable text with edge-case handling."""
        if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
            return {"url": url, "status": "failed", "error": "Invalid or empty URL"}

        try:
            # Increased timeout slightly and added more granular control
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            async with session.get(url, timeout=timeout, allow_redirects=True) as response:
                # 1. Check Content-Type to avoid downloading large binaries (images, PDFs, etc.)
                content_type = response.headers.get('Content-Type', '').lower()
                if 'text/html' not in content_type:
                    return {"url": url, "status": "failed", "error": f"Unsupported content type: {content_type}"}

                # 2. Check HTTP status
                if response.status != 200:
                    return {"url": url, "status": "failed", "error": f"HTTP {response.status}: {response.reason}"}

                # 3. Robust decoding
                content = await response.read()
                try:
                    encoding = response.get_encoding() or 'utf-8'
                    html = content.decode(encoding, errors='ignore')
                except Exception:
                    html = content.decode('utf-8', errors='ignore')

                # 4. Parse and validate content
                full_text = await asyncio.to_thread(parse_html_content, html)
                
                if not full_text or not full_text.strip():
                    return {"url": url, "status": "failed", "error": "No readable text content found"}

                return {"url": url, "status": "success", "full text": full_text.strip()}

        except asyncio.TimeoutError:
            return {"url": url, "status": "failed", "error": "Request timed out"}
        except aiohttp.ClientConnectorError as e:
            return {"url": url, "status": "failed", "error": f"Connection failed: {str(e)}"}
        except aiohttp.ClientError as e:
            return {"url": url, "status": "failed", "error": f"Client error: {str(e)}"}
        except Exception as e:
            return {"url": url, "status": "failed", "error": f"Unexpected error: {str(e)}"}

    async def extract_multiple_urls(self, urls: list[str] | LinkList):
        """extracts multiple urls with one aiohttp session"""
        if isinstance(urls, LinkList):
            urls = urls.links
            
        articles = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        print("Starting batch extraction...")
        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [self.extract_page(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            for result in results:
                if result['status'] == 'success':
                    articles.append(result['full text'])
                else:
                    print(f"Failed to extract {result.get('url')}: {result.get('error')}")
        return articles



async def main():
    """Main function to demonstrate the ContentAgent with sample lessons."""
    content_agent = ContentAgent()
    lessons = [""" The Power of Entropy
In physics, Entropy is a measure of randomness or disorder within a system. The Second Law of Thermodynamics states that the total entropy of an isolated system can never decrease over time; it can only remain constant or increase.
The Lesson: Nature naturally moves from order to chaos. This is why it’s easier to break a glass than to put it back together, and why energy spreads out rather than staying concentrated.""", """ The Speed of Light as a Universal LimitAccording to Einstein’s Special Relativity, light travels at a constant speed of approximately 299,792,458 meters per second in a vacuum. Because space and time are linked (spacetime), as an object approaches the speed of light, time actually slows down for that object relative to a stationary observer.The Lesson: Massive objects can never actually reach the speed of light because the energy required to accelerate them further becomes infinite. Light is the "speed limit" of information in our universe.$$E = mc^2$$ """, """The Symbiosis of Ecosystems
Biology isn't just about individual survival; it’s about interconnectedness. In any given ecosystem, organisms rely on a cycle of energy that starts with producers (plants) and moves through consumers and decomposers.
The Lesson: A "Keystone Species" is an organism that helps hold an entire system together. If you remove one small part of the chain—like a sea otter or a honeybee—the entire structure can collapse. """]
    lessons1 = ["""Think of a variable as a labeled box where you store information. You don't need to tell Python what kind of data you're putting in the box; it figures it out for you.

Integers: Whole numbers (e.g., 5).

Strings: Text, always wrapped in quotes (e.g., "Hello").

Floats: Decimals (e.g., 10.5).

Python
# This is how you "assign" a value
name = "Alice"
age = 25
is_learning = True

print(name) # This outputs: Alice """,
"""In many languages, programmers use curly brackets {} to group code. Python uses indentation (usually four spaces). This makes Python code very clean, but it also means you have to be precise—if your spacing is off, the code won't run!

This is most visible in If-Statements, which allow the program to make decisions.

Python
sugar_level = 10

if sugar_level > 5:
    print("Too sweet!")
else:
    print("Just right.")
Note how the print commands are tucked inside the logic blocks. """,
"""Programming is great for doing repetitive tasks. A List stores multiple items in order, and a For Loop lets you perform an action on every item in that list automatically.

Python
# A list of groceries
fruits = ["Apple", "Banana", "Cherry"]

# A loop that visits each fruit
for fruit in fruits:
    print("I need to buy a " + fruit)
Why this matters: Instead of writing 100 lines of code to handle 100 items, you can write two lines that handle any number of items. """]
    section_name = "Introduction to python."
    section_type = "practical"
    learned_knowledge= []
    for lesson in lessons1: 
        new_topics = await content_agent.topics_extraction(prior_knowledge = learned_knowledge, lesson_content = lesson)
        learned_knowledge.append(new_topics)
    task_test = await content_agent.task_test_genearator(lessons = lessons1, new_knowledge = learned_knowledge, section = section_name, section_type = section_type)
    return task_test
    #task_test = await content_agent.task_test_genearator()


async def main_curriculum():
    """Generates a full curriculum for python basics."""
    content_agent = ContentAgent()
    curriculum = {'main_goal' : 'know the basics of python' , 'sections': 
    [{'name': 'Fundamentals & First Steps',
    'lessons' : [
        {'name' : 'Setting Up & Saying Hello'},
        {'name': 'Variables (Boxes for Your Data)'},
        {'name': 'Basic Data Types'}
    ],
    'type':'practical'}, 
    {'name': 'Logic & Control Flow',
    'lessons': [
        {'name': 'Making Decisions (If/Else Statements)'},
        {'name':'Repeating Actions (For Loops)'},
        {'name': 'Conditional Repetition (While Loops)'}
    ],
    'type':'practical'
    },
    {'name': 'Organizing Data & Code',
    'lessons': [
        {'name': 'Grouping Data (Lists)'},
        {'name': 'Reusable Mini-Programs (Functions)'},
        {'name': 'Algorithmic Thinking & Pseudocode (Theory)'} 
    ],
    'type':'practical'
    }
    ]
}
    curriculum = await content_agent.content_agent(curriculum=curriculum)
    return curriculum

def print_curriculum():
    """Reads curriculum from output.txt and prints the main goal."""
# Open the text file and read its contents into a string
    try:
        with open('output.txt', 'r', encoding='utf-8') as file:
            dict_string = file.read()
        my_dict = ast.literal_eval(dict_string)
        print(my_dict['mPhysics 101'])
        section_name = (['Thermodynamicsain_goal'])
    except FileNotFoundError:
        print("output.txt not found.")

async def test_sources_agent_directly():
    agent = ContentAgent()
    print("initialized the class")
    lesson = "Variables in Python"
    goal = "understand basic python programming"
    print(f"Testing sources_agent for lesson: '{lesson}' with goal: '{goal}'...")
    # Passing 1 for topics as expected by sources_agent signature
    articles = await agent.sources_agent(lesson, goal, topics="1")
    print(f"\nFetched {len(articles)} articles/tool outputs.")
    for i, article in enumerate(articles):
        print(f"\n--- Output Item {i+1} (Preview) ---")
        #Showing first 500 characters to keep output manageable
        content = str(article)
        print(content)
    print (articles)
    print("\nTest complete.")

async def test_search_links_agent():
    agent = ContentAgent()
    query = "Quantum computing"
    print(f"Testing search_links_agent for query: '{query}'...")
    links = await agent.search_links_agent(query)
    print(f"\nFinal Output (Links):\n{links}")
    print("\nTest complete.")

async def test_fetching_pages():
    agent = ContentAgent()
    query = "Quantum computing "
    print(f"Testing search_links_agent for query: '{query}'...")
    env = os.environ.copy()
    search_params = {
        'command': 'npx.cmd',
        'args': ["-y", "open-websearch"],
        'env': env
    }
    
    search_server = MCPServerStdio(name='search server', params=search_params, client_session_timeout_seconds=30)
    links = await agent.search_links_agent(query,search_server)
    print(links)
    pages = await agent.extract_multiple_urls(links)
    for i, page in enumerate(pages):
        print(f"\n================================PAGE: {i+1} ==========================")
        print(page)
    print("\nTest complete.")

async def test_generate_lesson_function():
    agent = ContentAgent()
    articles = ["Entropy is a measure of randomness or disorder within a system.", "The Second Law of Thermodynamics states that the total entropy of an isolated system can never decrease over time; it can only remain constant or increase."]
    prior_knowledge = ["basic math"]
    lesson_name = "Introduction to Entropy"
    course_name = ""
    section_name = "Entropy"
    print(f"Testing generate_lesson for '{lesson_name}'...")
    lesson = await agent.generate_lesson(articles, prior_knowledge, lesson_name, course_name, section_name)
    create_lesson_html(lesson, 'markdown_lesson.html', 'hello there')
    print("\n--- Generated Lesson ---")
    print(f"Subtitle: {lesson.subtitle}")
    print(f"page 1: {lesson.page_1}")
    print(f"Is Practical: {lesson.is_practical}")
    print("Test complete.")

async def workflow():
    curriculum = {'main goal' : 'introduction to biology',
    'sections': [{ 'name': 'hello',
    'lessons': 
        [{'name': 'what is biology'},{'name':'common use cases'}] 
        }]
    }
    prior_knowledge = ['python', 'using llms']
    content_agent = ContentAgent()
    final_curriculum = await content_agent.content_agent(curriculum, prior_knowledge)
    print(final_curriculum)
    return final_curriculum
if __name__ == '__main__':
    asyncio.run(test_generate_lesson_function())