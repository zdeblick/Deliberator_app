from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple
import uvicorn

app = FastAPI()

# Enable CORS for GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data structure: List[List[Dict]]
# Each dict: {'argument': str, 'critiques': List[List[str, int, int]]}
data = [
    [  # Column 1
        {
            'argument': 'Climate change is primarily caused by human activities such as burning fossil fuels, deforestation, and industrial processes. The scientific consensus is overwhelming.',
            'critiques': [
                ['The scientific consensus claim needs more specific evidence', 85, 120],
                ['What about natural climate variations?', 0, 27]
            ]
        },
        {
            'argument': 'Renewable energy sources like solar and wind are becoming increasingly cost-effective and reliable alternatives to fossil fuels.',
            'critiques': [
                ['Reliability issues during peak demand periods', 77, 85],
                ['Storage costs not included in analysis', 50, 77]
            ]
        }
    ],
    [  # Column 2
        {
            'argument': 'Universal healthcare systems provide better outcomes at lower costs compared to privatized systems, as evidenced by countries like Canada and the UK.',
            'critiques': [
                ['Wait times can be problematic', 91, 130],
                ['Different countries have different contexts', 132, 162]
            ]
        }
    ],
    [  # Column 3
        {
            'argument': 'Artificial intelligence will revolutionize education by providing personalized learning experiences tailored to individual student needs.',
            'critiques': [
                ['Risk of reducing human interaction', 74, 101],
                ['Privacy concerns with student data', 102, 141]
            ]
        }
    ]
]

class NewArgument(BaseModel):
    column_index: int
    argument: str

class NewCritique(BaseModel):
    column_index: int
    panel_index: int
    critique_text: str
    start_ind: int
    end_ind: int

@app.get("/data")
async def get_data():
    """Return the full data structure"""
    return data

@app.post("/argument")
async def add_argument(new_arg: NewArgument):
    """Add a new argument to specified column"""
    if new_arg.column_index < 0 or new_arg.column_index >= len(data):
        raise HTTPException(status_code=400, detail="Invalid column index")
    
    new_panel = {
        'argument': new_arg.argument,
        'critiques': []
    }
    
    data[new_arg.column_index].append(new_panel)
    return {"message": "Argument added successfully"}

@app.post("/critique")
async def add_critique(new_crit: NewCritique):
    """Add a new critique to specified argument"""
    if new_crit.column_index < 0 or new_crit.column_index >= len(data):
        raise HTTPException(status_code=400, detail="Invalid column index")
    
    column = data[new_crit.column_index]
    if new_crit.panel_index < 0 or new_crit.panel_index >= len(column):
        raise HTTPException(status_code=400, detail="Invalid panel index")
    
    panel = column[new_crit.panel_index]
    
    # Validate indices
    if new_crit.start_ind < 0 or new_crit.end_ind > len(panel['argument']) or new_crit.start_ind >= new_crit.end_ind:
        raise HTTPException(status_code=400, detail="Invalid text indices")
    
    critique = [new_crit.critique_text, new_crit.start_ind, new_crit.end_ind]
    panel['critiques'].append(critique)
    
    return {"message": "Critique added successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
