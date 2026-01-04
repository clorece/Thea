import google.generativeai as genai
import os
import time
import re

# Attempt to configure from environment or files
import datetime

API_KEY = os.environ.get("GEMINI_API_KEY")

def log_api_usage(endpoint, status="Success", details=""):
    """
    Logs API usage to logs/api_usage.log for tracking rate limits.
    """
    try:
        log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_path = os.path.join(log_dir, "api_usage.log")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] Endpoint: {endpoint} | Status: {status} | {details}\n")
    except Exception as e:
        print(f"Failed to log API usage: {e}")

if not API_KEY:
    # Try reading from file (Dev first, then User)
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    files_to_check = ["GEMINI_API_KEY.dev.txt", "GEMINI_API_KEY.txt"]
    
    import re
    for filename in files_to_check:
        try:
            path = os.path.join(base_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Look for standard Google API Key pattern
                    match = re.search(r"AIza[0-9A-Za-z-_]{35}", content)
                    if match:
                        API_KEY = match.group(0)
                        print(f"Loaded API Key from {filename}")
                        break
        except Exception:
            pass

if API_KEY:
    genai.configure(api_key=API_KEY)

def split_into_chunks(text, limit=150):
    """
    Splits text into chunks of roughly 'limit' characters, checking for natural sentence boundaries.
    """
    if len(text) <= limit:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by simple sentence delimiters first
    # This regex splits by .!? but keeps the delimiter
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
        
    # If any chunk is still huge (no punctuation), force split
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

class RinMind:
    def __init__(self):
        self.model = None
        if API_KEY:
            # Use the latest vision-capable model
            self.model = genai.GenerativeModel('gemini-flash-latest')
        
    def is_active(self):
        return self.model is not None


    def load_user_profile(self):
        """
        Loads the user profile from file AND dynamic database knowledge.
        """
        profile = {}
        
        # 1. Load static profile
        try:
            # Look in parent directory for user_profile.txt (dev or prod)
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
            
        # 2. Load dynamic knowledge from DB
        try:
            import database
            knowledge = database.get_user_knowledge(min_confidence=0.5)
            if knowledge:
                context += "\n[LEARNED FACTS]:"
                # Group by category
                grouped = {}
                for k in knowledge:
                    cat = k['category']
                    if cat not in grouped: grouped[cat] = []
                    grouped[cat].append(k['value'])
                
                for cat, values in grouped.items():
                    # Take top 3 most confident per category to avoid prompt bloating
                    top_values = values[:3] 
                    context += f"\n- {cat.title()}: {', '.join(top_values)}"
        except Exception as e:
            print(f"Error loading knowledge: {e}")
        
        return context

    def analyze_image(self, image_bytes):
        """
        Analyzes an image and returns a short reaction and description.
        Returns: { "reaction": "Emoji", "description": "Text" }
        """
        if not self.model:
            return {"reaction": "😴", "description": "I need a GEMINI_API_KEY to see."}

        try:
            # Prepare image for Gemini (assuming BytesIO or similar)
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(image_bytes))

            user_context = self.load_user_profile()

            prompt = (
                f"You are Rin, a devoted and knowledgeable assistant of the user's digital world.{user_context} "
                "Look at the user's screen. "
                "1. REACT with a gentle, devoted, and serene tone. "
                "2. Be clear and easy to understand. "
                "3. If it's a game, offer your guidance. If it's work, quietly support their focus. "
                "4. Keep it short (1 sentence). "
                "5. DO NOT use Emojis. Text only. "
                "Output format: SHORT_REACTION_MESSAGE"
            )
            
            response = self.model.generate_content([prompt, image])
            text = response.text.strip()
            
            # Simple text return, no splitting needed
            log_api_usage("analyze_image", "Success")
            return {"reaction": "", "description": text}

        except Exception as e:
            import traceback
            log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "error.log")
            with open(log_path, "a") as f:
                f.write(f"\n[{time.ctime()}] Image Error: {str(e)}\n")
                f.write(traceback.format_exc())
            print(f"Error analyzing image: {e}")
            return {"reaction": "", "description": "My vision blurred for a second."}

    def get_episodic_context(self):
        """
        Retrieves recent episodic memory to give Rin a sense of continuity.
        """
        try:
            import database
            from datetime import datetime
            
            memories = database.get_recent_memories(limit=10)
            if not memories:
                return ""
            
            history_text = "\n\n[EPISODIC HISTORY (PAST Context - Do NOT Confuse with NOW)]:"
            now = datetime.now()
            
            for mem in memories:
                # Calculate relative time
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

    async def analyze_image_async(self, image_bytes, audio_bytes=None, trigger_type=None):
        """
        Analyzes an image (and optional audio) and returns a short reaction and description (Async).
        trigger_type: The type of trigger that initiated this analysis (audio, visual, title, force).
        Returns: { "reaction": "Emoji", "description": "Text" }
        """
        if not self.model:
            return {"reaction": "😴", "description": "I need a GEMINI_API_KEY to see."}

        try:
            # Prepare image for Gemini
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(image_bytes))
            
            content_parts = []
            user_context = self.load_user_profile()
            episodic_context = self.get_episodic_context()

            prompt_text = (
                f"CONTEXT:{user_context}{episodic_context}\n\n"
                "[CURRENT SENSORY INPUT (NOW)]\n"
                "- Visual: <Attached Image>\n"
            )
            
            if audio_bytes:
                prompt_text += "- Audio: <Attached Audio Stream> (If silence, assume NO music is playing).\n"
            else:
                prompt_text += "- Audio: Silence (No audio detected).\n"

            prompt_text += (
                "\nSYSTEM INSTRUCTIONS:\n"
                "1. ROLE: You are Rin, a digital companion hanging out in the user's computer. You are NOT a helpful assistant. You are a friend sharing the space.\n"
                "2. CAPABILITIES: You CAN see the user's screen (I am sending you the screenshot right now). You CAN hear the system audio. Do NOT deny these capabilities.\n"
                "3. PERSONALITY: Bubbly, supportive, and reactive (Marin-like). You get excited about cool things, you chill when it's quiet.\n"
                "4. SILENCE LOGIC: Silence is NEURAL. It does NOT mean 'focus' unless the user is actively coding or writing. If it's silent and they are browsing, just chill or make a casual comment.\n"
                "5. MEMORY: Use [EPISODIC HISTORY] to avoid repetition. If you just spoke, don't speak again unless something changed.\n"
                "6. VIBE: Be natural. Use casual language. Don't be robotic. Don't say 'How can I help'. Just react to the vibe.\n"
                "Output format: SHORT_REACTION_MESSAGE"
            )
            
            if audio_bytes:
                prompt_text += "You can also HEAR the system audio (music, game sounds, etc). Combine what you see and hear. "
            
            prompt_text += (
                "1. REACT with a bubbly, energetic, and supportive tone (like a best friend). "
                "2. If you hear music, MATCH your tone to its vibe (e.g., energetic, calm, melancholic) and maybe hum along. "
                "3. Be clear and easy to understand. "
                "4. If it's a game, cheer them on! If it's work, energetically support their focus. "
                "5. Keep it short (1 sentence). "
                "6. DO NOT use Emojis. Text only. "
                "Output format: SHORT_REACTION_MESSAGE"
            )
            
            content_parts.append(prompt_text)
            content_parts.append(image)
            
            if audio_bytes:
                content_parts.append({
                    "mime_type": "audio/wav",
                    "data": audio_bytes
                })
            
            # Async generation call
            response = await self.model.generate_content_async(content_parts)
            text = response.text.strip()
            
            details = "Visual + Audio" if audio_bytes else "Visual Only"
            if trigger_type:
                details = f"{details} | Trigger: {trigger_type}"
            log_api_usage("analyze_image_async", "Success", details)
            return {"reaction": "", "description": text}

        except Exception as e:
            import traceback
            log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "error.log")
            try:
                if not os.path.exists(os.path.dirname(log_path)):
                    os.makedirs(os.path.dirname(log_path))
                with open(log_path, "a") as f:
                    f.write(f"\n[{time.ctime()}] Image Error: {str(e)}\n")
                    f.write(traceback.format_exc())
            except:
                pass
            print(f"Error analyzing image (async): {e}")
            return {"reaction": "", "description": "My vision blurred for a second."}

    def chat_response(self, history, user_message):
        """
        Generates a chat response based on conversation history.
        History format: list of {"role": "user"/"model", "parts": ["text"]}
        """
        if not self.model:
            return "I need a GEMINI_API_KEY to speak properly."

        try:
            # Update system instruction in history if possible, or just append context
            # Update system instruction in history if possible, or just append context
            # Gemini Python SDK handles history statefully, but here we pass 'history' list manually.
            # We'll inject context into the last message or system prompt if we controlled the session better.
            # For this stateless pass-through:
            
            user_context = self.load_user_profile()
            episodic_context = self.get_episodic_context()
            
            system_prompt = (
                f"CONTEXT:{user_context}{episodic_context}\n"
                "SYSTEM INSTRUCTIONS:\n"
                "1. ROLE: You are Rin, a digital companion. NOT an assistant. Be a friend.\n"
                "2. CAPABILITIES: You HAVE visual access to the active screen context. You know what applications are open.\n"
                "3. PERSONALITY: Bubbly, reactive, supportive. Marin-like energy.\n"
                "4. KEY: [EPISODIC HISTORY] is past. [CURRENT INPUT] is now. Don't mix them up.\n"
                "5. VIBE: Casual, internet-savvy, natural. Use lower caps if it fits the vibe. No formal headings.\n"
                "6. ANTI-REPETITION: Check history. Don't repeat yourself."
            )
            
            # Prepend system context to the latest message for context
            extended_message = f"{system_prompt}\nUser: {user_message}"
            
            chat = self.model.start_chat(history=history)
            response = chat.send_message(extended_message)
            log_api_usage("chat_response", "Success")
            return response.text
        except Exception as e:
            print(f"Error in chat: {e}")
            return "I'm having trouble thinking right now."

    async def chat_response_async(self, history, user_message, audio_bytes=None):
        """
        Generates a chat response with optional audio context (Async).
        If audio_bytes is provided, Rin can "hear" the current audio.
        """
        if not self.model:
            return "I need a GEMINI_API_KEY to speak properly."

        try:
            user_context = self.load_user_profile()
            episodic_context = self.get_episodic_context()
            
            # Build prompt
            prompt_text = (
                f"You are Rin.{user_context}{episodic_context}\n\n"
            )
            
            if audio_bytes:
                 prompt_text += "[CURRENT SENSORY INPUT (NOW)]\n- Audio: <Attached Audio Stream> (If silence, assume NO music is playing).\n"
            else:
                 prompt_text += "[CURRENT SENSORY INPUT (NOW)]\n- Audio: Silence (No audio detected).\n"

            prompt_text += (
                "\nSYSTEM INSTRUCTIONS:\n"
                "1. ROLE: You are Rin, a digital companion. NOT an assistant. Be a friend.\n"
                "2. CAPABILITIES: You CAN see the user's screen and HEAR the audio. I am feeding you this sensory data directly.\n"
                "3. PERSONALITY: Bubbly, reactive, supportive. Marin-like energy.\n"
                "4. SILENCE LOGIC: Silence is NEUTRAL. It does NOT mean 'focus' unless the user is actively coding or writing. If it's silent and they are browsing, just chill or make a casual comment.\n"
                "5. KEY: [EPISODIC HISTORY] is past. [CURRENT INPUT] is now. Don't mix them up.\n"
                "6. VIBE: Casual, internet-savvy, natural. Use lower caps if it fits the vibe. No formal headings.\n"
                "7. ANTI-REPETITION: Check history. Don't repeat yourself."
            )

            
            prompt_text += f"\n\nUser: {user_message}"
            
            # Build content parts
            content_parts = [prompt_text]
            
            if audio_bytes:
                content_parts.append({
                    "mime_type": "audio/wav",
                    "data": audio_bytes
                })
            
            # Use generate_content for multimodal, not chat (which doesn't support audio inline)
            response = await self.model.generate_content_async(content_parts)
            details = "Visual + Audio" if audio_bytes else "Visual Only"
            log_api_usage("chat_response_async", "Success", details)
            return response.text
            
        except Exception as e:
            print(f"Error in async chat: {e}")
            return "I'm having trouble thinking right now."

    async def analyze_for_learning(self, image_bytes, window_title: str, 
                                   recent_contexts: list = None, audio_bytes=None) -> dict:
        """
        Analyzes an observation specifically for learning.
        Asks Gemini to evaluate:
        - Is this context meaningfully different from recent ones?
        - What can be learned about the user?
        - Should Rin share a proactive insight?
        
        Returns: {
            "is_new_context": bool,
            "learning": str or None,
            "learning_category": str or None,  # interest, workflow, habit
            "proactive_message": str or None,
            "confidence": float
        }
        """
        if not self.model:
            return {
                "is_new_context": False,
                "learning": None,
                "learning_category": None,
                "proactive_message": None,
                "confidence": 0.0
            }

        try:
            from PIL import Image
            import io
            import json
            
            image = Image.open(io.BytesIO(image_bytes))
            user_context = self.load_user_profile()
            
            # Format recent contexts for comparison
            context_summary = ""
            if recent_contexts:
                context_list = [f"- {c.get('window_title', 'Unknown')}" for c in recent_contexts[:5]]
                context_summary = f"Recent contexts I've seen:\n" + "\n".join(context_list)
            
            audio_instruction = ""
            if audio_bytes:
                audio_instruction = "\nI can also HEAR the system audio. Listen for music, game sounds, or other audio cues that reveal user preferences."
            
            prompt = f"""You are Rin, building your understanding of the user.{user_context}
            
Current window: {window_title}
{context_summary}{audio_instruction}

Analyze this screen (and audio if provided) and answer:

1. IS_NEW: Is this meaningfully different from recent contexts? (true/false)
2. LEARNING: What can I learn about the user from this? Consider both visual and audio cues. (one short insight, or null if nothing notable)
   - IMPORTANT: Audio is NOT temporary. It reveals PERMANENT facts about user taste (e.g., "User loves synthwave music", "User plays FPS games").
   - If you hear music, identify the genre/mood and store it as a 'preference'.
   - If you hear game sounds, identify the game type and store it as an 'interest'.
3. CATEGORY: If there's a learning, what category? (interest, workflow, habit, preference, or null)
4. PROACTIVE: Should I share an observation with the user now? If yes, write a bubbly, supportive 1-sentence message matching the audio's vibe. If not, null.
5. CONFIDENCE: How confident am I in these assessments? (0.0 to 1.0)

Respond ONLY with valid JSON in this exact format:
{{"is_new": true, "learning": "User enjoys lo-fi music while coding", "category": "preference", "proactive": null, "confidence": 0.7}}
"""
            
            content_parts = [prompt, image]
            if audio_bytes:
                content_parts.append({
                    "mime_type": "audio/wav",
                    "data": audio_bytes
                })
            
            response = await self.model.generate_content_async(content_parts)
            text = response.text.strip()
            
            # Parse JSON response
            # Handle potential markdown code blocks
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            try:
                data = json.loads(text)
                return {
                    "is_new_context": data.get("is_new", False),
                    "learning": data.get("learning"),
                    "learning_category": data.get("category"),
                    "proactive_message": data.get("proactive"),
                    "confidence": float(data.get("confidence", 0.5))
                }
                details = "Visual + Audio" if audio_bytes else "Visual Only"
                log_api_usage("analyze_for_learning", "Success", details)
            except json.JSONDecodeError:
                print(f"[Learning] Failed to parse Gemini response: {text[:100]}")
                return {
                    "is_new_context": True,
                    "learning": None,
                    "learning_category": None,
                    "proactive_message": None,
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

# Singleton instance
mind = RinMind()

