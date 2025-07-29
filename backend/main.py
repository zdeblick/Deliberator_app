from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initial sample data structure (list of columns, each with list of panels)
data = [
    [  # Column 1
        {
            "argument": "Climate change is accelerating due to human activity.",
            "critiques": [
                ["This claim lacks a specific citation.", 0, 41]
            ],
        },
        {
            "argument": "Governments should invest in renewable energy to combat climate change.",
            "critiques": [],
        },
    ],
    [  # Column 2
        {
            "argument": "Some argue that economic growth should not be sacrificed for environmental policies.",
            "critiques": [],
        }
    ],
]

class CritiquePayload(BaseModel):
    text: str
    start: int
    end: int
    critique: str

@app.get("/arguments")
def get_arguments():
    return data

@app.post("/highlight")
def add_critique(payload: CritiquePayload):
    for column in data:
        for panel in column:
            arg = panel["argument"]
            # Check if highlighted text is a substring of argument at given indices
            if payload.text == arg[payload.start : payload.end]:
                # Just append, no duplicate check
                panel["critiques"].append([payload.critique, payload.start, payload.end])
                return {"status": "success"}
    return {"status": "error", "message": "Matching argument not found."}

