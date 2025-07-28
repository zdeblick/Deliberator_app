from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/hello")
def hello():
    return {"message": "Hello from FastAPI backend!"}

# Define highlight model
class Highlight(BaseModel):
    text: str
    start: int
    end: int

@app.post("/highlight")
def receive_highlight(hl: Highlight):
    print(f"Received highlight: '{hl.text}' from {hl.start} to {hl.end}")
    return {"status": "success", "received": hl.dict()}
