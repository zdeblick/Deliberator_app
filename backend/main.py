from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample data structure
data = [
    [
        {
            "argument": "The Earth is warming due to human activity.",
            "critiques": [["This claim is supported by consensus.", 0, 15]]
        },
        {
            "argument": "Renewable energy sources are more sustainable long-term.",
            "critiques": []
        }
    ]
]

class CritiquePayload(BaseModel):
    argument_text: str
    critique: str
    start: int
    end: int

@app.get("/data")
def get_data():
    return data

@app.post("/submit")
def submit_critique(payload: CritiquePayload):
    for column in data:
        for panel in column:
            if panel["argument"] == payload.argument_text:
                panel["critiques"].append([payload.critique, payload.start, payload.end])
                return {"status": "success"}
    raise HTTPException(status_code=404, detail="Matching argument not found.")
