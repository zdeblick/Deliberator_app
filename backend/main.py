from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Dict, Optional
import uvicorn
import numpy as np

app = FastAPI()

# Enable CORS for GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your GitHub Pages URL
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# New data structures
# panels: Dict[panel_id, panel_data]
panels = {
    0: {
        'argument': 'Climate change is primarily caused by human activities such as burning fossil fuels, deforestation, and industrial processes. The scientific consensus is overwhelming.',
        'author': 'Dr. Climate',
        'critiques': [
            {'text': 'The scientific consensus claim needs more specific evidence', 'start_ind': 85, 'end_ind': 120, 'author': 'Skeptic1'},
            {'text': 'What about natural climate variations?', 'start_ind': 0, 'end_ind': 27, 'author': 'NaturalCycles'}
        ]
    },
    1: {
        'argument': 'Renewable energy sources like solar and wind are becoming increasingly cost-effective and reliable alternatives to fossil fuels.',
        'author': 'GreenTech',
        'critiques': [
            {'text': 'Reliability issues during peak demand periods', 'start_ind': 77, 'end_ind': 85, 'author': 'GridExpert'},
            {'text': 'Storage costs not included in analysis', 'start_ind': 50, 'end_ind': 77, 'author': 'EconomyWatch'}
        ]
    },
    2: {
        'argument': 'Universal healthcare systems provide better outcomes at lower costs compared to privatized systems, as evidenced by countries like Canada and the UK.',
        'author': 'HealthPolicy',
        'critiques': [
            {'text': 'Wait times can be problematic', 'start_ind': 91, 'end_ind': 130, 'author': 'PatientAdvocate'},
            {'text': 'Different countries have different contexts', 'start_ind': 132, 'end_ind': 162, 'author': 'ComparativeStudy'}
        ]
    },
    3: {
        'argument': 'Artificial intelligence will revolutionize education by providing personalized learning experiences tailored to individual student needs.',
        'author': 'EdTechFuture',
        'critiques': [
            {'text': 'Risk of reducing human interaction', 'start_ind': 74, 'end_ind': 101, 'author': 'HumanTouch'},
            {'text': 'Privacy concerns with student data', 'start_ind': 102, 'end_ind': 141, 'author': 'PrivacyWatch'}
        ]
    }
}

# layout: Dict[panel_id, (column_index, position_in_column)]
layout = {
    0: (0, 0),  # Column 1, position 1
    1: (0, 1),  # Column 1, position 2
    2: (1, 0),  # Column 2, position 1
    3: (2, 0)   # Column 3, position 1
}

# Users storage
users = {'system': {'password': None}}  # system user for default data

# Ratings storage: user -> statement_id -> (quality_rating, agreement_rating)
# statement_id format: "panel_X" for arguments, "panel_X_critique_Y" for critiques
ratings = {}

# Counter for new panel IDs
next_panel_id = 4

def convert_to_frontend_format():
    """Convert panels and layout to the frontend format"""
    # Find max column index
    max_col = max(col for col, pos in layout.values()) if layout else 0
    
    # Initialize columns
    columns = [[] for _ in range(max_col + 1)]
    
    # Group panels by column and sort by position
    for panel_id, (col_idx, position) in layout.items():
        if panel_id in panels:
            panel_data = panels[panel_id].copy()
            # Convert critiques to the old format for frontend compatibility but keep author
            old_format_critiques = []
            for critique in panel_data['critiques']:
                old_format_critiques.append([
                    critique['text'], 
                    critique['start_ind'], 
                    critique['end_ind'],
                    critique['author']  # Include author in the format
                ])
            panel_data['critiques'] = old_format_critiques
            
            # Add panel_id for reference
            panel_data['panel_id'] = panel_id
            
            columns[col_idx].append((position, panel_data))
    
    # Sort each column by position and remove position info
    for col in columns:
        col.sort(key=lambda x: x[0])
        col[:] = [panel for pos, panel in col]
    
    return columns

class UserLogin(BaseModel):
    username: str
    password: Optional[str] = None
    create_account: bool = False

class NewArgument(BaseModel):
    column_index: int
    argument: str
    author: str

class NewCritique(BaseModel):
    panel_id: int
    critique_text: str
    start_ind: int
    end_ind: int
    author: str

class NewRating(BaseModel):
    statement_id: str  # "panel_X" or "panel_X_critique_Y"
    quality_rating: int  # 1-7
    agreement_rating: int  # 1-7
    author: str

@app.post("/login")
async def login_user(user_data: UserLogin):
    """Handle user login or account creation"""
    username = user_data.username.strip()
    
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    
    if user_data.create_account:
        if username in users:
            raise HTTPException(status_code=400, detail="Username already exists")
        users[username] = {'password': user_data.password}
        return {"message": "Account created successfully", "username": username}
    else:
        if username not in users:
            raise HTTPException(status_code=400, detail="Username does not exist")
        if users[username]['password'] != user_data.password:
            raise HTTPException(status_code=400, detail="Incorrect password")
        return {"message": "Login successful", "username": username}

@app.get("/data")
async def get_data():
    """Return the data in frontend format"""
    return convert_to_frontend_format()

@app.post("/argument")
async def add_argument(new_arg: NewArgument):
    """Add a new argument to specified column"""
    global next_panel_id
    
    # Validate author is provided
    if not new_arg.author or not new_arg.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    # Create new panel
    panel_id = next_panel_id
    next_panel_id += 1
    
    panels[panel_id] = {
        'argument': new_arg.argument,
        'author': new_arg.author.strip(),
        'critiques': []
    }
    
    # Find the next position in the specified column
    positions_in_column = [pos for pid, (col, pos) in layout.items() if col == new_arg.column_index]
    next_position = max(positions_in_column) + 1 if positions_in_column else 0
    
    layout[panel_id] = (new_arg.column_index, next_position)
    
    return {"message": "Argument added successfully", "panel_id": panel_id}

@app.post("/critique")
async def add_critique(new_crit: NewCritique):
    """Add a new critique to specified panel"""
    if new_crit.panel_id not in panels:
        raise HTTPException(status_code=400, detail="Invalid panel ID")
    
    # Validate author is provided
    if not new_crit.author or not new_crit.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    panel = panels[new_crit.panel_id]
    
    # Validate indices
    if new_crit.start_ind < 0 or new_crit.end_ind > len(panel['argument']) or new_crit.start_ind >= new_crit.end_ind:
        raise HTTPException(status_code=400, detail="Invalid text indices")
    
    critique = {
        'text': new_crit.critique_text,
        'start_ind': new_crit.start_ind,
        'end_ind': new_crit.end_ind,
        'author': new_crit.author.strip()
    }
    
    panel['critiques'].append(critique)
    
    return {"message": "Critique added successfully"}

@app.post("/rating")
async def add_rating(new_rating: NewRating):
    """Add a rating for a statement"""
    # Validate rating values
    if not (1 <= new_rating.quality_rating <= 7) or not (1 <= new_rating.agreement_rating <= 7):
        raise HTTPException(status_code=400, detail="Ratings must be between 1 and 7")
    
    # Validate author is provided
    if not new_rating.author or not new_rating.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    # Validate statement exists
    if new_rating.statement_id.startswith("panel_"):
        parts = new_rating.statement_id.split("_")
        try:
            panel_id = int(parts[1])
            if panel_id not in panels:
                raise HTTPException(status_code=400, detail="Panel does not exist")
            
            if len(parts) > 2 and parts[2] == "critique":
                critique_index = int(parts[3])
                if critique_index >= len(panels[panel_id]['critiques']):
                    raise HTTPException(status_code=400, detail="Critique does not exist")
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid statement ID format")
    else:
        raise HTTPException(status_code=400, detail="Invalid statement ID format")
    
    # Store rating with author
    author = new_rating.author.strip()
    if author not in ratings:
        ratings[author] = {}
    
    ratings[author][new_rating.statement_id] = (
        new_rating.quality_rating,
        new_rating.agreement_rating
    )
    
    return {"message": "Rating added successfully"}

@app.get("/ratings")
async def get_ratings():
    """Get all ratings data"""
    return ratings

@app.get("/ratings/{author}")
async def get_user_ratings(author: str):
    """Get ratings for a specific author"""
    return ratings.get(author, {})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
