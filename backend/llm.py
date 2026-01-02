import google.generativeai as genai
import os
import time

# Attempt to configure from environment or files
API_KEY = os.environ.get("GEMINI_API_KEY")

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

class RinMind:
    def __init__(self):
        self.model = None
        if API_KEY:
            # Use the latest vision-capable model
            self.model = genai.GenerativeModel('gemini-flash-latest')
        
    def is_active(self):
        return self.model is not None


    def load_user_profile(self):
        """Reads user_profile.txt (or .dev.txt) and returns a context string."""
        profile = {}
        base_dir = os.path.join(os.path.dirname(__file__), "..")
        files_to_check = ["user_profile.dev.txt", "user_profile.txt"]
        
        try:
            for filename in files_to_check:
                path = os.path.join(base_dir, filename)
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                key, val = line.strip().split("=", 1)
                                if val.strip():
                                    profile[key.strip()] = val.strip()
                    # If we found and loaded a file (even if empty keys), stop looking
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
            return {"reaction": "", "description": text}

        except Exception as e:
            import traceback
            log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "error.log")
            with open(log_path, "a") as f:
                f.write(f"\n[{time.ctime()}] Image Error: {str(e)}\n")
                f.write(traceback.format_exc())
            print(f"Error analyzing image: {e}")
            return {"reaction": "", "description": "My vision blurred for a second."}

    async def analyze_image_async(self, image_bytes):
        """
        Analyzes an image and returns a short reaction and description (Async).
        Returns: { "reaction": "Emoji", "description": "Text" }
        """
        if not self.model:
            return {"reaction": "😴", "description": "I need a GEMINI_API_KEY to see."}

        try:
            # Prepare image for Gemini (assuming BytesIO or similar)
            from PIL import Image
            import io
            # Image.open is fast/lazy, but if it blocks we'd wrap it. Usually fine.
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
            
            # Async generation call
            response = await self.model.generate_content_async([prompt, image])
            text = response.text.strip()
            
            return {"reaction": "", "description": text}

        except Exception as e:
            import traceback
            log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "error.log")
            # We can leave sync file I/O for error logging for now or make it async later
            # For simplicity in this error path, sync write is acceptable/safe enough
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
            # Gemini Python SDK handles history statefully, but here we pass 'history' list manually.
            # We'll inject context into the last message or system prompt if we controlled the session better.
            # For this stateless pass-through:
            
            user_context = self.load_user_profile()
            system_prompt = f"System: You are Rin, a devoted and knowledgeable assistant of the user's digital world.{user_context} You are gentle, thoughtful, and deeply loyal. Speak clearly and warmly. Be concise."
            
            # Prepend system context to the latest message for context
            extended_message = f"{system_prompt}\nUser: {user_message}"
            
            chat = self.model.start_chat(history=history)
            response = chat.send_message(extended_message)
            return response.text
        except Exception as e:
            print(f"Error in chat: {e}")
            return "I'm having trouble thinking right now."

# Singleton instance
mind = RinMind()
