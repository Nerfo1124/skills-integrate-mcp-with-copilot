"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
import json
import secrets
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


class TeacherLoginRequest(BaseModel):
    username: str
    password: str


def load_teacher_credentials() -> dict[str, str]:
    teachers_file = current_dir / "teachers.json"
    try:
        with open(teachers_file, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Startup configuration error: required teacher credentials file "
            f"'{teachers_file}' was not found."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Startup configuration error: teacher credentials file "
            f"'{teachers_file}' contains invalid JSON: {exc}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Startup configuration error: could not read teacher credentials "
            f"file '{teachers_file}': {exc}"
        ) from exc

    teachers: dict[str, str] = {}
    for teacher in payload.get("teachers", []):
        username = teacher.get("username")
        password = teacher.get("password")
        if username and password:
            teachers[username] = password
    return teachers


teacher_credentials = load_teacher_credentials()
active_teacher_tokens: dict[str, str] = {}


def require_teacher(
    x_teacher_token: str | None = Header(default=None, alias="X-Teacher-Token")
) -> str:
    if not x_teacher_token or x_teacher_token not in active_teacher_tokens:
        raise HTTPException(
            status_code=401,
            detail="Teacher authentication is required for this action"
        )
    return active_teacher_tokens[x_teacher_token]

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/login")
def teacher_login(credentials: TeacherLoginRequest):
    stored_password = teacher_credentials.get(credentials.username)
    if not stored_password or stored_password != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    token = secrets.token_urlsafe(24)
    active_teacher_tokens[token] = credentials.username
    return {
        "message": "Teacher logged in successfully",
        "token": token,
        "username": credentials.username
    }


@app.post("/auth/logout")
def teacher_logout(x_teacher_token: str | None = Header(default=None, alias="X-Teacher-Token")):
    if not x_teacher_token or x_teacher_token not in active_teacher_tokens:
        raise HTTPException(status_code=401, detail="Invalid teacher session")

    del active_teacher_tokens[x_teacher_token]
    return {"message": "Teacher logged out successfully"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher)
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher)
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
