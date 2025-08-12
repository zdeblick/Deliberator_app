from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Dict, Optional
import uvicorn
import os
import asyncio
import asyncpg
from contextlib import asynccontextmanager
import numpy as np
from matrixfactorization import train_matrix_factorization
import json

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

async def set_value(key, value, overwrite=True):
    async with db_pool.acquire() as conn:
        json_value = json.dumps(value)
        
        if overwrite:
            await conn.execute(
                "INSERT INTO key_value_store (key, value) VALUES ($1, $2) "
                "ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP",
                key, json_value
            )
        else:
            await conn.execute(
                "INSERT INTO key_value_store (key, value) VALUES ($1, $2) "
                "ON CONFLICT (key) DO NOTHING",
                key, json_value
            )

async def get_value(key):
    async with db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT value FROM key_value_store WHERE key = $1", key)
        if result is None:
            return None
        return json.loads(result)
        
async def init_database():
    """Initialize database tables"""
    async with db_pool.acquire() as conn:
        # init schema in case it got deleted
        await conn.execute('CREATE SCHEMA IF NOT EXISTS public')

        await conn.execute('''
                CREATE TABLE IF NOT EXISTS key_value_store (
                key VARCHAR(255) PRIMARY KEY,
                value JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        await set_value('num_columns',3,overwrite=False)
        await set_value('global_intercept',0,overwrite=False)
        global num_columns
        num_columns = await get_value('num_columns')
        
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255),
            factor DOUBLE PRECISION,
            intercept DOUBLE PRECISION
        )
        ''')

        # Create statements table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS statements (
                id SERIAL PRIMARY KEY,
                statement_type TEXT NOT NULL,
                factor DOUBLE PRECISION,
                intercept DOUBLE PRECISION
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
                in_category_pos INTEGER NOT NULL DEFAULT 0
            )
        ''')
        
        # Create ratings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                rating_id SERIAL PRIMARY KEY,
                statement_id INTEGER REFERENCES statements(id) ON DELETE CASCADE,
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
                

async def convert_to_frontend_format():
    """Convert database data to the frontend format using dynamic positions"""
    async with db_pool.acquire() as conn:
        # Get all arguments with their current positions and critiques
        panels_query = '''
            SELECT 
                a.argument_id, a.argument, a.author, a.column_index,
                c.critique_id, c.text as critique_text, c.category_index,
                c.start_ind, c.end_ind, c.author as critique_author
            FROM arguments a
            LEFT JOIN critiques c ON a.argument_id = c.argument_id
            ORDER BY a.column_index, a.position_in_column, c.category_index, c.in_category_pos
        '''
        
        rows = await conn.fetch(panels_query)
        
        # max_col = max(rows['column_index'] for row in rows) if rows else 0
        columns = [[] for _ in range(num_columns)]

        argument_id = -1
        for row in rows:
            if argument_id != row['argument_id']:
                columns[row['column_index']].append( {
                    'argument_id': row['argument_id'],
                    'argument': row['argument'],
                    'author': row['author'],
                    'critiques': []
                })
                argument_id = row['argument_id']
            
            # Add critique if it exists
            if row['critique_id']:
                columns[row['column_index']][-1]['critiques'].append([
                    row['critique_text'],
                    row['start_ind'],
                    row['end_ind'],
                    row['critique_author'],
                    row['critique_id'],
                    row['category_index']
                ])

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
    position: int

class NewRating(BaseModel):
    statement_id: int  # id for argument or critique
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
        panel = await conn.fetchrow('SELECT argument, column_index FROM arguments WHERE argument_id = $1', new_crit.argument_id)
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
        
        category_index = min(panel['column_index'],1) if new_crit.position==0 else 1-min(panel['column_index'],1)
        next_pos = await conn.fetchval('''
            SELECT COALESCE(MAX(in_category_pos), -1)
            FROM critiques
            WHERE argument_id = $1 AND category_index = $2
        ''', new_crit.argument_id, category_index)
        
        # Insert critique with the statement_id
        await conn.execute('''
            INSERT INTO critiques (critique_id, argument_id, text, start_ind, end_ind, author, category_index, in_category_pos)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', statement_id, new_crit.argument_id, new_crit.critique_text, new_crit.start_ind, new_crit.end_ind, new_crit.author.strip(),category_index,next_pos)
    
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
    
    # Store rating (upsert)
    async with db_pool.acquire() as conn:
        rating_id = await conn.fetchval('''
            INSERT INTO ratings (statement_id, author, quality_rating, agreement_rating)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (statement_id, author)
            DO UPDATE SET 
                quality_rating = EXCLUDED.quality_rating,
                agreement_rating = EXCLUDED.agreement_rating,
                created_at = CURRENT_TIMESTAMP
            RETURNING id
        ''',
            new_rating.statement_id,
            new_rating.author.strip(),
            new_rating.quality_rating,
            new_rating.agreement_rating
        )
    
    repositioned = (rating_id>19) and (rating_id%10)==0
    
    if repositioned:
        rows =  await conn.fetch('''
            SELECT 
                r.agreement_rating, r.quality_rating, u.user_id, r.statement_id
            FROM ratings r
            LEFT JOIN users u ON r.author = u.username
        ''')
        a_ratings = [(row['agreement_rating']-4)/3 for row in rows]    # scale to [-1,1]
        q_ratings = [(row['quality_rating'])/3 for row in rows]        # scale to [-1,1]
        user_indexes = [row['user_id'] for row in rows]              
        statement_indexes = [row['statement_id'] for row in rows]    

        init_params = None
        if False: #warm start
            init_params = {}
            rows = await conn.fetch('SELECT factor, intercept FROM users')
            init_params['user_factors'] = [r['factor'] for r in rows]
            init_params['user_intercepts'] = [r['intercept'] for r in rows]
            rows = await conn.fetch('SELECT factor, intercept FROM statements')
            init_params['statement_factors'] = [r['factor'] for r in rows]
            init_params['statement_intercepts'] = [r['intercept'] for r in rows]
            init_params['global_intercept'] = await get_value('global_intercept')
        model, _ = train_matrix_factorization(a_ratings, user_indexes, statement_indexes, init_params=init_params)
        user_factors = model.user_factors.weight.detach().numpy().squeeze()
        statement_factors = model.statement_factors.weight.detach().numpy().squeeze()
        user_intercepts = model.user_intercepts.weight.detach().numpy().squeeze()
        statement_intercepts = model.statement_intercepts.weight.detach().numpy().squeeze()
        global_intercept = model.global_intercept.item()

        # TODO: use actual clustering for more than 2 clusters
        is_rator = np.isin(np.arange(user_factors.shape[0]),user_indexes)
        user_clusters = np.where(is_rator,(user_factors>0),np.nan)
        is_rated = np.isin(np.arange(statement_factors.shape[0]),statement_indexes)
        statement_clusters = np.where(is_rated,(statement_factors>0),np.nan)
        majority = 1*(np.nanmean(user_clusters)>0.5)
        minority = 1-majority
        condlist = [statement_clusters==majority, statement_clusters==minority, np.isnan(statement_clusters)]
        
        statement_cols = np.select(condlist,np.arange(num_cols),default=np.nan)
        mask = user_clusters[user_indexes]==statement_clusters[statement_indexes]  #ratings where users rated statements in their corresponding category
        quality_model, _  = train_matrix_factorization(q_ratings[mask], user_indexes[mask], statement_indexes[mask])
        is_rated = np.isin(np.arange(statement_factors.shape[0]),statement_indexes[mask])
        statement_quality = np.where(is_rated,quality_model.statement_intercepts.weight.detach().numpy().squeeze(),-1e6)
        
        argument_ids =  await conn.fetchvals('SELECT argument_id FROM arguments')
        argument_cols = statement_cols[np.array(argument_ids)]
        argument_quality = statement_quality[np.array(argument_ids)]
        position_in_column = np.nan*np.ones_like(argument_cols)
        for col in range(num_columns):
            position_in_column[argument_cols==col] = np.argsort(-argument_quality[argument_cols==col])

        rows = await conn.fetch('SELECT critique_id, argument_id FROM critiques')
        critique_ids = [r['critique_id'] for r in rows]
        critique_cols = statement_cols[np.array(critique_ids)]
        critique_quality = statement_quality[np.array(critique_ids)]
        parent_ids = [r['argument_id'] for r in rows]
        in_category_pos = np.nan*np.ones_like(critique_cols)
        category_index = np.nan*np.ones_like(critique_cols)
        
        for parent_id in np.unique(parent_ids):
            # assenting critiques
            mask = (parent_ids==parent_id) & (critique_cols==argument_cols[parent_id])
            in_category_pos[mask] = np.argsort(-critique_quality[mask])
            category_index[mask] = 1*(argument_cols[parent_id]==1) # put critiques on the side towards the column they're associated with
            # dissenting critiques
            mask = (parent_ids==parent_id) & (critique_cols!=argument_cols[parent_id])
            in_category_pos[mask] = np.argsort(-critique_quality[mask])
            category_index[mask] = 1-1*(argument_cols[parent_id]==1)

        await conn.executemany('''
                UPDATE users SET factor = $1, intercept = $2 WHERE user_id = $3
            ''', [(factor, intercept, user_id) for (factor, intercept, user_id) in zip(user_factors,user_intercepts,range(user_factors.size))])

        await conn.executemany('''
                UPDATE statements SET factor = $1, intercept = $2 WHERE id = $3
            ''', [(factor, intercept, id) for (factor, intercept, id) in zip(statement_factors,statement_intercepts,range(statement_factors.size))])
        
        await conn.executemany('''
                UPDATE arguments SET column_index = $1, position_in_column = $2 WHERE argument_id = $3
            ''', [(col, pos, argument_id) for (col, pos, argument_id) in zip(argument_cols,position_in_column,range(position_in_column.size))])

        await conn.executemany('''
                UPDATE critiques SET category_index = $1, in_category_pos = $2 WHERE critique_id = $3
            ''', [(cat, pos, critique_id) for (cat, pos, critique_id) in zip(category_index,in_category_pos,range(in_category_pos.size))])

    
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
