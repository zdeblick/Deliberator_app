
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/hello")
def read_root():
    return {"message": "Hello from FastAPI backend!"}

@app.post("/highlight")
def receive_highlight(hl: Highlight):
    print(f"Received highlight: '{hl.text}' from {hl.start} to {hl.end}")
    return {"status": "success", "received": hl.dict()}
