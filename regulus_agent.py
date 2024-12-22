import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import openai  # type: ignore
import os

app = FastAPI()
# Allow CORS for Angular frontend
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["http://localhost:4200"],  # Replace with your Angular frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY", "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")

# Define models for requests and responses
class Task(BaseModel):
    title: str
    description: str
    work_duration: int  # in hours
    complexity: int  # 1 = easy, 2 = medium, 3 = hard

class ProjectSpec(BaseModel):
    project_description: str

class Employee(BaseModel):
    name: str
    seniority: str  # "junior", "middle_level", "senior"
    work_duration: int  # hours per week
    expertise: str

class ScheduleRequest(BaseModel):
    tasks: List[Task]
    employees_csv: str  # File path to the CSV containing employee data

# Helper function to generate tasks using GPT-4
def generate_tasks_with_gpt(project_description):
    prompt = (
        "You are a project management assistant. Based on the following project description, generate a list of tasks. "
        "Each task should have a title, a description, work duration (in hours), and complexity (1=easy, 2=medium, 3=hard). "
        "Return the result as a valid JSON array of tasks."
        f"\n\n{project_description}"
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Correct model name
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response["choices"][0]["message"]["content"]

        # Log the raw response for debugging
        print("Raw response from OpenAI:", content)

        # Ensure response content is valid
        if not content.strip():
            raise ValueError("The API returned an empty response.")

        # Parse the response content into JSON
        tasks = json.loads(content)
        return tasks
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing JSON from OpenAI response. Response: {content}. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Helper function to assign tasks using GPT-4
def assign_tasks_with_gpt(tasks, employees):
    prompt = (
        "You are a scheduling assistant. Assign each task to the most suitable employee based on their expertise, seniority, and available work hours. "
        "Here is the list of tasks: \n" + json.dumps(tasks) + "\n\n"
        "Here is the list of employees: \n" + json.dumps(employees) + "\n\n"
        "Return the output strictly as a JSON array. Each element should contain: "
        "task title, task description, work duration, task complexity, and assigned employee's name. "
        "Do not include any explanations, comments, or extra text."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Correct model name
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response["choices"][0]["message"]["content"]

        # Log the raw response for debugging
        print("Raw response from OpenAI:", content)

        # Ensure response content is valid JSON
        if not content.strip():
            raise ValueError("The API returned an empty response.")

        assignments = json.loads(content)
        return assignments
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing JSON from OpenAI response. Response: {content}. Error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Endpoint to generate project tasks
@app.post("/generate-tasks/")
def generate_tasks(spec: ProjectSpec):
    try:
        tasks = generate_tasks_with_gpt(spec.project_description)
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tasks: {str(e)}")

# Endpoint to schedule tasks to employees
@app.post("/schedule-tasks/")
def schedule_tasks(schedule_request: ScheduleRequest):
    try:
        # Convert Pydantic Task objects to a list of dictionaries
        tasks_dict = [task.dict() for task in schedule_request.tasks]

        # Load employee data from CSV
        employees_df = pd.read_csv(schedule_request.employees_csv)
        employees = employees_df.to_dict(orient="records")

        # Assign tasks using GPT-4
        assignments = assign_tasks_with_gpt(tasks_dict, employees)
        return {"assigned_tasks": assignments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scheduling tasks: {str(e)}")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
