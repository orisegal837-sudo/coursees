from pathlib import Path
from openai import AsyncOpenAI 
from pydantic import BaseModel,Field
import asyncio
from dotenv import load_dotenv 
from google import genai
from google.genai import types as genai_types
from agents import Agent, HostedMCPTool, Runner, WebSearchTool
from agents.mcp import MCPServerStdio
import agents
import os
from pydantic import BaseModel
from pydantic import ValidationError
import sys
import io
import json
# Force standard output to handle UTF-8
#sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class LessonParts(BaseModel):
    """Represents a list of lesson content parts."""
    lesson_parts:list[str]


class PresentLesson: 
    """Handles the transformation of lesson content into presentable formats like HTML."""
    def __init__(self) -> None:
        """Initializes the PresentLesson agent with model and client settings."""
        load_dotenv(override=True)
        #self.style = style 
        #self.curriculum = curriculum
        self.client = AsyncOpenAI()
        self.model = 'gpt-5.4'
        self.google_client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
        self.google_html_model = os.environ.get("GOOGLE_HTML_MODEL", "gemini-2.5-pro")
        
    async def split_lesson(self, lesson:str):
        """Splits a single lesson text into logical parts (pages) using an LLM."""
        system_message = """You are a professional text processor. Your job is to split an educational text to 3-4 parts. 
        The split should be based on the parts of the lesson. Your job is to notice when a new subject is being taught. The change might be subtle.
        *IMPORTANT*: You must not change the text at all. You can cut but you cannot remove or add any word at ALL."""
        user_message = f"Please split this lesson: {lesson}"
        response =await self.client.responses.parse(
            model = 'gpt-5.4-nano-2026-03-17',
            input =  [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
            text_format=LessonParts
        )
        parts = response.output_parsed.lesson_parts
        lesson_parts = {'parts': []}
        for i, part in enumerate(parts): 
            lesson_parts['parts'].append({'id':f'page_{i+1}' ,'content':part})
        return lesson_parts


    async def html_agent(self,lesson_parts:dict,style:str):
        """Generates a complete, responsive HTML page for a lesson module using an LLM."""
        system_message = """
ROLE: You are an Expert UI/UX Front-End Developer specializing in semantic HTML, modern Tailwind CSS, and vanilla JavaScript.

TASK: Generate a complete, responsive, single-file HTML page for a lesson module. You must integrate provided text parts and styling, implement dynamic navigation, and strictly preserve the original Markdown text.

INPUT CONTEXT:
You will be provided with:
<lesson_parts>: The text parts of the lesson, including metadata like 'id', 'position', and 'number'.
<page_style>: Custom CSS that must govern the core style of the page.

DESIGN & LAYOUT REQUIREMENTS:
1. Visual Hierarchy: Structure the layout so the lesson content is the primary, central focus. Secondary metadata (id, position, number) must be placed on the sides (e.g., sidebars or marginalia) so it does not distract from the main educational content.
2. Styling: Seamlessly integrate the custom CSS from <page_style>. Use standard Tailwind utility classes for the structural layout.
3. Section Visibility: Every distinct lesson section container MUST include these exact utility classes: `transition-opacity duration-300 opacity-0 hidden`.

FUNCTIONALITY & JAVASCRIPT:
1. Dynamic Navigation: Create highly visible UI buttons for navigation (e.g., Next/Previous). Write vanilla JavaScript to handle the functionality, toggling between the lesson sections by manipulating the `hidden` and `opacity-0` classes for smooth transitions.
2. Markdown Rendering: 
   - Include the Marked.js library via CDN in the <head>: `<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>`
   - Place the raw Markdown from <lesson_parts> inside a hidden `<textarea id="markdown-source" style="display:none;">` within the `<body>`.
   - Write JavaScript to read the content from this `<textarea>`, parse it using Marked.js, and inject the resulting HTML into the appropriate, visible lesson containers.

STRICT CONSTRAINTS:
1. IMMUTABLE TEXT: You are strictly forbidden from altering the lesson text in any way. Do not add, remove, or summarize content. Do not convert the Markdown to HTML yourself; rely entirely on Marked.js.
2. EXECUTION-READY OUTPUT: Output ONLY the raw HTML code. Do not wrap the output in Markdown code blocks (e.g., ```html). Do not include introductory text, conversational filler, or explanations. The output must be ready to render in a browser exactly as is.
         """
        user_message = f"Please generate a page for this PARTS: {lesson_parts}. Use this STYLE: {style}"
        response = await self.client.responses.create(
                model = self.model,
                input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
            )
        code = response.output_text
        return code


    async def basic_page(self, lesson_parts:dict):
        """Generates individual HTML components for each lesson part without JavaScript."""
        code = "" 
        system_message = f"""# ROLE
You are an Expert UI/UX Front-End Developer specializing in semantic HTML and Tailwind/modern CSS. Your task is to generate a beautifully styled HTML view (component) for a specific section of content and integrate it with any existing views.

# INPUT CONTEXT
- [TEXT]: The actual content that needs to be displayed in this new view.
- [STYLE] (Optional): The style component of the code. 
- [VIEW_NUMBER]: The sequential index of this new view.
- [POSITION]: The structural placement of this new view ("first", "middle", or "last").

# INSTRUCTIONS & CONSTRAINTS

1. DESIGN & STYLING:
   - Make the view suitable for the [STYLE].
   - STRICT CONSTRAINT: Do NOT generate any JavaScript. No `<script>` tags, and no inline JS attributes (like `onclick`). HTML and CSS only.
   - STRICT CONSTRAINT: Don't generate the style at all. generate only one section component.
2. STRUCTURAL REQUIREMENTS:
   - The main wrapping container for the new view MUST have an `id` attribute that exactly matches the [POSITION] value (i.e., `id="first"`, `id="middle"`, or `id="last"`).
   - The main wrapping container MUST include the following exact CSS classes: `transition-opacity duration-300 opacity-100 block`.

3. PAGINATION NAVIGATION:
   Generate visually styled UI buttons for page switching for the new view based strictly on its [POSITION]:
   - If [POSITION] is "first": Render only a "Next Page" button, aligned to the right side of the view.
   - If [POSITION] is "middle": Render a "Previous Page" button aligned to the left, AND a "Next Page" button aligned to the right.
   - If [POSITION] is "last": Render only a "Previous Page" button, aligned to the left side of the view.

# OUTPUT FORMAT
- If [PREVIOUS_CODE] is provided, you MUST append your newly generated view to it and return the **entire, updated code** (containing both the [PREVIOUS_CODE] and the new view). 
- If no [PREVIOUS_CODE] is provided, return just the new view.
- You must not combine the views. Each view has to be separate. 
- Output ONLY the required HTML and CSS code. Do not include introductory text, conversational filler, or explanations.
""" 
        for part in lesson_parts['parts']:
            user_message = f"please generate a HTML view for this TEXT: {part['content']} The VIEW_ID is {part['id']}. The POSITION of the view: {part['position']}. Previous CODE(if any): {code}"
            response = await self.client.responses.create(
                model = self.model,
                input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
            )
            code = response.output_text
        return code

    async def js_agent(self,html:str):
        """Generates JavaScript logic for switching between lesson views."""
        system_message = """# ROLE
You are a JavaScript expert specializing in adding dynamic functionality to HTML code. Your task is to write the <script> and <style> elements required to enable seamless view-switching within a provided multi-view HTML page.

# INPUT CONTEXT
[CODE]: The code you need to add the script to. 

# INSTRUCTIONS & CONSTRAINTS

1. Core Functionality:

Implement the JavaScript logic to switch between the different views using button clicks.
Identify the "views" based on the logical structure of the provided HTML (e.g., distinct <section> or <div> containers acting as pages).
If navigation buttons do not already exist in the code, you must add them logically to enable the switching functionality.

2. Strict Modification Rules:

STRICT CONSTRAINT: Do NOT alter the existing HTML structure, content, or inline styles.
You are ONLY permitted to add:
   - Navigation buttons (only if none exist).
   - A <script> block for the switching and scrolling logic.
   - A <style> block specifically for the opacity transition classes.

3. UX & Design Requirements:
Scroll Behavior: The page must automatically scroll up to the top when switching to a new view.
Transitions: The transition between views must use a smooth CSS opacity change (fade out/fade in).

# OUTPUT FORMAT
Output ONLY the final, complete code (HTML, CSS, and JavaScript combined).
Do not include introductory text, conversational filler, markdown explanations, or comments outside of the code block.
        
         """
        user_message = f'Please generate a page script for this CODE: {html}'
        response = await self.client.responses.create(
                model = self.model,
                input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
            )
    
        response.encoding = 'utf-8'
        code = response.output_text
        return code

    async def presentation(self,lesson:str,style:str):
        """Orchestrates the creation of a full HTML presentation from a lesson text."""
        lesson_parts = await self.split_lesson(lesson =lesson)
        print(f"=============================Lesson Parts:=============================================")
        print(lesson_parts)
        if 1 == 1:
            html = await self.html_agent(lesson_parts=lesson_parts,style = style)
            print(f"=============================HTML:=============================================")
            print(html)
            final_full_page = await self.code_fixer(html)
            print(print(f"============================Final Full Page:============================================="))
            print(final_full_page)
            return final_full_page

    async def code_fixer(self,code:str):
        """Fixes and completes HTML code snippets to ensure they are valid and executable."""

async def main():
    #lesson_parts = """{'parts': [{'id': 'page_1', 'content': 'Welcome to the world of programming! Python is often called a "batteries-included" language because its powerful, yet the syntax is designed to read almost like English.\n\nIn this first lesson, we're going to cover the absolute essentials: **Variables**, **Data Types**, and **Basic Logic**.\n\n---\n\n## 1. The "Box" Metaphor: Variables\nThink of a **variable** as a labeled box. You put a value inside the box so you can remember it and use it later.\n\n```python\n# To create a variable, just give it a name and a value\nuser_name = "Alex"\nuser_age = 25\n```\n\n### Key Rules for Names:\n* Use underscores `_` instead of spaces.\n* Start with a letter (not a number).\n* Case matters: `Age` and `age` are two different boxes!\n\n---\n\n## 2. Common Data Types\nPython is smart enough to know what's inside your "box" based on how you write it.\n\n| Type | Name | Example | Description |\n| :--- | :--- | :--- | :--- |\n| **String** | `str` | `"Hello"` | Text wrapped in quotes. |\n| **Integer** | `int` | `42` | Whole numbers (no decimals). |\n| **Float** | `float` | `3.14` | Numbers with a decimal point. |\n| **Boolean**| `bool` | `True` | Logical values (True or False). |\n\n---\n', 'position': 'first'}, {'id': 'page_2', 'content': '## 3. Lists: The Organized Shelf\nSometimes one box isn\'t enough. A **List** lets you keep multiple items in a specific order.\n\n```python\n# Lists are defined with square brackets []\ncoding_languages = ["Python", "JavaScript", "C++"]\n\n# You can access items by their position (starting at 0!)\nprint(coding_languages[0])  # This outputs: Python\n```\n\n---\n\n## 4. Making Decisions: If Statements\nLogic is what makes a program "smart." We use `if` statements to check a condition. **Indentation** (the space at the start of the line) is how Python knows which code belongs inside the "if" block.\n\n```python\ntemperature = 22\n\nif temperature > 30:\n    print("It\'s a hot day!")\nelif temperature > 15:\n    print("It\'s a nice day.")\nelse:\n    print("Brrr, it\'s cold!")\n```\n\n---\n', 'position': 'middle'}, {'id': 'page_3', 'content': '## 5. Your First "Mini-Project"\nCopy and paste this into a Python editor to see it in action. It combines everything we just learned:\n\n```python\n# 1. Input: Getting data from the user\nname = input("What is your name? ")\nfavorite_number = int(input("What is your favorite number? "))\n\n# 2. Logic: Checking the number\nif favorite_number == 7:\n    print(f"Hey {name}, 7 is a lucky number!")\nelse:\n    print(f"Cool name, {name}. {favorite_number} is a solid choice.")\n```\n\n---\n\n**Quick Tip:** Don\'t worry about memorizing everything. In programming, knowing **how to search** for a solution is just as important as knowing the code itself!\n\nWhat specific goal do you have for learning Python - are you looking to automate tasks, analyze data, or maybe build a website?', 'position': 'last'}]}. """
    lesson = """ Welcome to the frontier of **Agentic AI**. 

In 2026, we’ve moved past the "Chatbot Era." We no longer just ask an AI to write a poem; we ask it to "research this competitor, draft a counter-strategy, and email the marketing team." That shift from *answering* to *acting* is what defines an **Agent**.

In this lesson, we’ll break down how to build these autonomous systems using Python.

---

## 1. The Core Concept: Brain vs. Hands
Traditional AI is a **linear pipeline**: Input $\rightarrow$ LLM $\rightarrow$ Output.
**Agentic AI** is a **loop**. The AI doesn't just talk; it reasons about a goal, chooses a tool, observes the result, and iterates until the job is done.



### The Four Pillars of an Agent:
1.  **Reasoning (The Brain):** The LLM deciding *what* to do.
2.  **Tools (The Hands):** Python functions the agent can call (APIs, databases, web search).
3.  **Memory (The Notebook):** Short-term context (what happened 5 seconds ago) and long-term state.
4.  **Planning (The Roadmap):** Breaking a big goal (e.g., "Plan a trip") into sub-tasks.

---

## 2. Setting Up Your Environment
In 2026, the industry has coalesced around frameworks that prioritize **type safety** and **controllability**. We’ll use `pydantic-ai` for its strict schema validation and `LangGraph` for workflow management.

```bash
pip install pydantic-ai langgraph openai
```

---

## 3. Building Your First Agent
Let’s build a **Code Investigator Agent**. Its goal is to read a local Python file, find a bug, and suggest a fix using a tool.

### Step 1: Define the Tools
Tools are just regular Python functions decorated so the AI knows how to use them.

```python
from pydantic_ai import Agent, RunContext
import os

# This is our 'Hand' - a tool to read files
def read_local_file(ctx: RunContext[str], filename: str) -> str:
    ""Reads a file from the local directory.""
    with open(filename, 'r') as f:
        return f.read()

# Step 2: Initialize the Agent
# We give it a 'system prompt' (its personality/mission)
agent = Agent(
    'openai:gpt-4o', # Or your 2026 model of choice
    system_prompt="You are a senior QA engineer. Use your tools to find bugs.",
    tools=[read_local_file]
)
```

### Step 2: The Execution Loop
When you run this, the Agent doesn't just guess. It calls `read_local_file`, looks at the code, and then provides a final answer.

```python
async def main():
    result = await agent.run("Check 'app.py' for any potential security risks.")
    print(f"Agent's Analysis: {result.data}")

# Logic: 
# 1. Agent thinks: "I need to see app.py first."
# 2. Agent calls: read_local_file(filename="app.py")
# 3. Agent receives: "print(os.getenv('SECRET_KEY'))"
# 4. Agent concludes: "You are leaking your secret key to stdout!"
```

---

## 4. Multi-Agent Orchestration
Real-world tasks are usually too big for one agent. In 2026, we use **Multi-Agent Systems (MAS)**. Think of it like a corporate hierarchy: a **Supervisor Agent** delegates tasks to **Worker Agents**.



### Common Patterns:
* **The Router:** One agent decides which specialist (e.g., "Coder" or "Writer") should handle the prompt.
* **The Orchestrator-Worker:** A lead agent breaks a task into pieces and waits for workers to report back.
* **The Swarm:** Agents work in parallel on a shared "state" (like a shared document).

---

## 5. Why Most Agents Fail (and how to fix it)
Building agents is easy; building *reliable* agents is hard. Here are the "Golden Rules" for 2026:

1.  **Human-in-the-Loop (HITL):** Never let an agent spend 1,000$ on AWS or delete a database without a "confirm" button.
2.  **Observability:** Use tools like *LangSmith* or *Phoenix* to trace every "thought" the agent had. If it failed, was it because the tool returned garbage or the LLM hallucinated?
3.  **Strict Schemas:** Always use Pydantic models for tool inputs. If the agent tries to pass a string where a number is required, the system should catch it before the tool even runs.

---

### Quick Check-In
Building your first agent feels a bit like giving a toddler a chainsaw—exciting but nerve-wracking! Which part of the agentic loop sounds the most challenging to implement for your specific project: the reasoning, the tool integration, or managing the state?"""
    style = """:root{

      --bg: #0b1220;

      --panel: rgba(255,255,255,.06);

      --panel-2: rgba(255,255,255,.08);

      --stroke: rgba(255,255,255,.12);

      --text: rgba(255,255,255,.92);

      --muted: rgba(255,255,255,.72);

      --muted-2: rgba(255,255,255,.62);

      --accent: #7c3aed;

      --accent-2: #22d3ee;

      --shadow: 0 18px 50px rgba(0,0,0,.45);

      --radius-xl: 22px;

      --radius-lg: 16px;

      --radius-md: 12px;

      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;

      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";

    }



    * { box-sizing: border-box; }

    html, body { height: 100%; }

    body{

      margin:0;

      font-family: var(--sans);

      background:

        radial-gradient(1200px 800px at 30% -10%, rgba(124,58,237,.20), transparent 60%),

        radial-gradient(1000px 680px at 90% 10%, rgba(34,211,238,.14), transparent 55%),

        linear-gradient(180deg, #060913 0%, #050712 100%);

      color: var(--text);

    }



    main{

      min-height: 100%;

      display:flex;

      align-items: center;

      justify-content: center;

      padding: 22px;

    }



    section[id]{

      width: min(1100px, 100%);

    }



    .view-shell{

      color: var(--text);

      background:

        radial-gradient(1000px 600px at 10% 0%, rgba(124,58,237,.35), transparent 60%),

        radial-gradient(900px 520px at 90% 20%, rgba(34,211,238,.22), transparent 55%),

        linear-gradient(180deg, #0b1220 0%, #070b14 100%);

      border: 1px solid rgba(255,255,255,.08);

      border-radius: var(--radius-xl);

      box-shadow: var(--shadow);

      overflow: hidden;

    }

    .view-inner{

      padding: clamp(18px, 3.5vw, 34px);

    }

    .topbar{

      display:flex;

      align-items:flex-start;

      justify-content:space-between;

      gap:16px;

      margin-bottom: 18px;

    }

    .badge{

      display:inline-flex;

      align-items:center;

      gap:10px;

      padding: 8px 12px;

      border: 1px solid var(--stroke);

      background: rgba(255,255,255,.05);

      border-radius: 999px;

      color: var(--muted);

      font-size: 13px;

      letter-spacing:.2px;

      backdrop-filter: blur(10px);

      -webkit-backdrop-filter: blur(10px);

    }

    .dot{

      width:10px;height:10px;border-radius:999px;

      background: linear-gradient(135deg, var(--accent), var(--accent-2));

      box-shadow: 0 0 0 4px rgba(124,58,237,.16);

    }

    .title{

      margin: 6px 0 6px 0;

      font-size: clamp(22px, 2.6vw, 34px);

      line-height: 1.15;

      letter-spacing: -.02em;

    }

    .subtitle{

      margin: 0;

      color: var(--muted);

      font-size: 15.5px;

      line-height: 1.6;

      max-width: 78ch;

    }

    .grid{

      display:grid;

      grid-template-columns: 1.05fr .95fr;

      gap: 16px;

      margin-top: 18px;

    }

    @media (max-width: 980px){

      .grid{ grid-template-columns: 1fr; }

      .topbar{ flex-direction: column; align-items: stretch; }

      .chip[aria-label="View ID"]{ align-self:flex-start; }

    }

    .card{

      border: 1px solid var(--stroke);

      background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.04));

      border-radius: var(--radius-lg);

      overflow:hidden;

    }

    .card-h{

      padding: 14px 16px;

      border-bottom: 1px solid rgba(255,255,255,.10);

      background: rgba(255,255,255,.04);

      display:flex;

      align-items:center;

      justify-content:space-between;

      gap: 12px;

    }

    .card-h h2{

      margin:0;

      font-size: 14px;

      letter-spacing: .14em;

      text-transform: uppercase;

      color: rgba(255,255,255,.86);

    }

    .chip{

      font-size: 12px;

      color: rgba(255,255,255,.78);

      border: 1px solid rgba(255,255,255,.14);

      background: rgba(124,58,237,.10);

      padding: 6px 10px;

      border-radius: 999px;

      white-space: nowrap;

    }

    .card-b{

      padding: 16px;

    }

    .p{

      margin: 0 0 12px 0;

      color: var(--muted);

      line-height: 1.7;

      font-size: 15px;

    }

    .strong{

      color: rgba(255,255,255,.92);

      font-weight: 650;

    }

    .rules{

      margin: 12px 0 0 0;

      padding: 0;

      list-style: none;

      display:grid;

      gap: 10px;

    }

    .rule{

      display:flex;

      gap: 10px;

      padding: 10px 12px;

      border: 1px solid rgba(255,255,255,.10);

      background: rgba(255,255,255,.04);

      border-radius: var(--radius-md);

    }

    .rule svg{ flex: 0 0 auto; margin-top: 1px; opacity: .95; }

    .rule b{ color: rgba(255,255,255,.92); }

    .rule span{ color: var(--muted-2); font-size: 14px; line-height: 1.55; }



    .code{

      border: 1px solid rgba(34,211,238,.22);

      background:

        radial-gradient(800px 300px at 20% 0%, rgba(34,211,238,.10), transparent 65%),

        linear-gradient(180deg, rgba(8,12,24,.72), rgba(8,12,24,.92));

      border-radius: var(--radius-lg);

      overflow:hidden;

      margin-top: 12px;

    }

    .code-h{

      display:flex;

      align-items:center;

      justify-content:space-between;

      padding: 10px 12px;

      border-bottom: 1px solid rgba(255,255,255,.10);

      color: rgba(255,255,255,.78);

      font-size: 12.5px;

    }

    .code-dots{

      display:flex; gap:6px; align-items:center;

    }

    .code-dots i{

      width:10px;height:10px;border-radius:999px; display:inline-block;

      background: rgba(255,255,255,.22);

    }

    .code pre{

      margin:0;

      padding: 14px 14px 16px 14px;

      font-family: var(--mono);

      font-size: 13.5px;

      line-height: 1.65;

      color: rgba(255,255,255,.90);

      overflow:auto;

      tab-size: 2;

    }

    .kw{ color: #a78bfa; }

    .cm{ color: rgba(255,255,255,.55); }

    .st{ color: #67e8f9; }

    .nu{ color: #fbbf24; }



    .table-wrap{

      overflow:auto;

      border-radius: var(--radius-lg);

      border: 1px solid rgba(255,255,255,.10);

      background: rgba(255,255,255,.03);

    }

    table{

      width:100%;

      border-collapse: separate;

      border-spacing: 0;

      min-width: 640px;

      color: rgba(255,255,255,.86);

      font-size: 14px;

    }

    thead th{

      text-align:left;

      font-size: 12px;

      letter-spacing: .14em;

      text-transform: uppercase;

      color: rgba(255,255,255,.72);

      background: rgba(255,255,255,.05);

      padding: 12px 12px;

      border-bottom: 1px solid rgba(255,255,255,.10);

      position: sticky;

      top: 0;

      backdrop-filter: blur(10px);

      -webkit-backdrop-filter: blur(10px);

      z-index: 1;

    }

    tbody td{

      padding: 12px 12px;

      border-bottom: 1px solid rgba(255,255,255,.08);

      vertical-align: top;

      color: rgba(255,255,255,.82);

    }

    tbody tr:hover td{

      background: rgba(124,58,237,.06);

    }

    .pill{

      display:inline-flex;

      align-items:center;

      gap:8px;

      padding: 6px 10px;

      border-radius: 999px;

      border: 1px solid rgba(255,255,255,.14);

      background: rgba(255,255,255,.04);

      font-family: var(--mono);

      font-size: 13px;

      color: rgba(255,255,255,.88);

      white-space: nowrap;

    }

    .pill i{

      width:8px;height:8px;border-radius:999px; display:inline-block;

      background: linear-gradient(135deg, var(--accent), var(--accent-2));

      opacity:.95;

    }



    .nav{

      display:flex;

      align-items:center;

      justify-content:flex-end;

      gap: 12px;

      padding: 16px clamp(18px, 3.5vw, 34px);

      border-top: 1px solid rgba(255,255,255,.10);

      background: rgba(255,255,255,.03);

    }

    .btn{

      display:inline-flex;

      align-items:center;

      justify-content:center;

      gap: 10px;

      padding: 10px 14px;

      border-radius: 999px;

      border: 1px solid rgba(255,255,255,.14);

      background: rgba(255,255,255,.04);

      color: rgba(255,255,255,.90);

      text-decoration:none;

      font-size: 14px;

      line-height: 1;

      transition: transform .15s ease, background .15s ease, border-color .15s ease, box-shadow .15s ease;

      user-select:none;

      white-space: nowrap;

    }

    .btn:hover{

      background: rgba(255,255,255,.07);

      border-color: rgba(255,255,255,.18);

      transform: translateY(-1px);

      box-shadow: 0 10px 25px rgba(0,0,0,.25);

    }

    .btn:focus-visible{

      outline: 2px solid rgba(34,211,238,.55);

      outline-offset: 3px;

    }

    .btn-primary{

      border-color: rgba(34,211,238,.30);

      background: linear-gradient(135deg, rgba(124,58,237,.22), rgba(34,211,238,.16));

    }

    .btn svg{ opacity:.9; }

    .sr-only{

      position:absolute;

      width:1px;height:1px;

      padding:0;margin:-1px;

      overflow:hidden;clip:rect(0,0,0,0);

      white-space:nowrap;border:0;

    }



    .split{

      display:grid;

      grid-template-columns: 1fr 1fr;

      gap: 16px;

      margin-top: 18px;

    }

    @media (max-width: 980px){

      .split{ grid-template-columns: 1fr; }

    }

    .mini{

      display:flex;

      flex-wrap: wrap;

      gap: 10px;

      margin-top: 10px;

    }

    .kbd{

      display:inline-flex;

      align-items:center;

      gap:8px;

      padding: 6px 10px;

      border-radius: 999px;

      border: 1px solid rgba(255,255,255,.14);

      background: rgba(255,255,255,.04);

      color: rgba(255,255,255,.86);

      font-size: 13px;

      white-space: nowrap;

    }

    .kbd code{

      font-family: var(--mono);

      color: rgba(255,255,255,.90);

    }

    .hr{

      height: 1px;

      background: rgba(255,255,255,.10);

      margin: 14px 0;

      border: 0;

    }



    .callout{

      border: 1px solid rgba(124,58,237,.22);

      background:

        radial-gradient(800px 260px at 10% 0%, rgba(124,58,237,.18), transparent 60%),

        linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));

      border-radius: var(--radius-lg);

      padding: 14px 16px;

    }

    .callout-h{

      display:flex;

      align-items:flex-start;

      gap: 12px;

      margin-bottom: 6px;

    }

    .icon-badge{

      width: 34px;

      height: 34px;

      border-radius: 12px;

      border: 1px solid rgba(255,255,255,.14);

      background: linear-gradient(135deg, rgba(124,58,237,.22), rgba(34,211,238,.12));

      display:grid;

      place-items:center;

      flex: 0 0 auto;

      box-shadow: 0 12px 30px rgba(0,0,0,.25);

    }

    .callout p{

      margin: 0;

      color: rgba(255,255,255,.78);

      line-height: 1.7;

      font-size: 14.5px;

    }

    .prompt{

      border: 1px solid rgba(255,255,255,.12);

      background: rgba(255,255,255,.035);

      border-radius: var(--radius-lg);

      padding: 16px;

    }

    .prompt h3{

      margin: 0 0 6px 0;

      font-size: 14px;

      letter-spacing: .14em;

      text-transform: uppercase;

      color: rgba(255,255,255,.86);

    }

    .choices{

      margin: 10px 0 0 0;

      padding: 0;

      list-style: none;

      display:flex;

      flex-wrap: wrap;

      gap: 10px;

    }

    .choice{

      display:inline-flex;

      align-items:center;

      gap: 8px;

      padding: 8px 10px;

      border-radius: 999px;

      border: 1px solid rgba(255,255,255,.14);

      background: rgba(255,255,255,.04);

      color: rgba(255,255,255,.82);

      font-size: 13.5px;

      white-space: nowrap;

    }

    .choice i{

      width: 10px; height: 10px; border-radius: 999px; display:inline-block;

      background: linear-gradient(135deg, var(--accent), var(--accent-2));

      box-shadow: 0 0 0 4px rgba(34,211,238,.10);

      opacity: .95;

    }



    .transition-opacity { transition: opacity 300ms ease; }

    .duration-300 { transition-duration: 300ms; }

    .opacity-100 { opacity: 1; }

    .opacity-0 { opacity: 0; }

    .block { display: block; }

    .hidden { display: none !important; }



    @media (prefers-reduced-motion: reduce){

      .transition-opacity{ transition: none !important; }

      .btn{ transition: none !important; }

    }

 """
    present_lesson = PresentLesson()
    code = await present_lesson.presentation(lesson=lesson,style= style)
    Path("output.html").unlink(missing_ok = True)
    with open("output.html", "w", encoding="utf-8") as file:
        file.write(code)
    print(code)
    return code

def generate_lesson_page(lesson_data: dict, lesson_name: str, output_filename: str = "lesson.html"):
    """
    Generates an HTML lesson page from a dictionary of lesson parts.
    """
    parts = lesson_data.get('parts', [])
    
    # 1. Generate the dynamic article HTML blocks for each part
    article_blocks = ""
    for part in parts:
        part_id = part.get("id", "")
        article_blocks += f"""
                  <article id="{part_id}" class="lesson-section transition-opacity duration-300 opacity-0 hidden">
                    <div class="markdown-body" data-content-target="{part_id}"></div>
                  </article>"""
    
    # 2. Serialize the parts list into a JSON string
    json_content = json.dumps(parts, indent=2)
    
    # 3. Base HTML Template
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Lesson Module - {{LESSON_NAME}}</title>
  <script>
    (function(){
      var ok = true;
      try{
        if(!window.tailwind) ok = false;
      }catch(e){ ok = false; }
    })();
  </script>
  <style>
    :root{
      --bg: #0b1220;
      --panel: rgba(255,255,255,.06);
      --panel-2: rgba(255,255,255,.08);
      --stroke: rgba(255,255,255,.12);
      --text: rgba(255,255,255,.92);
      --muted: rgba(255,255,255,.72);
      --muted-2: rgba(255,255,255,.62);
      --accent: #7c3aed;
      --accent-2: #22d3ee;
      --shadow: 0 18px 50px rgba(0,0,0,.45);
      --radius-xl: 22px;
      --radius-lg: 16px;
      --radius-md: 12px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
    }

    * { box-sizing: border-box; }
    html, body { height: 100%; }

    body{
      margin:0;
      font-family: var(--sans);
      background:
        radial-gradient(1200px 800px at 30% -10%, rgba(124,58,237,.20), transparent 60%),
        radial-gradient(1000px 680px at 90% 10%, rgba(34,211,238,.14), transparent 55%),
        linear-gradient(180deg, #060913 0%, #050712 100%);
      color: var(--text);
    }

    main{
      min-height: 100vh;
      display:flex;
      align-items: stretch;
      justify-content: center;
      padding: 0;
    }

    section[id]{
      width: 100%;
    }

    .view-shell{
      color: var(--text);
      background:
        radial-gradient(1000px 600px at 10% 0%, rgba(124,58,237,.35), transparent 60%),
        radial-gradient(900px 520px at 90% 20%, rgba(34,211,238,.22), transparent 55%),
        linear-gradient(180deg, #0b1220 0%, #070b14 100%);
      border: none;
      border-radius: 0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    
    .view-inner{
      padding: clamp(18px, 3.5vw, 34px);
      flex-grow: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .topbar{
      display:flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap:16px;
      margin-bottom: 24px;
      width: 100%;
      max-width: 1000px;
    }

    .badge{
      display:inline-flex;
      align-items:center;
      gap:10px;
      padding: 8px 12px;
      border: 1px solid var(--stroke);
      background: rgba(255,255,255,.05);
      border-radius: 999px;
      color: var(--muted);
      font-size: 13px;
      letter-spacing:.2px;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
    }

    .dot{
      width:10px;height:10px;border-radius:999px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      box-shadow: 0 0 0 4px rgba(124,58,237,.16);
    }

    .title{
      margin: 16px 0 8px 0;
      font-size: clamp(24px, 3vw, 40px);
      line-height: 1.15;
      letter-spacing: -.02em;
    }

    .subtitle{
      margin: 0 auto;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.6;
      max-width: 78ch;
    }

    .grid{
      display: flex;
      width: 100%;
      justify-content: center;
      flex-grow: 1;
    }

    .card{
      width: 100%;
      max-width: 1000px;
      border: 1px solid var(--stroke);
      background: linear-gradient(180deg, rgba(255,255,255,.07), rgba(255,255,255,.04));
      border-radius: var(--radius-lg);
      overflow:hidden;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow);
    }

    .card-h{
      padding: 16px 20px;
      border-bottom: 1px solid rgba(255,255,255,.10);
      background: rgba(255,255,255,.04);
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap: 12px;
    }

    .card-h h2{
      margin:0;
      font-size: 14px;
      letter-spacing: .14em;
      text-transform: uppercase;
      color: rgba(255,255,255,.86);
    }

    .card-b{
      padding: 24px;
      flex-grow: 1;
      text-align: left;
    }

    .pill{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding: 6px 12px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,.14);
      background: rgba(255,255,255,.04);
      font-family: var(--mono);
      font-size: 13px;
      color: rgba(255,255,255,.88);
      white-space: nowrap;
    }

    .pill i{
      width:8px;height:8px;border-radius:999px; display:inline-block;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      opacity:.95;
    }

    .nav{
      display:flex;
      align-items:center;
      justify-content: center;
      gap: 16px;
      padding: 20px;
      border-top: 1px solid rgba(255,255,255,.10);
      background: rgba(255,255,255,.03);
    }

    .btn{
      display:inline-flex;
      align-items:center;
      justify-content:center;
      gap: 10px;
      padding: 12px 20px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,.14);
      background: rgba(255,255,255,.04);
      color: rgba(255,255,255,.90);
      text-decoration:none;
      font-size: 15px;
      font-weight: 500;
      line-height: 1;
      transition: transform .15s ease, background .15s ease, border-color .15s ease, box-shadow .15s ease;
      user-select:none;
      white-space: nowrap;
      cursor: pointer;
    }

    .btn:hover{
      background: rgba(255,255,255,.07);
      border-color: rgba(255,255,255,.18);
      transform: translateY(-1px);
      box-shadow: 0 10px 25px rgba(0,0,0,.25);
    }

    .btn:focus-visible{
      outline: 2px solid rgba(34,211,238,.55);
      outline-offset: 3px;
    }

    .btn svg{ opacity:.9; }

    .transition-opacity { transition: opacity 300ms ease; }
    .duration-300 { transition-duration: 300ms; }
    .opacity-100 { opacity: 1; }
    .opacity-0 { opacity: 0; }
    .hidden { display: none !important; }

    .markdown-body h1, .markdown-body h2, .markdown-body h3 {
      color: rgba(255,255,255,.96);
      line-height: 1.2;
      margin: 0 0 14px 0;
    }
    .markdown-body h2 { font-size: clamp(24px, 2.7vw, 36px); letter-spacing: -.02em; }
    .markdown-body h3 { font-size: 20px; margin-top: 24px; }
    .markdown-body p {
      color: var(--muted);
      line-height: 1.8;
      font-size: 16px;
      margin: 0 0 16px 0;
    }
    .markdown-body ul, .markdown-body ol {
      margin: 0 0 16px 0;
      padding-left: 24px;
      color: var(--muted);
      font-size: 16px;
    }
    .markdown-body li { margin: 8px 0; line-height: 1.75; }
    .markdown-body strong { color: rgba(255,255,255,.95); }
    .markdown-body code {
      font-family: var(--mono);
      background: rgba(255,255,255,.07);
      border: 1px solid rgba(255,255,255,.10);
      border-radius: 8px;
      padding: 2px 6px;
      color: rgba(255,255,255,.94);
      font-size: .95em;
    }
    .markdown-body hr {
      border: 0;
      height: 1px;
      background: rgba(255,255,255,.12);
      margin: 24px 0;
    }
    .markdown-body pre code{
      background: transparent;
      border: 0;
      padding: 0;
      color: rgba(255,255,255,.90);
      font-size: 14px;
    }
    .markdown-body pre{
      overflow:auto;
      padding: 16px;
      border-radius: var(--radius-lg);
      border: 1px solid rgba(255,255,255,.10);
      background: rgba(0,0,0,.25);
      color: rgba(255,255,255,.90);
      font-family: var(--mono);
      line-height: 1.65;
    }

    @media (prefers-reduced-motion: reduce){
      .transition-opacity{ transition: none !important; }
      .btn{ transition: none !important; }
    }
  </style>
</head>
<body>
  <textarea id="markdown-source" style="display:none;">
{{JSON_CONTENT}}
  </textarea>

  <main>
    <section id="lesson-app">
      <div class="view-shell">
        <div class="view-inner">
          <div class="topbar">
            <div class="badge">
              <span class="dot"></span>
              <span>Lesson Module</span>
            </div>
            <h1 class="title">{{LESSON_NAME}}</h1>
            <p class="subtitle">Navigate through the lesson pages to review each section in sequence.</p>
          </div>

          <div class="grid">
            <div class="card">
              <div class="card-h">
                <h2>Main Lesson Content</h2>
                <span class="pill"><i></i><span id="content-status">Visible section</span></span>
              </div>
              <div class="card-b">
                <div id="sections-wrapper">
{{ARTICLE_BLOCKS}}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="nav">
          <button type="button" class="btn" id="prevBtn" aria-label="Previous section">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M15 6L9 12L15 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>Previous</span>
          </button>
          <button type="button" class="btn btn-primary" id="nextBtn" aria-label="Next section">
            <span>Next</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M9 6L15 12L9 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </section>
  </main>

  <script>
    (function () {
      function escapeHtml(s){
        return String(s)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;');
      }

      function simpleMarkdownToHtml(md){
        var lines = String(md || '').replace(/\\r\\n/g, '\\n').split('\\n');
        var html = [];
        var inCodeFence = false;
        var codeLang = '';
        var codeBuf = [];

        function flushCode(){
          if(!codeBuf.length) return;
          var code = escapeHtml(codeBuf.join('\\n'));
          html.push('<pre><code' + (codeLang ? ' class="language-' + escapeHtml(codeLang) + '"' : '') + '>' + code + '</code></pre>');
          codeBuf = [];
          codeLang = '';
        }

        for(var i=0;i<lines.length;i++){
          var line = lines[i];

          var fenceMatch = line.match(/^\\s*```(\\w+)?\\s*$/);
          if(fenceMatch){
            if(!inCodeFence){
              inCodeFence = true;
              codeLang = fenceMatch[1] || '';
              codeBuf = [];
            } else {
              inCodeFence = false;
              flushCode();
            }
            continue;
          }

          if(inCodeFence){
            codeBuf.push(line);
            continue;
          }

          if(/^\\s*---\\s*$/.test(line)){
            html.push('<hr/>');
            continue;
          }

          var headingMatch = line.match(/^(#{1,6})\\s+(.*)$/);
          if(headingMatch){
            var level = headingMatch[1].length;
            var text = headingMatch[2].trim();
            html.push('<h' + level + '>' + renderInline(text) + '</h' + level + '>');
            continue;
          }

          var ulMatch = line.match(/^\\s*-\\s+(.*)$/);
          if(ulMatch){
            var items = [];
            while(i < lines.length && (m = lines[i].match(/^\\s*-\\s+(.*)$/))){
              items.push('<li>' + renderInline(m[1].trim()) + '</li>');
              i++;
            }
            i--;
            html.push('<ul>' + items.join('') + '</ul>');
            continue;
          }

          if(line.trim() === ''){
            continue;
          }

          html.push('<p>' + renderInline(line.trim()) + '</p>');
        }

        flushCode();
        return html.join('');

        function renderInline(text){
          var out = escapeHtml(text);
          out = out.replace(/`([^`]+)`/g, function(_, code){ return '<code>' + code + '</code>'; });
          out = out.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
          return out;
        }
      }

      var rawEl = document.getElementById('markdown-source');
      var raw = rawEl ? rawEl.value : '[]';

      var lessonParts;
      try{
        lessonParts = JSON.parse(raw);
      }catch(e){
        lessonParts = [];
      }
      if(!Array.isArray(lessonParts)) lessonParts = [];

      var hasMarked = typeof window.marked !== 'undefined' && window.marked && typeof window.marked.parse === 'function';
      if(hasMarked){
        try{
          window.marked.setOptions({ breaks: false, gfm: true });
        }catch(e){}
      }

      lessonParts.forEach(function (part) {
        var target = document.querySelector('[data-content-target="' + part.id + '"]');
        if (target) {
          var content = part.content || '';
          target.innerHTML = hasMarked ? window.marked.parse(content) : simpleMarkdownToHtml(content);
        }
      });

      var sections = lessonParts
        .map(function(part){ return document.getElementById(part.id); })
        .filter(Boolean);

      var currentIndex = 0;
      var contentStatus = document.getElementById('content-status');
      var prevBtn = document.getElementById('prevBtn');
      var nextBtn = document.getElementById('nextBtn');

      function updateMeta(index) {
        if(contentStatus) contentStatus.textContent = 'Section ' + (index + 1) + ' / ' + lessonParts.length;

        var atFirst = index === 0;
        var atLast = index === lessonParts.length - 1;

        if(prevBtn){
          prevBtn.disabled = atFirst;
          prevBtn.style.opacity = atFirst ? '.45' : '1';
          prevBtn.style.pointerEvents = atFirst ? 'none' : 'auto';
        }
        if(nextBtn){
          nextBtn.disabled = atLast;
          nextBtn.style.opacity = atLast ? '.45' : '1';
          nextBtn.style.pointerEvents = atLast ? 'none' : 'auto';
        }
      }

      function showSection(index) {
        if(!sections.length) return;
        sections.forEach(function (section, i) {
          if (i === index) {
            section.classList.remove('hidden');
            requestAnimationFrame(function () {
              section.classList.remove('opacity-0');
              section.classList.add('opacity-100');
            });
          } else {
            section.classList.add('opacity-0');
            section.classList.remove('opacity-100');
            section.classList.add('hidden');
          }
        });
        currentIndex = index;
        updateMeta(index);
      }

      function transitionTo(index) {
        if(!sections.length) return;
        if (index < 0 || index >= sections.length || index === currentIndex) return;

        var current = sections[currentIndex];
        if(!current) return;

        current.classList.add('opacity-0');
        current.classList.remove('opacity-100');

        window.setTimeout(function () {
          current.classList.add('hidden');
          var next = sections[index];
          if(!next) return;

          next.classList.remove('hidden');
          requestAnimationFrame(function () {
            next.classList.remove('opacity-0');
            next.classList.add('opacity-100');
          });

          currentIndex = index;
          updateMeta(index);
        }, 300);
      }

      if(prevBtn) prevBtn.addEventListener('click', function () { transitionTo(currentIndex - 1); });
      if(nextBtn) nextBtn.addEventListener('click', function () { transitionTo(currentIndex + 1); });

      document.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowLeft') transitionTo(currentIndex - 1);
        if (event.key === 'ArrowRight') transitionTo(currentIndex + 1);
      });

      if(sections.length) showSection(0);
      else updateMeta(0);
    })();
  </script>
</body>
</html>"""

    # 4. Inject the dynamically built components into the HTML template
    html_output = html_template.replace("{{LESSON_NAME}}", lesson_name)
    html_output = html_output.replace("{{JSON_CONTENT}}", json_content)
    html_output = html_output.replace("{{ARTICLE_BLOCKS}}", article_blocks.lstrip())

    # 5. Write out the completed HTML to a file
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_output)
        
    print(f"Lesson HTML generated successfully: {output_filename}")
        
    print(f"Lesson HTML generated successfully: {output_filename}")
def static_page():
  lesson_name = "Testing the lesson. " 
  lesson_parts = {'parts': [{'id': 'page_1', 'content': """Welcome to the world of programming! Python is often called a 'batteries-included' language because its powerful, yet the syntax is designed to read almost like English.\n\n In this first lesson, we're going to cover the absolute essentials: **Variables**, **Data Types**, and **Basic Logic**.\n\n---\n\n## 1. The 'Box' Metaphor: Variables\nThink of a **variable** as a labeled box. You put a value inside the box so you can remember it and use it later.\n\n```python\n# To create a variable, just give it a name and a value\nuser_name = 'Alex'\nuser_age = 25\n```\n\n### Key Rules for Names:\n* Use underscores `_` instead of spaces.\n* Start with a letter (not a number).\n* Case matters: `Age` and `age` are two different boxes!\n\n---\n\n## 2. Common Data Types\nPython is smart enough to know what's inside your 'box' based on how you write it.\n\n| Type | Name | Example | Description |\n| :--- | :--- | :--- | :--- |\n| **String** | `str` | `'Hello'` | Text wrapped in quotes. |\n| **Integer** | `int` | `42` | Whole numbers (no decimals). |\n| **Float** | `float` | `3.14` | Numbers with a decimal point. |\n| **Boolean**| `bool` | `True` | Logical values (True or False). |\n\n---\n', 'position': 'first'}, {'id': 'page_2', 'content': '## 3. Lists: The Organized Shelf\nSometimes one box isn\'t enough. A **List** lets you keep multiple items in a specific order.\n\n```python\n# Lists are defined with square brackets []\ncoding_languages = ['Python', 'JavaScript', 'C++']\n\n# You can access items by their position (starting at 0!)\nprint(coding_languages[0])  # This outputs: Python\n```\n\n---\n\n## 4. Making Decisions: If Statements\nLogic is what makes a program "smart." We use `if` statements to check a condition. **Indentation** (the space at the start of the line) is how Python knows which code belongs inside the "if" block.\n\n```python\ntemperature = 22\n\nif temperature > 30:\n    print("It\'s a hot day!")\nelif temperature > 15:\n    print("It\'s a nice day.")\nelse:\n    print("Brrr, it\'s cold!")\n```\n\n---\n', 'position': 'middle'}, {'id': 'page_3', 'content': '## 5. Your First "Mini-Project"\nCopy and paste this into a Python editor to see it in action. It combines everything we just learned:\n\n```python\n# 1. Input: Getting data from the user\nname = input("What is your name? ")\nfavorite_number = int(input("What is your favorite number? "))\n\n# 2. Logic: Checking the number\nif favorite_number == 7:\n    print(f"Hey {name}, 7 is a lucky number!")\nelse:\n    print(f"Cool name, {name}. {favorite_number} is a solid choice.")\n```\n\n---\n\n**Quick Tip:** Don\'t worry about memorizing everything. In programming, knowing **how to search** for a solution is just as important as knowing the code itself!\n\nWhat specific goal do you have for learning Python - are you looking to automate tasks, analyze data, or maybe build a website?""", 'position': 'last'}]}
  code = generate_lesson_page(lesson_data= lesson_parts, lesson_name=lesson_name)
  return code

if __name__ == '__main__': 
    code = static_page()
    print(code)

    #curriculum: {'sections': [{'name': name, 'test': test, 'lessons': [{'content': content, 'html file' : html_file} ... ]}]}


