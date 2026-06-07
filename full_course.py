import asyncio
from typing import Any
from course_design import CourseDesigner
from content_agent import ContentAgent
from presentation import PresentLesson
from pathlib import Path
import re
import shutil
import json

INVALID_CHARS = r'[<>:"/\\|?*]'
def sanitize_name(name: str, max_len: int = 240) -> str:
    name = re.sub(INVALID_CHARS, '_', name)
    name = name.rstrip(' .')  # Windows disallows trailing space/dot
    return name[:max_len] if name else 'untitled'




def clean_html_padding_fast(html_string):
    """
    Removes plain text appearing before the first HTML tag 
    and after the last HTML tag with zero parsing overhead.
    """
    start_index = html_string.find('<')
    
    # If there's no opening tag, there's no HTML to extract
    if start_index == -1:
        return ""

    end_index = html_string.rfind('>')
    
    # Ensure the closing tag actually comes after the opening tag
    if end_index < start_index:
        return ""

    # Extract and return purely via fast string slicing
    return html_string[start_index:end_index + 1]

def create_html(lesson_parts:list,path:str, title:str):
    """
    Creates an HTML file for a lesson by injecting JSON data into a template.
    """
    json_string = json.dumps(lesson_parts, indent = 2) 
    with open("template1.html", "r", encoding="utf-8") as file:
      html_content = file.read()
    final_html = html_content.replace("%%JSON_DATA_HERE%%", json_string).replace("%%TITLE_HERE%%",title)
    with open(path,"w",encoding = "utf-8" ) as file: 
      file.write(final_html)
    return final_html



"""async def generate_course_with_pages(main_goal:str, prior_knowledge:list[str]):
  print("started to run")
  course_designer = CourseDesigner()
  curriculum = await course_designer.curriculum_gen(prior_knowledge=prior_knowledge, main_goal = main_goal)
  print("============================================")
  print("created course structure -- curriculum")
  print (len(curriculum['sections']))
  content_agent= ContentAgent()
  full_curriculum =await content_agent.content_agent(curriculum =  curriculum, prior_knowledge = prior_knowledge) 
  print(len(full_curriculum['sections']))
  print("============================================")
  print("Filled the course with content")
  present = PresentLesson()
  for section_idx, section in enumerate(full_curriculum['sections']):
    print(f"course length: {len(full_curriculum['sections'])}")
    shortened_name = f"{section_idx+1}_{section['name'][:15]}"
    sanitized_name = sanitize_name(shortened_name)
    folder_path = Path(sanitized_name)
    folder_path.mkdir(parents = True, exist_ok = True)
    for i, lesson in enumerate[Any](section['lessons']):
      print(f"section_length:{len(section['lessons'])}")
      html = await present.presentation(lesson = lesson['content'],style = style )
      cleaned_html = clean_html_padding_fast(html)
      file_name = f'lesson_{i+1}.html'
      file_path = folder_path/file_name
      file_path.write_text(cleaned_html, encoding='utf-8')
      lesson['path'] = file_path
  print("===================================================")
  print("added the html")
  return full_curriculum"""


async def course_with_pages(main_goal:str, prior_knowledge:list[str]): 
    """Generates the content with LLM, the html files are created with regular code."""
    print("started to run")
    course_designer = CourseDesigner()
    curriculum = await course_designer.curriculum_gen(prior_knowledge=prior_knowledge, main_goal = main_goal)
    print("============================================")
    print("created course structure -- curriculum")
    print (len(curriculum['sections']))
    content_agent= ContentAgent()
    full_curriculum =await content_agent.content_agent(curriculum =  curriculum, prior_knowledge = prior_knowledge) 
    print(len(full_curriculum['sections']))
    print("============================================")
    print("Filled the course with content")
    curriculum = await content_agent.content_agent(curriculum, prior_knowledge)
    print(curriculum)
    return curriculum


async def main():
    """Main execution function to generate a full course curriculum for Python Agentic AI Engineering."""
    main_goal = 'Removing Lignin'
    prior_knowledge = ['Basic Organic Chemistry', 'Carbohydrate Chemistry (Monosaccharides)','Stereochemistry of Sugars', 'Dehydration Synthesis & Hydrolysis', 'Glycosidic Linkages','Introduction to Polymer Science', 'Intermolecular Forces', 'Polymer Morphology', 'Thermodynamics of Packing', 'Plant Cell Wall Biology', 'Cellulose Structure', 'Hemicellulose','Lignin Chemistry', 'Biomass Recalcitrance','Lignocellulose']
    curriculum = await course_with_pages(main_goal = main_goal, prior_knowledge = prior_knowledge) 
    with open("curriculum.txt", "w", encoding="utf-8") as file:
          file.write(str(curriculum))
    print(curriculum)
  
if __name__ == '__main__':
  asyncio.run(main())
  #html_file()