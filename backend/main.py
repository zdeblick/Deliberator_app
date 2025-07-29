from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data structure
data = [
    [  # Column 0
        {"argument": "Cats are independent animals.", "critiques": []},
        {"argument": "Dogs require more attention but are loyal.", "critiques": []},
    ],
    [  # Column 1
        {"argument": "Fish are low-maintenance pets.", "critiques": []},
    ]
]

@app.get("/data")
def get_data():
    return data

class HighlightInput(BaseModel):
    text: str
    start: int
    end: int
    critique: str

@app.post("/highlight")
def add_critique(h: HighlightInput):
    for column in data:
        for panel in column:
            arg = panel["argument"]
            if h.text in arg:
                start_idx = arg.find(h.text)
                if start_idx <= h.start and (start_idx + len(h.text)) >= h.end:
                    panel["critiques"].append([h.critique, h.start, h.end])
                    return {"status": "success", "panel": arg, "critique": h.critique}
    return {"status": "error", "message": "Highlight not within a single argument."}
