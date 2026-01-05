"""
Knowledge Engine for Rin's learning system.
Uses Gemini to extract knowledge from observations and build understanding of the user.
"""

import hashlib
import database
from typing import Optional
from datetime import datetime
from logger import log_activity


class KnowledgeEngine:
    """
    Extracts and manages knowledge about the user.
    Uses Gemini to analyze observations and build understanding.
    """
    
    def __init__(self):
        self._last_analysis = None
        self._analysis_interval = 60  # Seconds between deep analyses
    
    def process_observation(self, window_title: str, app_name: str, 
                           app_category: str, description: str) -> dict:
        """
        Process an observation and extract learnable knowledge.
        Called after Gemini analyzes a screen.
        
        Returns: { "learned": bool, "new_context": bool, "insight": str|None }
        """
        result = {
            "learned": False,
            "new_context": False,
            "insight": None
        }
        
        # Generate context hash
        context_hash = self._hash_context(window_title, app_name)
        
        # Check if we've seen this context before
        existing = database.find_similar_context(window_title, app_name)
        
        if existing:
            # Update occurrence count
            database.store_context_embedding(
                context_hash=context_hash,
                window_title=window_title,
                app_name=app_name,
                app_category=app_category,
                description=description
            )
        else:
            # New context - store it
            database.store_context_embedding(
                context_hash=context_hash,
                window_title=window_title,
                app_name=app_name,
                app_category=app_category,
                description=description
            )
            result["new_context"] = True
        
        # Extract knowledge from the observation
        knowledge_extracted = self._extract_knowledge(
            window_title, app_name, app_category, description
        )
        
        if knowledge_extracted:
            result["learned"] = True
        
        return result
    
    async def process_observation_with_gemini(self, image_bytes, window_title: str,
                                               app_name: str, app_category: str,
                                               audio_bytes=None) -> dict:
        """
        Process an observation using Gemini for intelligent learning.
        This is the Phase 2B vision-based approach with optional audio.
        
        Returns: { "learned": bool, "new_context": bool, "insight": str|None, "proactive": str|None }
        """
        from llm import mind
        
        result = {
            "learned": False,
            "new_context": False,
            "insight": None,
            "proactive": None
        }
        
        # Get recent contexts for comparison
        recent_contexts = self._get_recent_contexts(limit=5)
        
        # Ask Gemini to analyze this observation for learning (with optional audio)
        learning_result = await mind.analyze_for_learning(
            image_bytes=image_bytes,
            window_title=window_title,
            recent_contexts=recent_contexts,
            audio_bytes=audio_bytes
        )
        
        # Process Gemini's learning response
        if learning_result.get("is_new_context"):
            result["new_context"] = True
            
            # Store context with Gemini's understanding
            context_hash = self._hash_context(window_title, app_name)
            database.store_context_embedding(
                context_hash=context_hash,
                window_title=window_title,
                app_name=app_name,
                app_category=app_category,
                description=learning_result.get("learning") or ""
            )
        
        # Store any learning Gemini extracted
        if learning_result.get("learning") and learning_result.get("learning_category"):
            category = learning_result["learning_category"]
            learning = learning_result["learning"]
            confidence = learning_result.get("confidence", 0.5)
            
            # Map category to our schema
            if category in ["interest", "hobby"]:
                database.learn_about_user(
                    category="interest",
                    key=learning[:30],  # Use first 30 chars as key
                    value=learning,
                    confidence=confidence
                )
            elif category in ["workflow", "habit"]:
                database.learn_about_user(
                    category="workflow",
                    key=category,
                    value=learning,
                    confidence=confidence
                )
            elif category == "preference":
                database.learn_about_user(
                    category="preference",
                    key=learning[:30],
                    value=learning,
                    confidence=confidence
                )
            
            result["learned"] = True
            result["insight"] = learning
            print(f"[Knowledge] Gemini learned: {learning}")
            log_activity("LEARNING", f"Learned {category}: {learning}")
        
        # Handle proactive insights from Gemini
        # Handle Recommendations (High Priority - The ONLY thing we listen to now)
        if learning_result.get("recommendation"):
            rec_msg = learning_result["recommendation"]
            confidence = learning_result.get("confidence", 0.8)
            
            # Store (DISABLED to prevent re-sending as insight)
            # database.add_rin_insight(
            #     insight_type="recommendation",
            #     content=rec_msg,
            #     context={"window_title": window_title, "app": app_name},
            #     relevance_score=confidence
            # )
            result["recommendation"] = rec_msg
            print(f"[Knowledge] Gemini recommendation: {rec_msg}")
        
        return result
    
    def _get_recent_contexts(self, limit: int = 5) -> list:
        """Get recently seen contexts for comparison."""
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT window_title, app_name, app_category, description
            FROM context_embeddings
            ORDER BY last_seen DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def _hash_context(self, window_title: str, app_name: str) -> str:
        """Generate a hash for a context."""
        content = f"{app_name}:{window_title}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _extract_knowledge(self, window_title: str, app_name: str, 
                          app_category: str, description: str) -> bool:
        """Extract learnable knowledge from an observation."""
        learned_something = False
        
        # Learn about interests from window titles
        interests = self._detect_interests(window_title, description)
        for interest in interests:
            database.learn_about_user(
                category="interest",
                key=interest["key"],
                value=interest["value"],
                confidence=interest.get("confidence", 0.5)
            )
            learned_something = True
        
        # Learn about workflows from app category patterns
        if app_category:
            database.learn_about_user(
                category="app_usage",
                key=app_category,
                value=app_name,
                confidence=0.3  # Low initial confidence, grows with repetition
            )
            learned_something = True
        
        return learned_something
    
    def _detect_interests(self, window_title: str, description: str) -> list:
        """Detect user interests from window title and description."""
        interests = []
        title_lower = window_title.lower() if window_title else ""
        desc_lower = description.lower() if description else ""
        
        # Game development
        if any(x in title_lower for x in ["unreal", "unity", "godot", "game dev"]):
            interests.append({"key": "game_development", "value": "unreal/unity/godot", "confidence": 0.7})
        
        # Programming languages/frameworks
        if any(x in title_lower for x in ["python", "javascript", "typescript", "react", "next.js"]):
            interests.append({"key": "programming", "value": "web development", "confidence": 0.6})
        
        # Shader/graphics
        if any(x in title_lower for x in ["shader", "glsl", "hlsl", "graphics"]):
            interests.append({"key": "graphics_programming", "value": "shaders", "confidence": 0.7})
        
        # Gaming
        if any(x in title_lower for x in ["steam", "discord", "valorant", "genshin"]):
            interests.append({"key": "gaming", "value": "games", "confidence": 0.5})
        
        # AI/ML
        if any(x in title_lower for x in ["gemini", "ollama", "ai", "llm", "machine learning"]):
            interests.append({"key": "ai_ml", "value": "AI/ML development", "confidence": 0.6})
        
        return interests
    
    def generate_proactive_insight(self) -> Optional[dict]:
        """
        Generate a proactive insight based on accumulated knowledge.
        Called periodically to see if Rin has something to share.
        
        Returns: { "type": str, "message": str, "id": int } or None
        """
        # First, check for unshared insights
        unshared = database.get_unshared_insights(min_relevance=0.6, limit=1)
        if unshared:
            return None # SILENCED INSIGHTS
            # insight = unshared[0]
            # return {
            #     "type": insight["insight_type"],
            #     "message": insight["content"],
            #     "id": insight["id"]
            # }
        
        # Generate new insights from knowledge
        insight = self._generate_insight_from_knowledge()
        if insight:
            # Check if we already have this specific insight (shared or unshared) to avoid spam
            existing = database.get_db_connection().execute(
                "SELECT id FROM rin_insights WHERE content = ? AND created_at > date('now', '-1 day')",
                (insight["message"],)
            ).fetchone()
            
            if existing:
                return None

            insight_id = database.add_rin_insight(
                insight_type=insight["type"],
                content=insight["message"],
                context=insight.get("context"),
                relevance_score=insight.get("relevance", 0.6)
            )
            # return {
            #     "type": insight["type"],
            #     "message": insight["message"],
            #     "id": insight_id
            # }
            return None
        
        return None
    
    def _generate_insight_from_knowledge(self) -> Optional[dict]:
        """Generate an insight from accumulated user knowledge."""
        knowledge = database.get_user_knowledge(min_confidence=0.6)
        
        if not knowledge:
            return None
        
        # Check for high-confidence interests
        interests = [k for k in knowledge if k["category"] == "interest"]
        if interests:
            top_interest = interests[0]
            if top_interest["evidence_count"] >= 5:  # Only share well-established insights
                return {
                    "type": "proactive",  # Changed from 'observation' so frontend displays it
                    "message": f"I've noticed you're quite interested in {top_interest['value']}.",
                    "context": {"knowledge_id": top_interest["id"]},
                    "relevance": 0.7
                }
        
        # Check for app usage patterns
        app_usage = [k for k in knowledge if k["category"] == "app_usage"]
        if len(app_usage) >= 3:
            categories = [k["key"] for k in app_usage[:3]]
            return {
                "type": "proactive",
                "message": f"Your main focus areas seem to be: {', '.join(categories)}.",
                "context": {"categories": categories},
                "relevance": 0.6
            }
        
        return None
    
    def get_context_for_llm(self) -> str:
        """
        Generate a context string about the user for LLM prompts.
        This helps Rin personalize her responses.
        """
        parts = []
        
        # Get high-confidence knowledge
        knowledge = database.get_user_knowledge(min_confidence=0.5)
        
        # Interests
        interests = [k for k in knowledge if k["category"] == "interest"]
        if interests:
            interest_values = [k["value"] for k in interests[:3]]
            parts.append(f"User interests: {', '.join(interest_values)}")
        
        # App usage patterns
        app_usage = [k for k in knowledge if k["category"] == "app_usage"]
        if app_usage:
            categories = list(set(k["key"] for k in app_usage[:5]))
            parts.append(f"User focuses on: {', '.join(categories)}")
        
        # Knowledge summary
        summary = database.get_knowledge_summary()
        if summary["contexts_learned"]["unique"] > 0:
            parts.append(f"Contexts observed: {summary['contexts_learned']['unique']}")
        
        return " | ".join(parts) if parts else ""
    
    def mark_insight_delivered(self, insight_id: int, feedback: str = None):
        """Mark an insight as delivered to the user."""
        database.mark_insight_shared(insight_id, feedback)
    
    def organize_knowledge(self):
        """
        Organize and clean up knowledge during idle time.
        Called during deep thinking mode.
        """
        try:
            conn = database.get_db_connection()
            c = conn.cursor()
            
            # 1. Merge duplicate knowledge entries
            # Find entries with same category and similar keys
            c.execute("""
                SELECT id, category, key, value, confidence, evidence_count
                FROM user_knowledge
                ORDER BY category, key, confidence DESC
            """)
            rows = c.fetchall()
            
            seen = {}
            to_delete = []
            
            for row in rows:
                entry_key = f"{row['category']}:{row['key']}"
                if entry_key in seen:
                    # Merge into the first (higher confidence) entry
                    master_id = seen[entry_key]
                    c.execute("""
                        UPDATE user_knowledge 
                        SET evidence_count = evidence_count + ?,
                            confidence = MIN(1.0, confidence + 0.05)
                        WHERE id = ?
                    """, (row['evidence_count'], master_id))
                    to_delete.append(row['id'])
                else:
                    seen[entry_key] = row['id']
            
            # Delete duplicates
            for row_id in to_delete:
                c.execute("DELETE FROM user_knowledge WHERE id = ?", (row_id,))
            
            # 2. Archive very old, low-confidence entries
            c.execute("""
                DELETE FROM user_knowledge
                WHERE confidence < 0.2 
                AND updated_at < date('now', '-30 days')
            """)
            archived = c.rowcount
            
            # 3. Clean up old context embeddings (keep only last 1000)
            c.execute("""
                DELETE FROM context_embeddings
                WHERE id NOT IN (
                    SELECT id FROM context_embeddings
                    ORDER BY last_seen DESC
                    LIMIT 1000
                )
            """)
            
            conn.commit()
            conn.close()
            
            if to_delete or archived > 0:
                print(f"[Knowledge] Organized: merged {len(to_delete)} duplicates, archived {archived} old entries")
                
        except Exception as e:
            print(f"[Knowledge] Organization error: {e}")
    
    def apply_confidence_decay(self):
        """
        Apply confidence decay to knowledge based on age.
        Implements: confidence = confidence * (0.95 ^ weeks_since_update)
        Called periodically during deep thinking.
        """
        try:
            conn = database.get_db_connection()
            c = conn.cursor()
            
            # Only decay entries that haven't been decayed in the last week
            c.execute("""
                UPDATE user_knowledge
                SET confidence = confidence * 0.95,
                    updated_at = CURRENT_TIMESTAMP
                WHERE updated_at < date('now', '-7 days')
                AND confidence > 0.1
            """)
            
            decayed = c.rowcount
            conn.commit()
            conn.close()
            
            if decayed > 0:
                print(f"[Knowledge] Applied decay to {decayed} knowledge entries")
                
        except Exception as e:
            print(f"[Knowledge] Decay error: {e}")


# Singleton instance
knowledge_engine = KnowledgeEngine()
