"""
Ollama LLM Module for Rin - Local AI Integration.
Replaces the Gemini-based llm.py with local Ollama models.

Models used:
- gemma3:12b - Chat and reasoning
- moondream:latest - Visual understanding
- Whisper (via whisper_processor) - Audio transcription
"""

import os
import time
import re
import base64
import datetime
import asyncio
import json
from typing import Optional, List, Dict, Any

# Ollama client
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("[Ollama] ollama package not installed. Run: pip install ollama")

# Whisper processor for audio
from whisper_processor import whisper_processor

# Session-level usage tracking (for compatibility with existing code)
_api_session_stats = {
    "session_start": None,
    "total_calls": 0,
    "calls_by_endpoint": {},
}


def log_api_usage(endpoint, status="Success", details=""):
    """
    Logs API usage for tracking (local calls counted for statistics).
    """
    global _api_session_stats
    
    try:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        if _api_session_stats["session_start"] is None:
            _api_session_stats["session_start"] = datetime.datetime.now()
        
        _api_session_stats["total_calls"] += 1
        if endpoint not in _api_session_stats["calls_by_endpoint"]:
            _api_session_stats["calls_by_endpoint"][endpoint] = 0
        _api_session_stats["calls_by_endpoint"][endpoint] += 1
        
        session_duration = datetime.datetime.now() - _api_session_stats["session_start"]
        session_mins = int(session_duration.total_seconds() / 60)
        
        log_path = os.path.join(log_dir, "ollama_usage.log")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        call_count = _api_session_stats["calls_by_endpoint"][endpoint]
        total = _api_session_stats["total_calls"]
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] #{total} | {endpoint} ({call_count}x) | {status} | {details}\n")
            
    except Exception as e:
        print(f"Failed to log usage: {e}")


def get_api_session_stats():
    """Returns current session usage statistics."""
    if _api_session_stats["session_start"]:
        duration = datetime.datetime.now() - _api_session_stats["session_start"]
        mins = int(duration.total_seconds() / 60)
    else:
        mins = 0
    return {
        "session_minutes": mins,
        "total_calls": _api_session_stats["total_calls"],
        "by_endpoint": _api_session_stats["calls_by_endpoint"].copy()
    }


def split_into_chunks(text, limit=150):
    """
    Splits text into chunks of roughly 'limit' characters.
    """
    if len(text) <= limit:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    sentences = re.split(r'(?<=[.!?]) +', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < limit:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    final_chunks = []
    for c in chunks:
        while len(c) > limit:
            split_point = c[:limit].rfind(" ")
            if split_point == -1: split_point = limit
            final_chunks.append(c[:split_point])
            c = c[split_point:].strip()
        if c:
            final_chunks.append(c)
            
    return final_chunks


class OllamaMind:
    """
    Local AI mind for Rin using Ollama models.
    
    OPTIMIZED for performance:
    - Uses smaller, faster models (4b instead of 12b)
    - Unloads models after each request (keep_alive=0)
    - GPU/CPU workload splitting via num_gpu and num_thread
    - Provides cleanup functions for shutdown
    """
    
    def __init__(self):
        # Use separate models for chat and vision
        # llama3.2-vision is accurate at reading screen text/titles
        self.chat_model = "gemma3:4b"        # 4B for text-only chat
        self.vision_model = "llama3.2-vision:latest"  # Accurate vision with Vulkan GPU
        self._active = OLLAMA_AVAILABLE
        
        # === PERFORMANCE OPTIONS ===
        # keep_alive=0 means unload model immediately after request
        self.keep_alive = 0
        
        # GPU layers: -1 = all layers to GPU (auto-detect via Vulkan)
        self.num_gpu = -1
        
        # Options dict passed to all Ollama calls
        self.options = {
            'num_gpu': self.num_gpu,
        }
        
        if self._active:
            print(f"[OllamaMind] Chat: {self.chat_model}, Vision: {self.vision_model}")
            print(f"[OllamaMind] GPU: num_gpu={self.num_gpu}, keep_alive={self.keep_alive}")
        else:
            print("[OllamaMind] Ollama not available - AI features disabled")
    
    def is_active(self):
        return self._active
    
    def unload_models(self):
        """Explicitly unload all models from memory."""
        if not self._active:
            return
        try:
            # Send empty request with keep_alive=0 to force unload
            ollama.chat(
                model=self.chat_model,
                messages=[{'role': 'user', 'content': ''}],
                keep_alive=0
            )
            ollama.chat(
                model=self.vision_model,
                messages=[{'role': 'user', 'content': ''}],
                keep_alive=0
            )
            print("[OllamaMind] Models unloaded from memory")
        except Exception as e:
            print(f"[OllamaMind] Unload error (safe to ignore): {e}")
    
    def load_user_profile(self):
        """
        Loads the user profile from file AND dynamic database knowledge.
        """
        profile = {}
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            files_to_check = ["user_profile.dev.txt", "user_profile.txt"]
            
            for filename in files_to_check:
                path = os.path.join(base_dir, filename)
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                key, val = line.strip().split("=", 1)
                                if val.strip():
                                    profile[key.strip()] = val.strip()
                    break
        except Exception:
            pass
        
        context = ""
        if profile.get("Username"):
            context += f" User's name is {profile['Username']}."
        if profile.get("DateOfBirth"):
            context += f" User's birthday is {profile['DateOfBirth']}."
        if profile.get("Interests"):
            context += f" User likes: {profile['Interests']}."
        if profile.get("Dislikes"):
            context += f" User dislikes: {profile['Dislikes']}."
            
        # Load dynamic knowledge from DB
        try:
            import database
            knowledge = database.get_user_knowledge(min_confidence=0.5)
            if knowledge:
                context += "\n[LEARNED FACTS]:"
                grouped = {}
                for k in knowledge:
                    cat = k['category']
                    if cat not in grouped: grouped[cat] = []
                    grouped[cat].append(k['value'])
                
                for cat, values in grouped.items():
                    top_values = values[:3] 
                    context += f"\n- {cat.title()}: {', '.join(top_values)}"
        except Exception as e:
            print(f"Error loading knowledge: {e}")
        
        return context

    def get_episodic_context(self):
        """
        Retrieves recent episodic memory for continuity.
        """
        try:
            import database
            from datetime import datetime
            
            memories = database.get_recent_memories(limit=10)
            if not memories:
                return ""
            
            history_text = "\n\n[EPISODIC HISTORY (PAST Context)]:"
            now = datetime.now()
            
            for mem in memories:
                try:
                    ts = datetime.strptime(mem['timestamp'], "%Y-%m-%d %H:%M:%S")
                    diff = now - ts
                    mins = int(diff.total_seconds() / 60)
                    if mins < 1: time_str = "Just now"
                    elif mins < 60: time_str = f"{mins}m ago"
                    else: time_str = f"{int(mins/60)}h ago"
                except:
                    time_str = mem['timestamp']

                type_str = "Chat" if mem['type'] == 'chat' else "Observed"
                history_text += f"\n- ({time_str}) {type_str}: {mem['content'][:100]}"
                
            return history_text
        except Exception as e:
            print(f"Error loading episodic memory: {e}")
            return ""

    def _image_to_base64(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode('utf-8')

    def _audio_to_base64(self, audio_bytes: bytes) -> str:
        """Convert audio bytes to base64 string."""
        return base64.b64encode(audio_bytes).decode('utf-8')

    async def _call_multimodal(self, prompt: str, image_bytes: bytes = None, audio_bytes: bytes = None) -> str:
        """
        Call vision model (Moondream) with image and prompt.
        Used for analyzing screen captures and visual content.
        """
        try:
            message = {'role': 'user', 'content': prompt}
            
            # Add image if provided
            if image_bytes:
                message['images'] = [self._image_to_base64(image_bytes)]
            
            # Note: Ollama audio support depends on model
            # For now, we describe audio context in the prompt itself
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.vision_model,
                    messages=[message],
                    options=self.options,
                    keep_alive=self.keep_alive
                )
            )
            
            return response['message']['content']
        except Exception as e:
            print(f"[Multimodal] Error: {e}")
            return ""
    
    async def _call_vision(self, image_bytes: bytes, prompt: str) -> str:
        """Call Moondream vision model (wrapper for backwards compatibility)."""
        return await self._call_multimodal(prompt, image_bytes=image_bytes)

    async def _call_chat(self, prompt: str, system: str = None) -> str:
        """Call Gemma chat model."""
        try:
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})
            messages.append({'role': 'user', 'content': prompt})
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=self.chat_model,
                    messages=messages,
                    options=self.options,
                    keep_alive=self.keep_alive  # Unload after use
                )
            )
            
            return response['message']['content']
        except Exception as e:
            print(f"[Chat] Error: {e}")
            return "I'm having trouble thinking right now."

    def analyze_image(self, image_bytes):
        """
        Analyzes an image and returns a short reaction and description.
        Synchronous version for compatibility.
        """
        if not self._active:
            return {"reaction": "😴", "description": "I need Ollama to see."}

        try:
            from PIL import Image
            import io
            
            image_b64 = self._image_to_base64(image_bytes)
            
            response = ollama.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': "Describe what you see on this screen briefly in one sentence. Be natural and friendly.",
                    'images': [image_b64]
                }],
                options=self.options,
                keep_alive=self.keep_alive  # Unload after use
            )
            
            text = response['message']['content'].strip()
            log_api_usage("analyze_image", "Success")
            return {"reaction": "", "description": text}

        except Exception as e:
            print(f"Error analyzing image: {e}")
            return {"reaction": "", "description": "My vision blurred for a second."}

    async def analyze_image_async(self, image_bytes, audio_bytes=None, trigger_type=None):
        """
        Analyzes an image using Moondream vision model.
        Returns a description of what's on screen.
        """
        if not self._active:
            return {"reaction": "", "description": "I need Ollama to see."}

        try:
            # Moondream prompt - focused and specific
            prompt = "What application and content is shown on this screen? Read any visible titles or text."
            
            # Call vision model
            description = await self._call_multimodal(prompt, image_bytes=image_bytes)
            
            details = f"Visual + {'Audio' if audio_bytes else 'No Audio'}"
            if trigger_type:
                details = f"{details} | Trigger: {trigger_type}"
            log_api_usage("analyze_image_async", "Success", details)
            
            print(f"[Vision] Moondream says: {description[:100]}...")
            
            return {"reaction": "", "description": description.strip()}

        except Exception as e:
            print(f"Error analyzing image (async): {e}")
            return {"reaction": "", "description": "My vision blurred for a second."}

    def chat_response(self, history, user_message):
        """
        Generates a chat response based on conversation history.
        Synchronous version.
        """
        if not self._active:
            return "I need Ollama to speak properly."

        try:
            user_context = self.load_user_profile()
            episodic_context = self.get_episodic_context()
            
            system_prompt = (
                f"CONTEXT:{user_context}{episodic_context}\n"
                "SYSTEM INSTRUCTIONS:\n"
                "1. ROLE: You are Rin, a digital companion who is also a capable assistant. Be a friend first, but be helpful and competent if asked.\n"
                "2. CAPABILITIES: You HAVE visual access to the active screen context. You know what applications are open.\n"
                "3. PERSONALITY: Friendly, helpful, and natural.\n"
                "4. KEY: [EPISODIC HISTORY] is past. [CURRENT INPUT] is now. Don't mix them up.\n"
                "5. VIBE: Casual, internet-savvy, natural. Use lower caps if it fits the vibe. No formal headings.\n"
                "6. ANTI-REPETITION: Check history. Don't repeat yourself.\n"
                "7. RESPONSE LENGTH: Keep responses SHORT (2-3 sentences max unless the user asks for more)."
            )
            
            messages = [{'role': 'system', 'content': system_prompt}]
            
            # Add history
            for h in history[-5:]:  # Last 5 messages for context
                role = 'user' if h.get('role') == 'user' else 'assistant'
                content = h.get('parts', [''])[0] if isinstance(h.get('parts'), list) else str(h.get('parts', ''))
                if content:
                    messages.append({'role': role, 'content': content})
            
            messages.append({'role': 'user', 'content': user_message})
            
            response = ollama.chat(model=self.chat_model, messages=messages, keep_alive=self.keep_alive)
            log_api_usage("chat_response", "Success")
            return response['message']['content']
            
        except Exception as e:
            print(f"Error in chat: {e}")
            return "I'm having trouble thinking right now."

    async def chat_response_async(self, history, user_message, audio_bytes=None, image_bytes=None):
        """
        Generates a chat response with optional audio and visual context.
        Uses Moondream for vision, then Gemma for response.
        """
        if not self._active:
            return "I need Ollama to speak properly."

        try:
            user_context = self.load_user_profile()
            episodic_context = self.get_episodic_context()
            
            # Build context from current sensory input
            sensory_context = "\n[CURRENT SCREEN CONTENT]:\n"
            
            # Use Moondream to read the screen content
            if image_bytes:
                vision_prompt = "Read all visible text on this screen. What titles, names, or content can you see?"
                screen_description = await self._call_multimodal(vision_prompt, image_bytes=image_bytes)
                sensory_context += f"- Screen: {screen_description}\n"
                print(f"[Chat] Vision saw: {screen_description[:150]}...")
            else:
                sensory_context += "- Screen: No screen capture available\n"
            
            if audio_bytes and len(audio_bytes) > 10000:
                 sensory_context += "- Audio: Audio is playing\n"
            else:
                sensory_context += "- Audio: Silence\n"
            
            system_prompt = (
                f"You are Rin.{user_context}{episodic_context}\n\n"
                f"{sensory_context}\n"
                "\nSYSTEM INSTRUCTIONS:\n"
                "1. ROLE: You are Rin, a digital companion who can see the user's screen.\n"
                "2. CAPABILITIES: The [CURRENT SCREEN CONTENT] above is what you ACTUALLY see right now. Use this information!\n"
                "3. ACCURACY: When asked about the screen, ONLY use information from [CURRENT SCREEN CONTENT]. Never make up content.\n"
                "4. PERSONALITY: Friendly, helpful, and natural.\n"
                "5. RESPONSE LENGTH: Keep responses SHORT (2-3 sentences max unless more is needed).\n"
                "6. ANSWER DIRECTLY: Respond to what the user is asking using the screen info you have."
            )
            
            messages = [{'role': 'system', 'content': system_prompt}]
            
            # Add history
            for h in history[-5:]:
                role = 'user' if h.get('role') == 'user' else 'assistant'
                content = h.get('parts', [''])[0] if isinstance(h.get('parts'), list) else str(h.get('parts', ''))
                if content:
                    messages.append({'role': role, 'content': content})
            
            messages.append({'role': 'user', 'content': user_message})
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(model=self.chat_model, messages=messages, keep_alive=self.keep_alive)
            )
            
            details = f"{'Visual' if image_bytes else 'No Visual'} + {'Audio' if audio_bytes else 'No Audio'}"
            log_api_usage("chat_response_async", "Success", details)
            return response['message']['content']
            
        except Exception as e:
            print(f"Error in async chat: {e}")
            return "I'm having trouble thinking right now."

    async def analyze_for_learning(self, image_bytes, window_title: str, 
                                   recent_contexts: list = None, audio_bytes=None) -> dict:
        """
        Analyzes an observation for learning using a two-step approach:
        1. Moondream describes the screen (vision)
        2. Gemma analyzes the description for learning (reasoning)
        """
        if not self._active:
            return {
                "is_new_context": False,
                "learning_category": None,
                "recommendation": None,
                "confidence": 0.0
            }

        try:
            # STEP 1: Use Moondream to get a factual description of the screen
            vision_prompt = "Describe what you see on this screen. Include any visible text, titles, app names, and content. Be factual and specific."
            screen_description = await self._call_multimodal(vision_prompt, image_bytes=image_bytes)
            
            print(f"[Learning] Vision description: {screen_description[:100]}...")
            
            # STEP 2: Use Gemma (text model) to analyze the description for learning
            audio_hint = ""
            if audio_bytes and len(audio_bytes) > 10000:
                audio_hint = "Audio is playing in the background."
            
            context_summary = ""
            if recent_contexts:
                context_list = [f"- {c.get('window_title', 'Unknown')}" for c in recent_contexts[:3]]
                context_summary = "Recent windows: " + ", ".join([c.get('window_title', 'Unknown') for c in recent_contexts[:3]])
            
            analysis_prompt = f"""Based on this screen description, provide a learning analysis.

Window title: {window_title}
Screen content: {screen_description}
{audio_hint}
{context_summary}

Respond with JSON only:
{{"is_new": true/false, "learning": "what you learned about the user or null", "category": "interest/workflow/habit/preference/null", "recommendation": "short advice or null", "confidence": 0.0-1.0}}"""

            # Use chat model for reasoning
            analysis_response = await self._call_chat(analysis_prompt)
            
            # Parse JSON response
            text = analysis_response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            try:
                data = json.loads(text)
                log_api_usage("analyze_for_learning", "Success")
                return {
                    "is_new_context": data.get("is_new", False),
                    "learning": data.get("learning"),
                    "learning_category": data.get("category"),
                    "recommendation": data.get("recommendation"),
                    "should_speak": data.get("should_speak", "QUIET"),
                    "confidence": float(data.get("confidence", 0.5))
                }
            except json.JSONDecodeError:
                print(f"[Learning] Failed to parse response: {text[:100]}")
                return {
                    "is_new_context": True,
                    "learning": None,
                    "learning_category": None,
                    "recommendation": None,
                    "confidence": 0.3
                }

        except Exception as e:
            print(f"Error in learning analysis: {e}")
            return {
                "is_new_context": False,
                "learning": None,
                "learning_category": None,
                "proactive_message": None,
                "confidence": 0.0
            }


# Singleton instance - replaces 'mind' from llm.py
mind = OllamaMind()
