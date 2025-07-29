from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple

app = FastAPI()

# Allow CORS from your frontend domain (or '*')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for security in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model for highlights
class Highlight(BaseModel):
    text: str
    start: int
    end: int

# Example structured data - replace with your real data or DB
ARGUMENTS_DATA = [
    [
        {
            "argument": "Climate change is a critical issue that requires urgent action.",
            "critiques": [
                ["This is an overstatement.", 0, 14],  # highlights first 14 chars
                ["Urgent action is politically difficult.", 31, 55]
            ],
        },
        {
            "argument": "Renewable energy sources are becoming more affordable.",
            "critiques": []
        }
    ],
    [
        {
            "argument": "Investing in green tech creates jobs.",
            "critiques": [
                ["Depends on the sector.", 11, 25]
            ],
        }
    ]
]

# In-memory highlight storage
HIGHLIGHTS: List[Highlight] = []

@app.get("/arguments")
def get_arguments():
    return ARGUMENTS_DATA

@app.post("/highlight")
def receive_highlight(hl: Highlight):
    # For now, just store it in memory and print
    HIGHLIGHTS.append(hl)
    print(f"Received highlight: '{hl.text}' at {hl.start}-{hl.end}")
    return {"status": "success", "received": hl.dict()}

@app.get("/")
def root():
    return {"message": "FastAPI backend is running."}
