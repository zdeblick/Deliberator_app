from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Dict, Optional
import uvicorn
import os
import asyncio
import asyncpg
from contextlib import asynccontextmanager

# Database connection pool
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_pool
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is required")
    
    # Create connection pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    
    # Initialize database
    await init_database()
    
    yield
    
    # Shutdown
    if db_pool:
        await db_pool.close()

app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

async def init_database():
    """Initialize database tables"""
    async with db_pool.acquire() as conn:
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255)
            )
        ''')
        
        # Create panels table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS panels (
                panel_id SERIAL PRIMARY KEY,
                argument TEXT NOT NULL,
                author VARCHAR(255) NOT NULL,
                column_index INTEGER NOT NULL,
                position_in_column INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create critiques table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS critiques (
                critique_id SERIAL PRIMARY KEY,
                panel_id INTEGER REFERENCES panels(panel_id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                start_ind INTEGER NOT NULL,
                end_ind INTEGER NOT NULL,
                author VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create ratings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                rating_id SERIAL PRIMARY KEY,
                statement_id VARCHAR(255) NOT NULL,
                author VARCHAR(255) NOT NULL,
                quality_rating INTEGER CHECK (quality_rating >= 1 AND quality_rating <= 7),
                agreement_rating INTEGER CHECK (agreement_rating >= 1 AND agreement_rating <= 7),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(statement_id, author)
            )
        ''')
        
        # Insert default user if not exists
        await conn.execute('''
            INSERT INTO users (username, password) 
            VALUES ('system', NULL) 
            ON CONFLICT (username) DO NOTHING
        ''')
        
        # Insert sample data if panels table is empty
        panel_count = await conn.fetchval('SELECT COUNT(*) FROM panels')
        if panel_count == 0:
            sample_panels = [
                ('Climate change is primarily caused by human activities such as burning fossil fuels, deforestation, and industrial processes. The scientific consensus is overwhelming.', 'Dr. Climate', 0, 0),
                ('Renewable energy sources like solar and wind are becoming increasingly cost-effective and reliable alternatives to fossil fuels.', 'GreenTech', 0, 1),
                ('Universal healthcare systems provide better outcomes at lower costs compared to privatized systems, as evidenced by countries like Canada and the UK.', 'HealthPolicy', 1, 0),
                ('Artificial intelligence will revolutionize education by providing personalized learning experiences tailored to individual student needs.', 'EdTechFuture', 2, 0)
            ]
            
            for argument, author, col_idx, pos in sample_panels:
                panel_id = await conn.fetchval('''
                    INSERT INTO panels (argument, author, column_index, position_in_column)
                    VALUES ($1, $2, $3, $4)
                    RETURNING panel_id
                ''', argument, author, col_idx, pos)
                
                # Add sample critiques
                if panel_id == 1:  # First panel
                    await conn.execute('''
                        INSERT INTO critiques (panel_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, 'The scientific consensus claim needs more specific evidence', 85, 120, 'Skeptic1'),
                        ($1, 'What about natural climate variations?', 0, 27, 'NaturalCycles')
                    ''', panel_id)
                elif panel_id == 2:  # Second panel
                    await conn.execute('''
                        INSERT INTO critiques (panel_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, 'Reliability issues during peak demand periods', 77, 85, 'GridExpert'),
                        ($1, 'Storage costs not included in analysis', 50, 77, 'EconomyWatch')
                    ''', panel_id)
                elif panel_id == 3:  # Third panel
                    await conn.execute('''
                        INSERT INTO critiques (panel_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, 'Wait times can be problematic', 91, 130, 'PatientAdvocate'),
                        ($1, 'Different countries have different contexts', 132, 162, 'ComparativeStudy')
                    ''', panel_id)
                elif panel_id == 4:  # Fourth panel
                    await conn.execute('''
                        INSERT INTO critiques (panel_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, 'Risk of reducing human interaction', 74, 101, 'HumanTouch'),
                        ($1, 'Privacy concerns with student data', 102, 141, 'PrivacyWatch')
                    ''', panel_id)

async def convert_to_frontend_format():
    """Convert database data to the frontend format"""
    async with db_pool.acquire() as conn:
        # Get all panels with their critiques
        panels_query = '''
            SELECT p.panel_id, p.argument, p.author, p.column_index, p.position_in_column,
                   c.critique_id, c.text as critique_text, c.start_ind, c.end_ind, c.author as critique_author
            FROM panels p
            LEFT JOIN critiques c ON p.panel_id = c.panel_id
            ORDER BY p.column_index, p.position_in_column, c.critique_id
        '''
        
        rows = await conn.fetch(panels_query)
        
        # Group by panel
        panels_dict = {}
        for row in rows:
            panel_id = row['panel_id']
            if panel_id not in panels_dict:
                panels_dict[panel_id] = {
                    'panel_id': panel_id,
                    'argument': row['argument'],
                    'author': row['author'],
                    'column_index': row['column_index'],
                    'position_in_column': row['position_in_column'],
                    'critiques': []
                }
            
            # Add critique if it exists
            if row['critique_id']:
                critique_index = len(panels_dict[panel_id]['critiques'])
                panels_dict[panel_id]['critiques'].append([
                    row['critique_text'],
                    row['start_ind'],
                    row['end_ind'],
                    row['critique_author'],
                    critique_index
                ])
        
        # Group by columns
        if not panels_dict:
            return []
            
        max_col = max(panel['column_index'] for panel in panels_dict.values())
        columns = [[] for _ in range(max_col + 1)]
        
        for panel in panels_dict.values():
            columns[panel['column_index']].append({
                'panel_id': panel['panel_id'],
                'argument': panel['argument'],
                'author': panel['author'],
                'critiques': panel['critiques']
            })
        
        # Sort each column by position
        for col_idx, column in enumerate(columns):
            # Get positions for sorting
            panel_positions = []
            for panel in column:
                panel_id = panel['panel_id']
                position = next(p['position_in_column'] for p in panels_dict.values() if p['panel_id'] == panel_id)
                panel_positions.append((position, panel))
            
            panel_positions.sort(key=lambda x: x[0])
            columns[col_idx] = [panel for position, panel in panel_positions]
        
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
    
    async with db_pool.acquire() as conn:
        if user_data.create_account:
            # Check if user already exists
            existing = await conn.fetchrow('SELECT username FROM users WHERE username = $1', username)
            if existing:
                raise HTTPException(status_code=400, detail="Username already exists")
            
            # Create new user
            await conn.execute(
                'INSERT INTO users (username, password) VALUES ($1, $2)',
                username, user_data.password
            )
            return {"message": "Account created successfully", "username": username}
        else:
            # Check if user exists and password matches
            user = await conn.fetchrow('SELECT password FROM users WHERE username = $1', username)
            if not user:
                raise HTTPException(status_code=400, detail="Username does not exist")
            if user['password'] != user_data.password:
                raise HTTPException(status_code=400, detail="Incorrect password")
            return {"message": "Login successful", "username": username}

@app.get("/data")
async def get_data():
    """Return the data in frontend format"""
    return await convert_to_frontend_format()

@app.post("/argument")
async def add_argument(new_arg: NewArgument):
    """Add a new argument to specified column"""
    # Validate author is provided
    if not new_arg.author or not new_arg.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    async with db_pool.acquire() as conn:
        # Find the next position in the specified column
        max_position = await conn.fetchval('''
            SELECT COALESCE(MAX(position_in_column), -1)
            FROM panels
            WHERE column_index = $1
        ''', new_arg.column_index)
        
        next_position = max_position + 1
        
        # Insert new panel
        panel_id = await conn.fetchval('''
            INSERT INTO panels (argument, author, column_index, position_in_column)
            VALUES ($1, $2, $3, $4)
            RETURNING panel_id
        ''', new_arg.argument, new_arg.author.strip(), new_arg.column_index, next_position)
    
    return {"message": "Argument added successfully", "panel_id": panel_id}

@app.post("/critique")
async def add_critique(new_crit: NewCritique):
    """Add a new critique to specified panel"""
    # Validate author is provided
    if not new_crit.author or not new_crit.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    async with db_pool.acquire() as conn:
        # Validate panel exists and get argument text
        panel = await conn.fetchrow('SELECT argument FROM panels WHERE panel_id = $1', new_crit.panel_id)
        if not panel:
            raise HTTPException(status_code=400, detail="Invalid panel ID")
        
        # Validate indices
        argument = panel['argument']
        if new_crit.start_ind < 0 or new_crit.end_ind > len(argument) or new_crit.start_ind >= new_crit.end_ind:
            raise HTTPException(status_code=400, detail="Invalid text indices")
        
        # Insert critique
        await conn.execute('''
            INSERT INTO critiques (panel_id, text, start_ind, end_ind, author)
            VALUES ($1, $2, $3, $4, $5)
        ''', new_crit.panel_id, new_crit.critique_text, new_crit.start_ind, new_crit.end_ind, new_crit.author.strip())
    
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
            
            async with db_pool.acquire() as conn:
                # Check if panel exists
                panel_exists = await conn.fetchval('SELECT 1 FROM panels WHERE panel_id = $1', panel_id)
                if not panel_exists:
                    raise HTTPException(status_code=400, detail="Panel does not exist")
                
                # If it's a critique rating, validate critique exists
                if len(parts) > 2 and parts[2] == "critique":
                    critique_index = int(parts[3])
                    critique_count = await conn.fetchval('''
                        SELECT COUNT(*) FROM critiques WHERE panel_id = $1
                    ''', panel_id)
                    if critique_index >= critique_count:
                        raise HTTPException(status_code=400, detail="Critique does not exist")
                        
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Invalid statement ID format")
    else:
        raise HTTPException(status_code=400, detail="Invalid statement ID format")
    
    # Store rating (upsert)
    async with db_pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO ratings (statement_id, author, quality_rating, agreement_rating)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (statement_id, author)
            DO UPDATE SET 
                quality_rating = EXCLUDED.quality_rating,
                agreement_rating = EXCLUDED.agreement_rating
        ''', new_rating.statement_id, new_rating.author.strip(), 
             new_rating.quality_rating, new_rating.agreement_rating)
    
    return {"message": "Rating added successfully"}

@app.get("/ratings")
async def get_ratings():
    """Get all ratings data"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM ratings')
        
        # Convert to the expected format: author -> statement_id -> (quality, agreement)
        ratings = {}
        for row in rows:
            author = row['author']
            if author not in ratings:
                ratings[author] = {}
            ratings[author][row['statement_id']] = (row['quality_rating'], row['agreement_rating'])
        
        return ratings

@app.get("/ratings/{author}")
async def get_user_ratings(author: str):
    """Get ratings for a specific author"""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM ratings WHERE author = $1', author)
        
        user_ratings = {}
        for row in rows:
            user_ratings[row['statement_id']] = (row['quality_rating'], row['agreement_rating'])
        
        return user_ratings

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
