from typing import Literal
from openai import AsyncOpenAI 
from pydantic import BaseModel,Field
import asyncio
from dotenv import load_dotenv


#NOTE: יש דין אחד של SUBJECTS ויש דין של SECTIONS. 
class sections(BaseModel):
    """Represents the top-level sections of the course curriculum."""
    sections: list[str] = Field("The top layer of the course. 8 sections of main subjects, that will be used for learning the end goal.")

class Lessons(BaseModel):
    """Represents the list of lessons within a specific course section."""
    lessons: list[str] = Field("The lessons of the sections of the course. 4 lessons for the subject .")

class SectionType(BaseModel):
    """Represents the classification of a section as either practical or theoretical."""
    type: Literal['practical','theoretical']

class CourseDesigner:
    """Designer responsible for creating course structures, including subjects and lessons."""
    def __init__(self) -> None:
        """Initializes the CourseDesigner with model and client settings."""
        load_dotenv(override=True) 
        self.client = AsyncOpenAI()
        self.model = 'gpt-5'
    
    async def subjects_agent(self,prior_knowledge, main_goal):
        """Generates the high-level subjects/sections for the course based on goal and prior knowledge."""
        system_message = f"""You are a helpful course structure designer. The user will give you the end-goal, and your job is to design the TOP layer of the structure of the course.
        Your job is to output a 3-8 part list of the most important parts of the course.
        You will also be given the knowledge the student already has. You need to consider it when choosing the course parts. 
        You can choose subjects that are later to the subjects the student has learned. 
        From the other side, you cannot put subjects which the student already learned.
        If a subject's necessary preface is relatively small, you can choose it and the student will learn it. """
        
        response_format = {
            'format' :{'type': 'json_schema',
            'json_schema': {
                'name' : 'sections',
                'schema' : sections.model_json_schema(),
                'strict' : True

            }}
        }

        user_message = f"""Please design a course structure for this goal {main_goal}.
        Please note that I already know these subjects: {prior_knowledge}"""
        response = await self.client.responses.parse(
            model = self.model,
            input = [{'role':'system','content' : system_message },
            {'role':'user','content' : user_message }],
            text_format = sections
        )
        
        return response.output_parsed.sections

    async def lessons_agent(self,sections:list[str],prior_knowledge:str,main_goal:str): 
        """Generates specific lessons for each subject section in the curriculum."""
        #structure of curriculum: {main goal:main_goal, sections: [{name: section_1,lessons:[{name:..., content: ... (will be added using the content agent)}, lesson_2...], type: practical/theoretical}, {name: section_2,lessons:[lesson_1, lesson_2...]}]}
        curriculum = {'main goal' : main_goal,
        'sections' : []}
        system_message = f"""You are a lessons picker specialist. Your job is to pick relevant lessons for the currently learned subject.
        IMPORTANT: You need to pick 4-5 lessons. Also you need to choose only the NAME of the lesson. 
        You will be given a list of already learned knowledge and you mustn't pick a subject that was already learned.
        You will be given a main goal and you need to pick lessons that will help progress toward reaching the main goal while still staying on the subject. 
        Please note that each subject is actually a section in a course, and the lessons will be part of the subject. Also a big part of the already-learned subjects, are previous lessons from the course.""" 
        for section in sections:
            lessons_list = []
            user_message = f"""Please generate lessons' name for this subject: {section}. I have already learned these subjects or lessons: {prior_knowledge}. My main goal is :{main_goal}"""
            response = await self.client.responses.parse(
                model = self.model,
                input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
                text_format=Lessons
            )
            lessons = response.output_parsed.lessons
            type = await self.section_classifier(section,lessons)
            for lesson in lessons:
                lessons_list.append({'name':lesson})
            curriculum['sections'].append({'name' : section, 'lessons':lessons_list,'type': type })
        return curriculum 

    async def section_classifier(self, section:str, lessons:list[str]):
        """Classifies a section as either 'practical' or 'theoretical' based on its content."""
        system_message = """Role: You are a professional section type classifier. Your job is to determine whether a lesson section is "practical" or "theoretical" based on its name and content.
Requirements:
Choose 'theoretical' if the section's tasks or assessments involve proving knowledge, solving conceptual problems, or recalling facts.
If a task can be completed simply by answering a question or solving an equation on paper (such as in Mathematics or History), it is theoretical. 
Even if the learner is "solving" something, if the implementation is just to arrive at an answer, it belongs here.
Choose 'practical' ONLY if the core task CAN BE ONE THAT forces the learner to actively practice a tangible skill, and it is impossible to complete the task merely by answering a question. 
This requires creating, building, or operating something (e.g., programming a functioning application, designing a graphic, or physical craftsmanship). 
If the task cannot be done without actively practicing the real-world skill itself, it is practical.
"""
        user_message = f"Here is the section name: {section}. Lessons: {lessons}. Please classify the section."
        response = await self.client.responses.parse(
            model = self.model,
            input = [{'role':'system','content' : system_message },
                {'role':'user','content' : user_message }],
            text_format= SectionType
        )
        section_type = response.output_parsed.type
        return section_type

    async def curriculum_gen(self, prior_knowledge:str,main_goal:str):
        """Orchestrates the generation of a full course curriculum."""
        sections = await self.subjects_agent(prior_knowledge,main_goal)
        full_curriculum = await self.lessons_agent(sections,prior_knowledge,main_goal)
        return full_curriculum


async def main():
    """Main entry point for testing CourseDesigner with an LLM Engineering goal."""
    end_goal = 'Removing lignin, exposing cellulose'
    prior_knowledge = ['Basic Organic Chemistry', 'Carbohydrate Chemistry (Monosaccharides)','Stereochemistry of Sugars', 'Dehydration Synthesis & Hydrolysis', 'Glycosidic Linkages','Introduction to Polymer Science', 'Intermolecular Forces', 'Polymer Morphology', 'Thermodynamics of Packing', 'Plant Cell Wall Biology', 'Cellulose Structure', 'Hemicellulose','Lignin Chemistry', 'Biomass Recalcitrance','Lignocellulose']
    designer = CourseDesigner()
    sections = await designer.subjects_agent(prior_knowledge,end_goal)
    print(len(sections))
    full_course = await designer.lessons_agent(sections,prior_knowledge,end_goal)
    return full_course
if __name__ == '__main__':
    response = asyncio.run(main())
    print(response)