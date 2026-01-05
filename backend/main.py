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
from io import BytesIO
from PIL import Image, ImageChops, ImageStat
import database
from llm import mind, split_into_chunks, get_api_session_stats
from capture import capture_screen_base64, get_active_window_title
from activity_tracker import activity_collector
from pattern_engine import pattern_engine
from learning_config import get_config, update_config
from knowledge_engine import knowledge_engine
from ears import ears
from logger import log_activity, clear_activity_log
from thinking_engine import thinking_engine, ThinkingState

# -- Data Models --
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: List[str]

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
last_recommendation_time = 0  # Cooldown for recommendations
thinking_enabled = True  # Feature flag for thinking system

# -- Lifecycle Events --
@app.on_event("startup")
async def startup_event():
    """Start background services on app startup."""
    
    # Clear logs on startup to keep them fresh per session
    import os
    try:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        # Ensure log dir exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Clear all logs on startup for a fresh session
        for log_file in ["api_usage.log", "error.log", "backend.log", "activity.log"]:
            path = os.path.join(log_dir, log_file)
            if os.path.exists(path):
                with open(path, "w") as f:
                    f.write("") # Truncate
        
        # Mark new session in activity log
        log_activity("SYSTEM", "=== Rin Backend Started (Session Return) ===")

        print("[Startup] Cleared api_usage.log and error.log")
    except Exception as e:
        print(f"[Startup] Failed to clear logs: {e}")

    print("[Startup] Starting activity collector...")
    activity_collector.start()
    print("[Startup] Starting ears (audio capture)...")
    ears.start()
    
    # Start thinking cycle background task
    if thinking_enabled:
        asyncio.create_task(thinking_cycle_loop())
        print("[Startup] Thinking system enabled")
    
    # Verify logging works
    log_activity("SYSTEM", "Rin Backend Started - Logging Active")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on app shutdown."""
    print("[Shutdown] Stopping activity collector...")
    activity_collector.stop()
    print("[Shutdown] Stopping ears...")
    ears.stop()

# Local log_activity removed in favor of logger module


# ============== Thinking System ==============

async def thinking_cycle_loop():
    """Background loop that runs thinking cycles periodically."""
    print("[Thinking] Background thinking loop started")
    await asyncio.sleep(10)  # Initial delay to let system stabilize
    
    while True:
        try:
            # Update thinking state
            state = thinking_engine.update_state()
            
            # Run thinking cycle if it's time
            if thinking_engine.should_run_thinking_cycle():
                result = await thinking_engine.run_thinking_cycle()
                
                # Process significant observations through Gemini
                for obs in result.significant_observations:
                    if obs.image_bytes:
                        thinking_engine.increment_gemini_calls()
                        await process_significant_observation(obs)
            
            # Deep thinking during idle
            if state == ThinkingState.DEEP_REFLECTION:
                await run_deep_thinking()
            
        except Exception as e:
            print(f"[Thinking] Cycle error: {e}")
        
        # Sleep until next check (5 seconds for responsiveness)
        await asyncio.sleep(5)


async def process_significant_observation(obs):
    """Process a significant observation through Gemini."""
    try:
        # This is where Gemini gets called for truly significant observations
        gemini_result = await knowledge_engine.process_observation_with_gemini(
            image_bytes=obs.image_bytes,
            window_title=obs.window_title,
            app_name=obs.app_name,
            app_category=obs.app_category,
            audio_bytes=obs.audio_bytes
        )
        
        # Handle recommendations
        rec_content = gemini_result.get("recommendation")
        if rec_content and rec_content.lower() != "null" and thinking_engine.can_notify():
            thinking_engine.mark_notification_sent()
            
            reaction_queue.append({
                "type": "recommendation",
                "content": "💡",
                "description": rec_content
            })
            
            database.add_memory(
                "chat",
                rec_content,
                meta={"role": "model", "is_recommendation": True}
            )
            
            log_activity("RECOMMENDATION", f"{rec_content}")
            print(f"[Thinking] Significant recommendation: {rec_content}")
            
    except Exception as e:
        print(f"[Thinking] Gemini processing failed: {e}")


async def run_deep_thinking():
    """Run deep thinking tasks during user idle time."""
    try:
        # Knowledge organization
        knowledge_engine.organize_knowledge()
        
        # Apply confidence decay (weekly)
        knowledge_engine.apply_confidence_decay()
        
        # Pattern analysis
        pattern_engine.analyze_all(force=True)
        
        print("[Thinking] Deep thinking cycle completed")
        
    except Exception as e:
        print(f"[Thinking] Deep thinking error: {e}")


@app.get("/thinking/status")
def get_thinking_status():
    """Get current thinking system status."""
    return thinking_engine.get_status()


@app.get("/thinking/thoughts")
def get_pending_thoughts():
    """Get any thoughts Rin wants to share."""
    thoughts = thinking_engine.get_pending_thoughts()
    return {"thoughts": thoughts, "count": len(thoughts)}


@app.get("/")
def read_root():
    return {"status": "Rin Backend is running", "learning": activity_collector.is_running()}

@app.get("/health")
def health_check():
    return {"status": "ok", "learning_active": activity_collector.is_running()}


@app.get("/api/usage")
def get_api_usage():
    """Get real-time API usage statistics for this session."""
    stats = get_api_session_stats()
    thinking_stats = thinking_engine.get_status().get("stats", {})
    return {
        "gemini": stats,
        "thinking": {
            "observations_total": thinking_stats.get("observations_total", 0),
            "observations_deduplicated": thinking_stats.get("observations_deduplicated", 0),
            "significant_count": thinking_stats.get("significant_count", 0),
            "gemini_calls_from_thinking": thinking_stats.get("gemini_calls", 0)
        }
    }


def calculate_visual_difference(img_b64_1, img_b64_2):
    """
    Calculates the visual difference between two base64 images.
    Returns a float representing the percentage difference (0.0 to 100.0).
    """
    try:
        if not img_b64_1 or not img_b64_2:
            return 100.0
            
        # Convert base64 to PIL Images
        img1_data = base64.b64decode(img_b64_1)
        img2_data = base64.b64decode(img_b64_2)
        
        img1 = Image.open(BytesIO(img1_data)).convert('RGB')
        img2 = Image.open(BytesIO(img2_data)).convert('RGB')
        
        # Resize to small thumbnails for fast comparison
        thumb_size = (64, 64)
        img1 = img1.resize(thumb_size)
        img2 = img2.resize(thumb_size)
        
        # Calculate difference
        diff = ImageChops.difference(img1, img2)
        stat = ImageStat.Stat(diff)
        
        # Average difference across channels
        diff_val = sum(stat.mean) / len(stat.mean)
        
        # Normalize roughly to a percentage (255 is max diff)
        return (diff_val / 255.0) * 100.0
    except Exception as e:
        print(f"Diff Check Error: {e}")
        return 100.0

@app.get("/capture")
async def get_screen_capture(analyze: bool = False):
    """
    Returns a snapshot of the current screen.
    If analyze=True, it triggers an async LLM analysis of the screen.
    """
    global last_analyzed_title, last_analyzed_image, last_trigger_time
    
    title = get_active_window_title()
    # Use higher quality scale
    image_b64 = capture_screen_base64(scale=0.75)
    
    # -- Smart Trigger Logic --
    # 1. Title Change: Immediate
    # 2. Audio Spike: Immediate (independent of visual cooldown)
    # 3. Visual Change: If timer > 5s AND significant visual difference (>5%)
    # 4. Force Update: If timer > 30s (sanity check)
    
    import time
    should_trigger = False
    trigger_type = None
    current_time = time.time()
    visual_diff = 0.0
    
    # Check Audio Spike (independent trigger)
    _, volume_delta = ears.get_volume_delta()
    if volume_delta > 0.15:  # Significant volume increase (silence -> sound)
        print(f"[Trigger] Audio spike detected: delta={volume_delta:.3f}")
        should_trigger = True
        trigger_type = "audio"
    
    # Check Title Change
    if not should_trigger and title != last_analyzed_title:
        print(f"[Trigger] Title changed: '{last_analyzed_title}' -> '{title}'")
        should_trigger = True
        trigger_type = "title"
    
    # Check Timer & Visuals (only if no audio/title trigger)
    if not should_trigger and (current_time - last_trigger_time) > 5.0:
        # Only check visual difference if enough time has passed to matter
        if last_analyzed_image:
            visual_diff = calculate_visual_difference(last_analyzed_image, image_b64)
            # Threshold: 5% difference (tuned from 2.5% to reduce noise)
            if visual_diff > 5.0:
                print(f"[Trigger] Visual Diff: {visual_diff:.2f}% (> 5%)")
                should_trigger = True
                trigger_type = "visual"
            elif (current_time - last_trigger_time) > 30.0:
                 # Force update every 30s even if static, just to be alive
                 print(f"[Trigger] Force update (30s timeout)")
                 should_trigger = True
                 trigger_type = "force"
        else:
            should_trigger = True
            trigger_type = "initial"
            
    if analyze and should_trigger:
        last_analyzed_title = title
        last_trigger_time = current_time
        last_analyzed_image = image_b64  # Update last seen image
        asyncio.create_task(process_observation(title, image_b64, trigger_type=trigger_type))
        
    return {
        "status": "ok",
        "window": title,
        "image": image_b64,
        "diff": visual_diff
    }

async def process_observation(window_title, image_b64, trigger_type=None):
    """Background task to analyze screen and optionally buffer for thinking."""
    try:
        image_bytes = base64.b64decode(image_b64)
        
        # Capture simultaneous audio (last 5 seconds)
        audio_bytes = ears.get_recent_audio_bytes(duration_seconds=5.0)
        if audio_bytes:
            print(f"[Ears] Captured {len(audio_bytes)} bytes of audio context")
        else:
            print(f"[Ears] No audio captured (running={ears.running}, buffer_size={len(ears.audio_buffer)})")
        
        # Always get basic reaction for immediate UI feedback
        result = await mind.analyze_image_async(image_bytes, audio_bytes=audio_bytes, trigger_type=trigger_type)
        
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
        
        # Rule-based knowledge extraction (still runs - it's cheap/local)
        knowledge_result = knowledge_engine.process_observation(
            window_title=window_title or "",
            app_name=app_name or "",
            app_category=app_category,
            description=result['description']
        )
        
        if knowledge_result.get("learned"):
            print(f"[Knowledge] Rule-based learning extracted")
        
        # ============== THINKING SYSTEM INTEGRATION ==============
        # Instead of calling Gemini directly, buffer the observation
        # The thinking cycle will determine if it's significant enough for Gemini
        
        if thinking_enabled:
            # Buffer this observation for the thinking system
            buffered = thinking_engine.buffer_observation(
                window_title=window_title or "",
                app_name=app_name or "",
                app_category=app_category,
                image_bytes=image_bytes,
                audio_bytes=audio_bytes
            )
            
            if buffered:
                print(f"[Thinking] Observation buffered (buffer size: {len(thinking_engine.observation_buffer)})")
            else:
                print(f"[Thinking] Observation deduplicated")
        else:
            # Fallback: Old behavior when thinking is disabled
            import random
            if random.random() < 0.1:  # Reduced to 10% when fallback
                try:
                    gemini_result = await knowledge_engine.process_observation_with_gemini(
                        image_bytes=image_bytes,
                        window_title=window_title or "",
                        app_name=app_name or "",
                        app_category=app_category,
                        audio_bytes=audio_bytes
                    )
                    
                    rec_content = gemini_result.get("recommendation")
                    if rec_content and rec_content.lower() != "null":
                        import time as time_module
                        global last_recommendation_time
                        if time_module.time() - last_recommendation_time > 30:
                            last_recommendation_time = time_module.time()
                            reaction_queue.append({
                                "type": "recommendation",
                                "content": "💡",
                                "description": rec_content
                            })
                            log_activity("RECOMMENDATION", f"{rec_content}")
                except Exception as e:
                    print(f"[Knowledge] Gemini learning failed: {e}")
        
        print(f"Analysis: {result}")
        
        # Log the observation
        log_activity("OBSERVATION", f"Window: {window_title}")
        
        # Add to reaction queue for frontend
        reaction_queue.append({
            "type": "reaction",
            "content": result['reaction'],
            "description": result['description']
        })
        
        # Log the reaction
        log_activity("REACTION", f"{result['description']}")
        
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
    
    # Capture current audio for context (if ears are active)
    audio_bytes = None
    if ears.running:
        audio_bytes = ears.get_recent_audio_bytes(duration_seconds=5.0)
        if audio_bytes:
            print(f"[Chat] Including {len(audio_bytes)} bytes of audio context")
    
    # Generate response (with optional audio context)
    response_text = await mind.chat_response_async(formatted_history, msg.message, audio_bytes=audio_bytes)
    
    # Record model response (full text)
    database.add_memory("chat", f"Rin: {response_text}")
    
    # Log to activity log
    log_activity("CHAT", f"User: {msg.message}")
    log_activity("CHAT", f"Rin: {response_text}")
    
    # Split for display
    chunks = split_into_chunks(response_text, limit=200)
    
    # Queue extra chunks
    if len(chunks) > 1:
        for chunk in chunks[1:]:
            # We use 'chat' type so frontend ChatBox can potentially pick it up via queue if we wire it,
            # OR we use 'reaction' type so it shows in overlay.
            # User request: "queue should adapt to this change by queueing rin's seperated message in order"
            # We will use 'chat' type and ensure frontend handles it.
            reaction_queue.append({
                "type": "chat",
                "content": "💬",
                "description": chunk
            })
            
    return {"response": [chunks[0]] if chunks else []}

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

@app.get("/ears/status")
def get_ears_status():
    """Get current status of audio listening."""
    return {"listening": ears.running, "device": ears.mic.name if ears.mic else "None"}

@app.post("/ears/toggle")
def toggle_ears(enable: bool):
    """Enable or disable audio listening."""
    if enable:
        ears.start()
    else:
        ears.stop()
    return {"listening": ears.running}


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
