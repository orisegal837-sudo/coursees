import json
import os
import random
from pydantic import BaseModel,Field


class Lesson(BaseModel):
    subtitle: str = Field("subtitle for the lesson. Bried description of what will be learned")
    page_1: str = Field(description="First part of the lesson.")
    page_2: str = Field(description="Second part of the lesson.")
    page_3: str = Field(description="Third part of the lesson.")
    page_4: str = Field(default=None, description="Optional fourth part of the lesson: summary.") 
    is_practical : bool 

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

class Answer(BaseModel):
    """Represents a single answer option for a test question."""
    answer: str
    is_correct: bool = Field(description="Defines whether the option is the answer to the question.")

class Question(BaseModel):
    """Represents a multiple-choice question with a list of options."""
    question: str = Field(description="The question text.")
    answers: list[Answer] = Field(description="The options of answers for the questions. ONE is correct.")
    note: str | None = Field(default=None, description="A note or explanation to be shown after an answer is selected.")

class Test(BaseModel):
    """Represents a full test consisting of a list of questions."""
    questions: list[Question] = Field(description="A list of questions for the test.")

def generate_task_markdown(task: PracticalTask) -> str:
    """
    Generates a Markdown/HTML string for the Structured Cards layout.
    """
    instructions_html = "".join([f"<li>{instr}</li>" for instr in task.instructions])
    criteria_html = "".join([f"<li>{crit}</li>" for crit in task.criteria])
    
    givens_html = ""
    if task.givens:
        givens_html = f"""
    <div class="task-card givens-card">
        <h3>📋 Provided Materials</h3>
        <p>{task.givens}</p>
    </div>
"""

    markdown = f"""
<div class="task-container">
    <div class="task-card objective-card">
        <h3>🎯 Learning Objective</h3>
        <p>{task.learning_objective}</p>
    </div>
    {givens_html}
    <div class="task-card instructions-card">
        <h3>🛠️ Instructions</h3>
        <ol class="instructions-list">
            {instructions_html}
        </ol>
    </div>

    <div class="task-card criteria-card">
        <h3>✅ Success Criteria</h3>
        <ul class="criteria-checklist">
            {criteria_html}
        </ul>
    </div>
</div>
"""
    return markdown

def create_task_html(task: PracticalTask, path: str):
    """
    Creates an HTML file for a task by injecting JSON data into template1.html.
    
    Args:
        task (PracticalTask): The task object containing title, objective, instructions, and criteria.
        path (str): The file path where the HTML will be saved.
    """
    content = generate_task_markdown(task)
    # We wrap it in a list as the template expects an array of sections
    lesson_parts = [{"id": "task_main", "content": content}]
    
    json_string = json.dumps(lesson_parts, indent=2)
    
    # Check if template1.html exists, otherwise fallback to template.html
    template_file = "template1.html" if os.path.exists("template1.html") else "template.html"
    
    with open(template_file, "r", encoding="utf-8") as file:
        html_content = file.read()
    
    # Inject JSON and metadata into the template placeholders
    final_html = (html_content
                  .replace("%%JSON_DATA_HERE%%", json_string)
                  .replace("%%BADGE_HERE%%", "Practical Task")
                  .replace("%%TITLE_HERE%%", "Practical Task")
                  .replace("%%SUBTITLE_HERE%%", "Apply your knowledge through this hands-on assignment."))
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    
    with open(path, "w", encoding="utf-8") as file:
        file.write(final_html)
    
    return final_html


def create_lesson_html(lesson: Lesson, path:str,lesson_name:str): 
    """
    Creates an HTML file for a lesson injecting JSON data into template1.html.
    
    Args:
        lesson (Lesson): The lesson object containing multiple pages.
        path (str): The file path where the HTML will be saved.
    """
    lesson_parts = [
        {"id": "lesson_page_1", 'content': lesson.page_1},
        {"id": "lesson_page_2", 'content': lesson.page_2},
        {"id": "lesson_page_3", 'content': lesson.page_3},
        {"id": "lesson_page_4", 'content': lesson.page_4}
    ]
    json_string = json.dumps(lesson_parts, indent=2)
    template_file = "template1.html" if os.path.exists("template1.html") else "template.html"
    subtitle = lesson.subtitle
    with open(template_file, "r", encoding="utf-8") as file:
        html_content = file.read()
        final_html = (html_content
                  .replace("%%JSON_DATA_HERE%%", json_string)
                  .replace("%%BADGE_HERE%%", "lesson")
                  .replace("%%TITLE_HERE%%", lesson_name)
                  .replace("%%SUBTITLE_HERE%%", subtitle))
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    
    with open(path, "w", encoding="utf-8") as file:
        file.write(final_html)
    
    return final_html
def create_guide_html(guide: PracticalGuide, path: str):
    """
    Creates an HTML file for a practical guide by injecting JSON data into template1.html.
    
    Args:
        guide (PracticalGuide): The guide object containing multiple pages.
        path (str): The file path where the HTML will be saved.
    """
    # Map the pages to the lesson_parts format
    lesson_parts = [
        {"id": "guide_page_1", "content": guide.page_1},
        {"id": "guide_page_2", "content": guide.page_2},
        {"id": "guide_page_3", "content": guide.page_3},
    ]
    
    if guide.page_4:
        lesson_parts.append({"id": "guide_page_4", "content": guide.page_4})
    
    json_string = json.dumps(lesson_parts, indent=2)
    
    # Check if template1.html exists, otherwise fallback to template.html
    template_file = "template1.html" if os.path.exists("template1.html") else "template.html"
    
    with open(template_file, "r", encoding="utf-8") as file:
        html_content = file.read()
    
    # Inject JSON and metadata into the template placeholders
    final_html = (html_content
                  .replace("%%JSON_DATA_HERE%%", json_string)
                  .replace("%%BADGE_HERE%%", "Practical Guide")
                  .replace("%%TITLE_HERE%%", "Practical Guide")
                  .replace("%%SUBTITLE_HERE%%", "A step-by-step walkthrough of the implementation."))
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    
    with open(path, "w", encoding="utf-8") as file:
        file.write(final_html)
    
    return final_html

def generate_test_markdown(test: Test) -> tuple[str, str]:
    """
    Generates (HTML content, Script/Style) for the Test layout with dynamic scoring.
    """
    questions_html = []
    for i, q in enumerate(test.questions):
        # Create a copy of the answers list and shuffle it
        shuffled_answers = list(q.answers)
        random.shuffle(shuffled_answers)
        
        answers_html = []
        for a in shuffled_answers:
            is_correct_str = "true" if a.is_correct else "false"
            correct_class = "correct-answer" if a.is_correct else ""
            # Using data attributes instead of onclick for better reliability with markdown rendering
            answers_html.append(f"""
                <li class="answer-option {correct_class}" data-is-correct="{is_correct_str}">
                    {a.answer}
                </li>
            """)
        
        note_html = ""
        if q.note:
            note_html = f'<div class="test-note" style="display:none;"><strong>Note:</strong> {q.note}</div>'
            
        questions_html.append(f"""
            <div class="test-question" id="question-{i}" style="margin-bottom: 48px; padding-bottom: 24px; border-bottom: 1px solid var(--stroke-soft);">
                <h3 style="color: var(--text-heading);">{i+1}. {q.question}</h3>
                <ul class="test-answers" style="list-style: none; padding-left: 0;">
                    {"".join(answers_html)}
                </ul>
                {note_html}
            </div>
        """)
    
    # Static summary block (initially hidden)
    summary_block = f"""
        <div id="dynamic-summary" class="test-summary" style="display: none; margin-top: 40px; padding: 32px; background: rgba(139, 92, 246, 0.08); border: 2px solid var(--accent-primary); border-radius: var(--radius-xl); animation: testFadeIn 0.6s ease-out;">
            <h2 style="margin-top: 0; color: var(--accent-primary); text-align: center; font-size: 2em;">📊 Test Results</h2>
            <div style="display: flex; justify-content: space-around; margin: 24px 0; text-align: center;">
                <div>
                    <div id="score-text" style="font-size: 3em; font-weight: 700; color: var(--text-heading);">0/0</div>
                    <div style="color: var(--text-muted); text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.1em;">Final Score</div>
                </div>
                <div>
                    <div id="percentage-text" style="font-size: 3em; font-weight: 700; color: var(--accent-secondary);">0%</div>
                    <div style="color: var(--text-muted); text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.1em;">Accuracy</div>
                </div>
            </div>
            <div id="performance-msg" style="text-align: center; font-style: italic; margin-bottom: 24px; color: var(--text-main);"></div>
            
        </div>
    """

    script_and_style = f"""
<script>
(function() {{
    const totalQuestions = {len(test.questions)};
    let answeredCount = 0;
    let correctCount = 0;

    function initTest() {{
        console.log("Initializing test interactivity...");
        // Use event delegation on the document body to catch clicks even if elements are re-into the DOM
        document.body.addEventListener('click', function(e) {{
            const element = e.target.closest('.answer-option');
            if (!element) return;

            const questionDiv = element.closest('.test-question');
            if (!questionDiv || questionDiv.classList.contains('answered')) return;

            questionDiv.classList.add('answered');
            const isCorrect = element.getAttribute('data-is-correct') === 'true';
            
            answeredCount++;
            if (isCorrect) correctCount++;
            
            const noteDiv = questionDiv.querySelector('.test-note');
            if (noteDiv) noteDiv.style.display = 'block';
            
            const options = questionDiv.querySelectorAll('.answer-option');
            options.forEach(opt => {{
                opt.style.pointerEvents = 'none';
                if (opt.classList.contains('correct-answer')) {{
                    opt.classList.add('correct-selection');
                }}
            }});
            
            if (!isCorrect) {{
                element.classList.add('wrong-selection');
            }}
            
            if (answeredCount === totalQuestions) {{
                showSummary();
            }}
        }});
    }}

    function showSummary() {{
        const summaryDiv = document.getElementById('dynamic-summary');
        const scoreText = document.getElementById('score-text');
        const percentText = document.getElementById('percentage-text');
        const msgText = document.getElementById('performance-msg');
        
        if (!summaryDiv) return;

        const percentage = Math.round((correctCount / totalQuestions) * 100);
        if (scoreText) scoreText.textContent = correctCount + '/' + totalQuestions;
        if (percentText) percentText.textContent = percentage + '%';
        
        if (msgText) {{
            if (percentage === 100) msgText.textContent = "Perfect! You have a complete grasp of this section.";
            else if (percentage >= 70) msgText.textContent = "Great job! You've mastered most of the concepts.";
            else if (percentage >= 40) msgText.textContent = "Good effort. Review the notes for the questions you missed.";
            else msgText.textContent = "Keep practicing. Re-reading the lessons might help clarify these topics.";
        }}
        
        summaryDiv.style.display = 'block';
        setTimeout(() => {{
            summaryDiv.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        }}, 100);
    }}

    // Wait for the template's renderer to populate the DOM
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', () => setTimeout(initTest, 800));
    }} else {{
        setTimeout(initTest, 800);
    }}
}})();
</script>
<style>
.answer-option {{ 
    cursor: pointer; 
    padding: 14px 20px; 
    margin: 10px 0; 
    border: 1px solid var(--stroke-soft); 
    border-radius: var(--radius-md); 
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    background: rgba(255, 255, 255, 0.02) !important;
    position: relative;
    list-style: none;
}}
.answer-option:hover {{ 
    background: var(--bg-surface-hover) !important; 
    border-color: var(--stroke-strong) !important; 
    transform: translateX(6px);
}}
.correct-selection {{ 
    background-color: rgba(16, 185, 129, 0.1) !important; 
    border-color: #10b981 !important; 
    color: #10b981 !important;
    font-weight: 600;
}}
.correct-selection::after {{
    content: "✓";
    position: absolute;
    right: 20px;
}}
.wrong-selection {{ 
    background-color: rgba(239, 68, 68, 0.1) !important; 
    border-color: #ef4444 !important; 
    color: #ef4444 !important;
}}
.wrong-selection::after {{
    content: "✕";
    position: absolute;
    right: 20px;
}}
.test-note {{ 
    margin-top: 16px; 
    padding: 16px 20px; 
    background: rgba(255, 255, 255, 0.03); 
    border-left: 4px solid var(--accent-primary); 
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    animation: testFadeIn 0.4s ease-out;
    font-size: 0.95em;
    color: var(--text-muted);
    line-height: 1.6;
}}
@keyframes testFadeIn {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
</style>
"""
    return f'<div class="test-container">{"".join(questions_html)}{summary_block}</div>', script_and_style

def create_test_html(test: Test, path: str):
    """
    Creates an HTML file for a test by injecting JSON data into template1.html.
    
    Args:
        test (Test): The test object containing questions, answers, notes, and summary.
        path (str): The file path where the HTML will be saved.
    """
    content, script_and_style = generate_test_markdown(test)
    # We wrap it in a list as the template expects an array of sections
    lesson_parts = [{"id": "test_main", "content": content}]
    
    json_string = json.dumps(lesson_parts, indent=2)
    
    # Check if template1.html exists, otherwise fallback to template.html
    template_file = "template1.html" if os.path.exists("template1.html") else "template.html"
    
    with open(template_file, "r", encoding="utf-8") as file:
        html_content = file.read()
    
    # Inject JSON and metadata into the template placeholders
    final_html = (html_content
                  .replace("%%JSON_DATA_HERE%%", json_string)
                  .replace("%%BADGE_HERE%%", "Knowledge Check")
                  .replace("%%TITLE_HERE%%", "Section Test")
                  .replace("%%SUBTITLE_HERE%%", "Test your understanding of the concepts covered in this section."))
    
    # Inject script and style directly into body to ensure execution
    final_html = final_html.replace("</body>", f"{script_and_style}\n</body>")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    
    with open(path, "w", encoding="utf-8") as file:
        file.write(final_html)
    
    return final_html

def test_render():
    """
    Quick test function to verify task, guide, and test rendering.
    Run with: python -c "from tasks import test_render; test_render()"
    """
    # Sample Task
    sample_task = PracticalTask(
        title="Your First Time Machine: Initializing a Git Repo",
        learning_objective="Students will learn how to initialize a local repository and track their first file changes using Git.",
        givens="A simple text file named 'hello.txt', terminal with Git installed, and a new folder named 'my-first-repo'.",
        instructions=[
            "Create a new folder on your desktop named 'my-first-repo'.",
            "Open your terminal or command prompt and navigate into that folder using 'cd'.",
            "Run the command 'git init' to transform the folder into a Git repository.",
            "Create a new text file named 'hello.txt' and write your name inside it.",
            "Use 'git add hello.txt' to stage the file.",
            "Commit your changes by typing 'git commit -m \"Initial commit: Added hello.txt\"'."
        ],
        criteria=[
            "The directory contains a hidden '.git' folder indicating successful initialization.",
            "The 'git log' command shows one commit with the correct message.",
            "The 'git status' command reports a clean working tree with no untracked files."
        ])    

    output_task = "sample_task_output.html"
    create_task_html(sample_task, output_task)
    print(f"Sample task generated successfully: {os.path.abspath(output_task)}")

    # Sample Guide
    sample_guide = PracticalGuide(
        page_1="**The Objective and Prerequisites**\n\nObjective: Build a basic Python script...",
        page_2="**Initial Steps...**",
        page_3="**Further Steps...**",
        page_4="**Final Steps...**"
    )
    output_guide = "sample_guide_output.html"
    create_guide_html(sample_guide, output_guide)
    print(f"Sample guide generated successfully: {os.path.abspath(output_guide)}")

    # Sample Test
    sample_test = Test(
        questions=[
            Question(
                question="What is the primary purpose of 'git init'?",
                answers=[
                    Answer(answer="To delete a repository", is_correct=False),
                    Answer(answer="To initialize a new Git repository in a directory", is_correct=True),
                    Answer(answer="To push changes to GitHub", is_correct=False),
                    Answer(answer="To install Git on your computer", is_correct=False)
                ],
                note="git init creates a hidden .git directory and starts tracking the folder."
            ),
            Question(
                question="Which command is used to stage a file named 'app.py'?",
                answers=[
                    Answer(answer="git commit app.py", is_correct=False),
                    Answer(answer="git push app.py", is_correct=False),
                    Answer(answer="git add app.py", is_correct=True),
                    Answer(answer="git stage-all", is_correct=False)
                ],
                note="git add adds the file to the staging area, preparing it for a commit."
            )
        ],
    )
    output_test = "sample_test_output.html"
    create_test_html(sample_test, output_test)
    print(f"Sample test generated successfully: {os.path.abspath(output_test)}")

if __name__ == "__main__":
    test_render()
