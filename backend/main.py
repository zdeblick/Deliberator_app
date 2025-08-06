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
num_columns = 3

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
        # Create metadata table
        
        
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255)
            )
        ''')

        # Create statements table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS statements (
                id SERIAL PRIMARY KEY,
                statement_type TEXT NOT NULL
            )
        ''')
        
        # Create arguments table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS arguments (
                argument_id INTEGER PRIMARY KEY REFERENCES statements(id),
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
                critique_id INTEGER PRIMARY KEY REFERENCES statements(id),
                argument_id INTEGER REFERENCES arguments(argument_id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                start_ind INTEGER NOT NULL,
                end_ind INTEGER NOT NULL,
                author VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category_index INTEGER NOT NULL DEFAULT 0,
                quality INTEGER NOT NULL DEFAULT 5
            )
        ''')
        
        # Create ratings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                rating_id SERIAL PRIMARY KEY,
                ratee_id INTEGER REFERENCES statements(id) ON DELETE CASCADE,
                author VARCHAR(255) NOT NULL,
                quality_rating INTEGER CHECK (quality_rating >= 1 AND quality_rating <= 7),
                agreement_rating INTEGER CHECK (agreement_rating >= 1 AND agreement_rating <= 7),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ratee_id, author)
            )
        ''')
        
        # Insert default user if not exists
        await conn.execute('''
            INSERT INTO users (username, password) 
            VALUES ('system', NULL) 
            ON CONFLICT (username) DO NOTHING
        ''')
        
        # Insert sample data if arguments table is empty
        panel_count = await conn.fetchval('SELECT COUNT(*) FROM arguments')
        if panel_count == 0:
            sample_panels = [
                ('Climate change is primarily caused by human activities such as burning fossil fuels, deforestation, and industrial processes. The scientific consensus is overwhelming.', 'Dr. Climate', 0, 0),
                ('Renewable energy sources like solar and wind are becoming increasingly cost-effective and reliable alternatives to fossil fuels.', 'GreenTech', 0, 1),
                ('Universal healthcare systems provide better outcomes at lower costs compared to privatized systems, as evidenced by countries like Canada and the UK.', 'HealthPolicy', 1, 0),
                ('Artificial intelligence will revolutionize education by providing personalized learning experiences tailored to individual student needs.', 'EdTechFuture', 2, 0)
            ]
            
            for argument, author, col_idx, pos in sample_panels:
                # First create a statement entry
                statement_id = await conn.fetchval('''
                    INSERT INTO statements (statement_type)
                    VALUES ('argument')
                    RETURNING id
                ''')
                
                # Then create the argument with the statement_id as argument_id
                await conn.execute('''
                    INSERT INTO arguments (argument_id, argument, author, column_index, position_in_column)
                    VALUES ($1, $2, $3, $4, $5)
                ''', statement_id, argument, author, col_idx, pos)
                
                # Add sample critiques
                if statement_id == 1:  # First panel
                    # Create statement entries for critiques
                    critique1_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    critique2_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    
                    await conn.execute('''
                        INSERT INTO critiques (critique_id, argument_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, $2, 'The scientific consensus claim needs more specific evidence', 85, 120, 'Skeptic1'),
                        ($3, $2, 'What about natural climate variations?', 0, 27, 'NaturalCycles')
                    ''', critique1_id, statement_id, critique2_id)
                    
                elif statement_id == 2:  # Second panel
                    critique1_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    critique2_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    
                    await conn.execute('''
                        INSERT INTO critiques (critique_id, argument_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, $2, 'Reliability issues during peak demand periods', 77, 85, 'GridExpert'),
                        ($3, $2, 'Storage costs not included in analysis', 50, 77, 'EconomyWatch')
                    ''', critique1_id, statement_id, critique2_id)
                    
                elif statement_id == 3:  # Third panel
                    critique1_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    critique2_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    
                    await conn.execute('''
                        INSERT INTO critiques (critique_id, argument_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, $2, 'Wait times can be problematic', 91, 130, 'PatientAdvocate'),
                        ($3, $2, 'Different countries have different contexts', 132, 162, 'ComparativeStudy')
                    ''', critique1_id, statement_id, critique2_id)
                    
                elif statement_id == 4:  # Fourth panel
                    critique1_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    critique2_id = await conn.fetchval('''
                        INSERT INTO statements (statement_type)
                        VALUES ('critique')
                        RETURNING id
                    ''')
                    
                    await conn.execute('''
                        INSERT INTO critiques (critique_id, argument_id, text, start_ind, end_ind, author)
                        VALUES 
                        ($1, $2, 'Risk of reducing human interaction', 74, 101, 'HumanTouch'),
                        ($3, $2, 'Privacy concerns with student data', 102, 141, 'PrivacyWatch')
                    ''', critique1_id, statement_id, critique2_id)

async def recalculate_positions():
    """
    Dynamic positioning algorithm - this is where you'll implement your logic
    based on ratings, connections, or other criteria.
    For now, this is a placeholder that maintains current positions.
    """
    async with db_pool.acquire() as conn:
        # Get all arguments with their average ratings
        arguments_with_ratings = await conn.fetch('''
            SELECT 
                a.argument_id,
                a.argument,
                a.author,
                AVG(CASE WHEN r.statement_id = 'panel_' || a.argument_id THEN r.quality_rating END) as avg_quality,
                AVG(CASE WHEN r.statement_id = 'panel_' || a.argument_id THEN r.agreement_rating END) as avg_agreement,
                COUNT(CASE WHEN r.statement_id = 'panel_' || a.argument_id THEN 1 END) as rating_count
            FROM arguments a
            LEFT JOIN ratings r ON r.statement_id = 'panel_' || a.argument_id
            GROUP BY a.argument_id, a.argument, a.author
            ORDER BY a.argument_id
        ''')
        
        # TODO: Implement your dynamic positioning algorithm here
        # For now, we'll just distribute them evenly across columns
        num_columns = 3
        
        for i, arg in enumerate(arguments_with_ratings):
            new_column = i % num_columns
            new_position = i // num_columns
            
            # Update or insert position
            await conn.execute('''
                INSERT INTO argument_positions (argument_id, column_index, position_in_column, last_updated)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT (argument_id)
                DO UPDATE SET 
                    column_index = EXCLUDED.column_index,
                    position_in_column = EXCLUDED.position_in_column,
                    last_updated = EXCLUDED.last_updated
            ''', arg['argument_id'], new_column, new_position)
        
        return len(arguments_with_ratings)

async def check_and_trigger_repositioning():
    """
    Check if repositioning should be triggered based on new ratings
    This could be called after each rating is added, or on a schedule
    """
    async with db_pool.acquire() as conn:
        # Get count of recent ratings (last hour as example)
        recent_ratings_count = await conn.fetchval('''
            SELECT COUNT(*) FROM ratings 
            WHERE created_at > NOW() - INTERVAL '1 hour'
        ''')
        
        # Simple trigger: if we have 5+ new ratings in the last hour, reposition
        # You can customize this logic based on your needs
        if recent_ratings_count >= 5:
            await recalculate_positions()
            return True
    
    return False

async def convert_to_frontend_format():
    """Convert database data to the frontend format using dynamic positions"""
    async with db_pool.acquire() as conn:
        # Get all arguments with their current positions and critiques
        panels_query = '''
            SELECT 
                a.argument_id, a.argument, a.author, 
                ap.column_index, ap.position_in_column,
                c.critique_id, c.text as critique_text, 
                c.start_ind, c.end_ind, c.author as critique_author
            FROM arguments a
            LEFT JOIN argument_positions ap ON a.argument_id = ap.argument_id
            LEFT JOIN critiques c ON a.argument_id = c.argument_id
            ORDER BY ap.column_index, ap.position_in_column, c.critique_id
        '''
        
        rows = await conn.fetch(panels_query)
        
        # Group by panel
        panels_dict = {}
        for row in rows:
            argument_id = row['argument_id']
            if argument_id not in panels_dict:
                panels_dict[argument_id] = {
                    'argument_id': argument_id,
                    'argument': row['argument'],
                    'author': row['author'],
                    'column_index': row['column_index'] or 0,  # Default to 0 if no position set
                    'position_in_column': row['position_in_column'] or 0,
                    'critiques': []
                }
            
            # Add critique if it exists
            if row['critique_id']:
                critique_index = len(panels_dict[argument_id]['critiques'])
                panels_dict[argument_id]['critiques'].append([
                    row['critique_text'],
                    row['start_ind'],
                    row['end_ind'],
                    row['critique_author'],
                    critique_index
                ])
        
        # Group by columns
        if not panels_dict:
            return []
            
        max_col = max(panel['column_index'] for panel in panels_dict.values()) if panels_dict else 0
        columns = [[] for _ in range(max_col + 1)]
        
        for panel in panels_dict.values():
            columns[panel['column_index']].append({
                'argument_id': panel['argument_id'],
                'argument': panel['argument'],
                'author': panel['author'],
                'critiques': panel['critiques']
            })
        
        # Sort each column by position
        for col_idx, column in enumerate(columns):
            # Get positions for sorting
            panel_positions = []
            for panel in column:
                argument_id = panel['argument_id']
                position = next(p['position_in_column'] for p in panels_dict.values() if p['argument_id'] == argument_id)
                panel_positions.append((position, panel))
            
            panel_positions.sort(key=lambda x: x[0])
            columns[col_idx] = [panel for position, panel in panel_positions]
        
        return columns

class UserLogin(BaseModel):
    username: str
    password: Optional[str] = None
    create_account: bool = False

class NewArgument(BaseModel):
    argument: str
    author: str
    # Removed column_index - positioning will be handled dynamically

class NewCritique(BaseModel):
    argument_id: int
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
    """Add a new argument - automatically determines best column"""
    # Validate author is provided
    if not new_arg.author or not new_arg.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    async with db_pool.acquire() as conn:
        # The last column will be for unsorted args
       target_column = num_columns-1
        
        # Find the next position in the target column
        max_position = await conn.fetchval('''
            SELECT COALESCE(MAX(position_in_column), -1)
            FROM arguments
            WHERE column_index = $1
        ''', target_column)
        
        next_position = max_position + 1
        
        # First create a statement entry
        statement_id = await conn.fetchval('''
            INSERT INTO statements (statement_type)
            VALUES ('argument')
            RETURNING id
        ''')
        
        # Insert new argument with the statement_id
        await conn.execute('''
            INSERT INTO arguments (argument_id, argument, author, column_index, position_in_column)
            VALUES ($1, $2, $3, $4, $5)
        ''', statement_id, new_arg.argument, new_arg.author.strip(), target_column, next_position)
    
    return {"message": "Argument added successfully", "argument_id": statement_id, "repositioned": False}

@app.post("/critique")
async def add_critique(new_crit: NewCritique):
    """Add a new critique to specified panel"""
    # Validate author is provided
    if not new_crit.author or not new_crit.author.strip():
        raise HTTPException(status_code=400, detail="Author is required")
    
    async with db_pool.acquire() as conn:
        # Validate panel exists and get argument text
        panel = await conn.fetchrow('SELECT argument FROM arguments WHERE argument_id = $1', new_crit.argument_id)
        if not panel:
            raise HTTPException(status_code=400, detail="Invalid panel ID")
        
        # Validate indices
        argument = panel['argument']
        if new_crit.start_ind < 0 or new_crit.end_ind > len(argument) or new_crit.start_ind >= new_crit.end_ind:
            raise HTTPException(status_code=400, detail="Invalid text indices")
        
        # First create a statement entry for the critique
        statement_id = await conn.fetchval('''
            INSERT INTO statements (statement_type)
            VALUES ('critique')
            RETURNING id
        ''')
        
        # Insert critique with the statement_id
        await conn.execute('''
            INSERT INTO critiques (critique_id, argument_id, text, start_ind, end_ind, author)
            VALUES ($1, $2, $3, $4, $5, $6)
        ''', statement_id, new_crit.argument_id, new_crit.critique_text, new_crit.start_ind, new_crit.end_ind, new_crit.author.strip())
    
    return {"message": "Critique added successfully"}

@app.post("/rating")
async def add_rating(new_rating: NewRating):
    """Add a rating for a statement and potentially trigger repositioning"""
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
            argument_id = int(parts[1])
            
            async with db_pool.acquire() as conn:
                # Check if panel exists
                panel_exists = await conn.fetchval('SELECT 1 FROM arguments WHERE argument_id = $1', argument_id)
                if not panel_exists:
                    raise HTTPException(status_code=400, detail="Panel does not exist")
                
                # If it's a critique rating, validate critique exists
                if len(parts) > 2 and parts[2] == "critique":
                    critique_index = int(parts[3])
                    critique_count = await conn.fetchval('''
                        SELECT COUNT(*) FROM critiques WHERE argument_id = $1
                    ''', argument_id)
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
                agreement_rating = EXCLUDED.agreement_rating,
                created_at = CURRENT_TIMESTAMP
        ''', new_rating.statement_id, new_rating.author.strip(), 
             new_rating.quality_rating, new_rating.agreement_rating)
    
    # Check if we should trigger repositioning
    repositioned = await check_and_trigger_repositioning()
    
    response = {"message": "Rating added successfully"}
    if repositioned:
        response["repositioned"] = True
        response["message"] += " - Arguments repositioned based on new data"
    
    return response

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
