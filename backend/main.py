from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pydantic import BaseModel
from typing import List, Optional
import base64
import asyncio
import database
from llm import mind
from capture import capture_screen_base64, get_active_window_title

# -- Data Models --
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

# -- State --
# We keep a simple in-memory queue for immediate reactions to send to frontend
reaction_queue = []
last_analysis_time = 0

@app.get("/")
def read_root():
    return {"status": "Thea Backend is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/capture")
async def get_screen_capture(analyze: bool = False):
    """
    Returns a snapshot of the current screen.
    If analyze=True, it triggers an async LLM analysis of the screen.
    """
    global last_analysis_time
    
    title = get_active_window_title()
    image_b64 = capture_screen_base64(scale=0.5)
    
    # Simple rate limiting for passive analysis (at most once every 10 seconds)
    import time
    if analyze and (time.time() - last_analysis_time > 10):
        last_analysis_time = time.time()
        asyncio.create_task(process_observation(title, image_b64))
        
    return {
        "status": "ok",
        "window": title,
        "image": image_b64
    }

async def process_observation(window_title, image_b64):
    """Background task to analyze screen and store memory."""
    try:
        image_bytes = base64.b64decode(image_b64)
        result = mind.analyze_image(image_bytes)
        
        # Store in DB
        content = f"User is processing: {window_title}. Observation: {result['description']}"
        database.add_memory("observation", content, meta={"image_path": "todo", "reaction": result['reaction']})
        
        print(f"Analysis: {result}")
        
        # Add to reaction queue for frontend
        reaction_queue.append({
            "type": "reaction",
            "content": result['reaction'],
            "description": result['description']
        })
        
    except Exception as e:
        print(f"Analysis failed: {e}")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(msg: ChatMessage):
    # Retrieve recent history
    memories = database.get_recent_memories(limit=10)
    
    # Format history for Gemini
    # (Simple mapping: 'observation' -> system context or user part, 'chat' -> dialog)
    formatted_history = []
    
    # Pre-inject system persona
    formatted_history.append({
        "role": "model",
        "parts": ["I am Thea, a helpful and curious desktop companion."]
    })
    
    for mem in memories:
        if mem['type'] == 'observation':
            formatted_history.append({
                "role": "user",
                "parts": [f"[System Observation] {mem['content']}"]
            })
        elif mem['type'] == 'chat':
             # Note: In a real app we'd split user/model messages better from DB
             # For now, we assume stored chat memories are just context
             pass

    # Record user message
    database.add_memory("chat", f"User: {msg.message}")
    
    # Generate response
    response_text = mind.chat_response(formatted_history, msg.message)
    
    # Record model response
    database.add_memory("chat", f"Thea: {response_text}")
    
    return {"response": response_text}

@app.get("/updates")
def get_updates():
    """Frontend polls this to get new reactions."""
    if reaction_queue:
        return reaction_queue.pop(0)
    return {"type": "none"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
