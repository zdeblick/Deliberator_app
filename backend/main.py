from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Allow frontend access (update if needed for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Example data structure
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
        }
    ],
    [  # Column 2
        {
            "argument": "Some argue that economic growth should not be sacrificed for environmental policies.",
            "critiques": [],
        }
    ]
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
            # Check if the selected text matches part of the argument
            if payload.text == arg[payload.start:payload.end]:
                # Avoid duplicates
                for existing in panel["critiques"]:
                    if existing[1] == payload.start and existing[2] == payload.end and existing[0] == payload.critique:
                        return {"message": "Duplicate critique ignored."}
                panel["critiques"].append([payload.critique, payload.start, payload.end])
                return {"message": "Critique added."}
    return {"error": "Matching argument not found."}
