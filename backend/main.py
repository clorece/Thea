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
from typing import List, Optional, Dict, Any
import base64
import asyncio
import database
from llm import mind
from capture import capture_screen_base64, get_active_window_title
from activity_tracker import activity_collector
from pattern_engine import pattern_engine
from learning_config import get_config, update_config
from knowledge_engine import knowledge_engine

# -- Data Models --
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class LearningConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    track_files: Optional[bool] = None
    track_apps: Optional[bool] = None
    share_insights: Optional[bool] = None

# -- State --
# We keep a simple in-memory queue for immediate reactions to send to frontend
reaction_queue = []
last_analyzed_title = ""
last_analyzed_image = None
last_trigger_time = 0
last_seen_image = None
last_screen_change_time = 0

# -- Lifecycle Events --
@app.on_event("startup")
async def startup_event():
    """Start background services on app startup."""
    print("[Startup] Starting activity collector...")
    activity_collector.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on app shutdown."""
    print("[Shutdown] Stopping activity collector...")
    activity_collector.stop()

@app.get("/")
def read_root():
    return {"status": "Rin Backend is running", "learning": activity_collector.is_running()}

@app.get("/health")
def health_check():
    return {"status": "ok", "learning_active": activity_collector.is_running()}

@app.get("/capture")
async def get_screen_capture(analyze: bool = False):
    """
    Returns a snapshot of the current screen.
    If analyze=True, it triggers an async LLM analysis of the screen.
    """
    global last_analyzed_title, last_analyzed_image, last_trigger_time
    
    title = get_active_window_title()
    image_b64 = capture_screen_base64(scale=0.5)
    
    # -- Simplified Trigger Logic --
    # 1. Title Change: Immediate
    # 2. Timer: Every 15 seconds (if no title change)
    
    import time
    should_trigger = False
    current_time = time.time()
    
    # Check Title Change
    if title != last_analyzed_title:
        print(f"[Trigger] Title changed: '{last_analyzed_title}' -> '{title}'")
        should_trigger = True
    
    # Check Time Cooldown (Periodic reaction)
    elif (current_time - last_trigger_time) > 15:
        print(f"[Trigger] Timer > 15s")
        should_trigger = True

    if analyze and should_trigger:
        last_analyzed_title = title
        last_trigger_time = current_time
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
        result = await mind.analyze_image_async(image_bytes)
        
        # Store in DB
        content = f"User is processing: {window_title}. Observation: {result['description']}"
        database.add_memory("observation", content, meta={"image_path": "todo", "reaction": result['reaction']})
        
        # Get app info for learning
        app_name = "unknown"
        app_category = "other"
        try:
            from activity_tracker import AppTracker
            tracker = AppTracker()
            app_name, _ = tracker._get_active_window_info()
            app_category = tracker._categorize_app(app_name or "", window_title or "")
        except:
            pass
        
        # Rule-based knowledge extraction (Phase 2A)
        knowledge_result = knowledge_engine.process_observation(
            window_title=window_title or "",
            app_name=app_name or "",
            app_category=app_category,
            description=result['description']
        )
        
        if knowledge_result.get("learned"):
            print(f"[Knowledge] Rule-based learning extracted")
        
        # Vision-based Gemini learning (Phase 2B) - runs less frequently
        # Only run deep learning analysis every 10 observations to save API calls
        import random
        if random.random() < 0.1:  # 10% of observations get deep analysis
            try:
                gemini_result = await knowledge_engine.process_observation_with_gemini(
                    image_bytes=image_bytes,
                    window_title=window_title or "",
                    app_name=app_name or "",
                    app_category=app_category
                )
                
                if gemini_result.get("learned"):
                    print(f"[Knowledge] Gemini insight: {gemini_result.get('insight')}")
                
                # If Gemini generated a proactive message, add it to reaction queue
                if gemini_result.get("proactive"):
                    reaction_queue.append({
                        "type": "proactive",
                        "content": "",
                        "description": gemini_result["proactive"]
                    })
            except Exception as e:
                print(f"[Knowledge] Gemini learning failed: {e}")
        
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
        "parts": ["I am Rin, a helpful and curious desktop companion."]
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
    database.add_memory("chat", f"Rin: {response_text}")
    
    return {"response": response_text}

@app.get("/updates")
def get_updates():
    """Frontend polls this to get new reactions."""
    if reaction_queue:
        return reaction_queue.pop(0)
    return {"type": "none"}

@app.get("/shutdown")
def shutdown_server():
    """Kill the backend process."""
    import os
    import signal
    print("Shutting down backend...")
    activity_collector.stop()
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "shutting_down"}


# ============== Activity & Learning Endpoints ==============

@app.get("/activity/stats")
def get_activity_stats(days: int = 7):
    """Get activity statistics for the past N days."""
    return {
        "apps": database.get_app_activity_stats(days=days),
        "files": database.get_file_activity_stats(days=days)
    }

@app.get("/activity/insights")
def get_activity_insights():
    """Get Rin's learned insights about user patterns."""
    insights = pattern_engine.get_insights_for_rin(max_insights=5)
    return {
        "insights": insights,
        "context": pattern_engine.get_context_for_response()
    }

@app.get("/activity/patterns")
def get_learned_patterns(pattern_type: Optional[str] = None, min_confidence: float = 0.0):
    """Get learned patterns from the database."""
    patterns = database.get_patterns(pattern_type=pattern_type, min_confidence=min_confidence)
    return {"patterns": patterns}

@app.get("/activity/config")
def get_learning_config():
    """Get current learning configuration."""
    return get_config()

@app.post("/activity/config")
def update_learning_config(config_update: LearningConfigUpdate):
    """Update learning configuration."""
    updates = {k: v for k, v in config_update.dict().items() if v is not None}
    if updates:
        new_config = update_config(updates)
        return {"status": "updated", "config": new_config}
    return {"status": "no_changes", "config": get_config()}


# ============== Knowledge Graph Endpoints ==============

@app.get("/knowledge/summary")
def get_knowledge_summary():
    """Get a summary of what Rin knows about the user."""
    return database.get_knowledge_summary()

@app.get("/knowledge/user")
def get_user_knowledge(category: Optional[str] = None, min_confidence: float = 0.0):
    """Get knowledge Rin has learned about the user."""
    knowledge = database.get_user_knowledge(category=category, min_confidence=min_confidence)
    return {"knowledge": knowledge, "count": len(knowledge)}

@app.get("/knowledge/insights")
def get_rin_insights():
    """Get Rin's generated insights."""
    unshared = database.get_unshared_insights(min_relevance=0.5, limit=10)
    return {"insights": unshared, "count": len(unshared)}

@app.get("/knowledge/proactive")
def get_proactive_insight():
    """Get a proactive insight Rin wants to share."""
    insight = knowledge_engine.generate_proactive_insight()
    if insight:
        return {"has_insight": True, **insight}
    return {"has_insight": False}

class ManualInsight(BaseModel):
    message: str
    relevance: float = 1.0

@app.post("/knowledge/insight/manual")
async def trigger_manual_insight(insight: ManualInsight):
    """Manually trigger a proactive insight (for debugging)."""
    insight_id = database.add_rin_insight(
        insight_type="proactive",
        content=insight.message,
        context={"source": "manual_trigger"},
        relevance_score=insight.relevance
    )
    return {"status": "created", "id": insight_id}

@app.post("/knowledge/insight/{insight_id}/feedback")
def submit_insight_feedback(insight_id: int, feedback: str = "acknowledged"):
    """Submit feedback on an insight."""
    knowledge_engine.mark_insight_delivered(insight_id, feedback)
    return {"status": "ok"}

@app.get("/knowledge/context")
def get_knowledge_context():
    """Get knowledge context string for LLM prompts."""
    return {"context": knowledge_engine.get_context_for_llm()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
