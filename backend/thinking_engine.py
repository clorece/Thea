"""
Rin's Thinking Engine - Core intelligence orchestration system.

This module transforms Rin from a continuous Gemini-dependent observer into
a local, edge-first intelligence that thinks before speaking and learns
during downtime.

Architecture:
- ObservationBuffer: Accumulates observations before processing
- IdleDetector: Tracks user activity, triggers deep thinking
- SignificanceScorer: Edge-based logic to filter noise
- ThinkingScheduler: Manages thinking cycles and cooldowns
"""

import time
import hashlib
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from logger import log_activity, log_system_change


class ThinkingState(Enum):
    """Rin's current thinking mode."""
    ACTIVE = "active"           # User is active, Rin observes
    THINKING = "thinking"       # Reviewing buffered observations
    DEEP_REFLECTION = "deep"    # User idle, knowledge reorganization
    RESTING = "resting"         # Minimal processing, waiting


@dataclass
class Observation:
    """A single buffered observation."""
    window_title: str
    app_name: str
    app_category: str
    context_hash: str
    timestamp: float
    image_bytes: Optional[bytes] = None
    audio_bytes: Optional[bytes] = None
    description: Optional[str] = None
    significance_score: float = 0.0


@dataclass
class ThinkingCycleResult:
    """Result of a thinking cycle."""
    significant_observations: List[Observation] = field(default_factory=list)
    gemini_recommendations: List[str] = field(default_factory=list)
    knowledge_updates: int = 0
    should_notify: bool = False
    notification_content: Optional[str] = None


@dataclass
class SavedThought:
    """A thought saved for later (when user asks 'what are you thinking?')."""
    content: str
    reason: str  # Why it was saved (e.g., "User in flow", "Not urgent")
    timestamp: float = field(default_factory=time.time)
    context: Optional[str] = None  # Window title when thought occurred


class ObservationBuffer:
    """
    Ring buffer for accumulating observations before processing.
    Prevents immediate Gemini calls, allows significance filtering.
    """
    
    def __init__(self, max_size: int = 10):
        self.buffer: deque[Observation] = deque(maxlen=max_size)
        self.context_hashes: set = set()  # For deduplication
        self._recent_hash_ttl = 30  # 30 seconds - allow re-observation of same context
        self._hash_timestamps: Dict[str, float] = {}
    
    def add(self, obs: Observation) -> bool:
        """
        Add observation to buffer.
        Returns True if added, False if deduplicated.
        """
        # Clean up old hashes
        self._cleanup_old_hashes()
        
        # Check for duplicate context
        if obs.context_hash in self.context_hashes:
            return False
        
        self.buffer.append(obs)
        self.context_hashes.add(obs.context_hash)
        self._hash_timestamps[obs.context_hash] = time.time()
        return True
    
    def get_all(self) -> List[Observation]:
        """Get all buffered observations."""
        return list(self.buffer)
    
    def get_recent(self, seconds: float = 60) -> List[Observation]:
        """Get observations from the last N seconds."""
        cutoff = time.time() - seconds
        return [o for o in self.buffer if o.timestamp >= cutoff]
    
    def clear(self):
        """Clear the buffer after processing."""
        self.buffer.clear()
        # Don't clear hashes - keep for continued deduplication
    
    def _cleanup_old_hashes(self):
        """Remove old context hashes to prevent memory bloat."""
        cutoff = time.time() - self._recent_hash_ttl
        expired = [h for h, t in self._hash_timestamps.items() if t < cutoff]
        for h in expired:
            self.context_hashes.discard(h)
            del self._hash_timestamps[h]
    
    def __len__(self) -> int:
        return len(self.buffer)


class IdleDetector:
    """
    Tracks user activity to determine when to enter deep thinking mode.
    """
    
    def __init__(self, idle_threshold_seconds: float = 120):  # 2 minutes
        self.idle_threshold = idle_threshold_seconds
        self.last_activity_time: float = time.time()
        self._activity_history: deque = deque(maxlen=100)
    
    def record_activity(self, window_title: str = ""):
        """Record user activity."""
        now = time.time()
        self._activity_history.append({
            "timestamp": now,
            "window": window_title
        })
        self.last_activity_time = now
    
    def is_idle(self) -> bool:
        """Check if user is considered idle."""
        return time.time() - self.last_activity_time > self.idle_threshold
    
    def get_idle_duration(self) -> float:
        """Get how long user has been idle in seconds."""
        return max(0, time.time() - self.last_activity_time)
    
    def get_activity_intensity(self, window_seconds: float = 60) -> float:
        """
        Calculate activity intensity (0-1) based on recent activity.
        Higher = more rapid context switching.
        """
        cutoff = time.time() - window_seconds
        recent = [a for a in self._activity_history if a["timestamp"] >= cutoff]
        
        if len(recent) < 2:
            return 0.0
        
        # Count unique windows
        unique_windows = len(set(a["window"] for a in recent if a["window"]))
        # Normalize: 10+ unique windows in a minute = intensity 1.0
        return min(1.0, unique_windows / 10)


class SignificanceScorer:
    """
    Edge-based significance scoring for observations.
    Determines what's worth sending to Gemini.
    """
    
    def __init__(self):
        self._seen_contexts: Dict[str, int] = {}  # hash -> count
        self._last_significant_time: float = 0
        self._category_weights = {
            "development": 0.6,
            "work": 0.5,
            "communication": 0.4,
            "media": 0.3,
            "other": 0.2
        }
    
    def score(self, obs: Observation, 
              previous_obs: Optional[Observation] = None,
              activity_intensity: float = 0.5) -> float:
        """
        Calculate significance score (0-1) for an observation.
        Higher = more significant, more likely to need Gemini.
        """
        score = 0.0
        
        # 1. Novelty: Have we seen this context before?
        seen_count = self._seen_contexts.get(obs.context_hash, 0)
        novelty = 1.0 / (1 + seen_count * 0.5)  # Decay with repeats
        score += novelty * 0.3
        
        # 2. Category weight
        category_weight = self._category_weights.get(obs.app_category.lower(), 0.2)
        score += category_weight * 0.2
        
        # 3. Context change (if we have previous)
        if previous_obs:
            if obs.app_name != previous_obs.app_name:
                score += 0.2  # App switch is significant
            if obs.app_category != previous_obs.app_category:
                score += 0.15  # Category switch more significant
        else:
            score += 0.1  # First observation gets some points
        
        # 4. Deep focus bonus (low activity intensity = focused)
        focus_bonus = (1 - activity_intensity) * 0.15
        score += focus_bonus
        
        # 5. Time since last significant observation
        time_since = time.time() - self._last_significant_time
        if time_since > 300:  # 5 minutes
            score += 0.1  # Been quiet too long, worth checking
        
        # Update tracking
        self._seen_contexts[obs.context_hash] = seen_count + 1
        
        return min(1.0, score)
    
    def mark_significant(self):
        """Mark that a significant observation was processed."""
        self._last_significant_time = time.time()
    
    def reset_context(self, context_hash: str):
        """Reset seen count for a context (e.g., after major change)."""
        self._seen_contexts.pop(context_hash, None)


class ThinkingEngine:
    """
    Main orchestrator for Rin's thinking system.
    Manages state, buffers, and coordinates with other engines.
    """
    
    def __init__(self):
        self.state = ThinkingState.ACTIVE
        self.observation_buffer = ObservationBuffer(max_size=10)
        self.idle_detector = IdleDetector(idle_threshold_seconds=120)
        self.significance_scorer = SignificanceScorer()
        
        # Timing configuration
        self.thinking_cycle_interval = 10  # seconds (was 45) - faster reactions
        self.notification_cooldown = 15    # seconds (was 30) - more bubbly
        
        # Two-tier decision thresholds
        self.significance_threshold = 0.4  # Minimum for any processing
        self.gemini_threshold = 0.4        # Same as significance - let Gemini decide more
        
        # State tracking
        self._last_thinking_cycle = 0
        self._last_notification_time = 0
        self._pending_thoughts: List[str] = []
        self._saved_thoughts: List[SavedThought] = []  # Deferred notifications
        self._cycle_count = 0
        self._gemini_call_count = 0
        
        # Statistics
        self._stats = {
            "observations_total": 0,
            "observations_buffered": 0,
            "observations_deduplicated": 0,
            "significant_count": 0,
            "gemini_consulted": 0,
            "edge_filtered": 0,
            "thoughts_saved": 0,
            "notifications_sent": 0
        }
    
    def buffer_observation(self, window_title: str, app_name: str,
                           app_category: str, image_bytes: Optional[bytes] = None,
                           audio_bytes: Optional[bytes] = None) -> bool:
        """
        Buffer a new observation for later processing.
        Returns True if buffered, False if deduplicated.
        """
        # Create context hash
        context_hash = self._hash_context(window_title, app_name)
        
        obs = Observation(
            window_title=window_title,
            app_name=app_name,
            app_category=app_category,
            context_hash=context_hash,
            timestamp=time.time(),
            image_bytes=image_bytes,
            audio_bytes=audio_bytes
        )
        
        # Record activity for idle detection
        self.idle_detector.record_activity(window_title)
        
        # Add to buffer
        self._stats["observations_total"] += 1
        if self.observation_buffer.add(obs):
            self._stats["observations_buffered"] += 1
            return True
        else:
            self._stats["observations_deduplicated"] += 1
            return False
    
    def should_run_thinking_cycle(self) -> bool:
        """Check if it's time for a thinking cycle."""
        return time.time() - self._last_thinking_cycle >= self.thinking_cycle_interval
    
    def can_notify(self) -> bool:
        """Check if notification cooldown has passed."""
        return time.time() - self._last_notification_time >= self.notification_cooldown
    
    def update_state(self) -> ThinkingState:
        """
        Update Rin's thinking state based on current conditions.
        Should be called periodically.
        """
        previous_state = self.state
        
        if self.idle_detector.is_idle():
            idle_duration = self.idle_detector.get_idle_duration()
            if idle_duration > 300:  # 5 minutes
                self.state = ThinkingState.RESTING
            else:
                self.state = ThinkingState.DEEP_REFLECTION
        elif len(self.observation_buffer) > 0 and self.should_run_thinking_cycle():
            self.state = ThinkingState.THINKING
        else:
            self.state = ThinkingState.ACTIVE
        
        # Log state transitions
        if self.state != previous_state:
            print(f"[Thinking] State: {previous_state.value} → {self.state.value}")
            log_activity("THINKING", f"State: {previous_state.value} → {self.state.value}")
            log_system_change("THINKING_STATE", "changed", f"{previous_state.value} -> {self.state.value}")
        
        return self.state
    
    async def run_thinking_cycle(self) -> ThinkingCycleResult:
        """
        Run a thinking cycle: evaluate buffered observations,
        determine significance, optionally call Gemini.
        """
        self._last_thinking_cycle = time.time()
        self._cycle_count += 1
        
        result = ThinkingCycleResult()
        observations = self.observation_buffer.get_all()
        
        if not observations:
            return result
        
        # Score each observation
        activity_intensity = self.idle_detector.get_activity_intensity()
        previous_obs = None
        
        for obs in observations:
            score = self.significance_scorer.score(
                obs, previous_obs, activity_intensity
            )
            obs.significance_score = score
            
            if score >= self.significance_threshold:
                result.significant_observations.append(obs)
                self.significance_scorer.mark_significant()
            
            previous_obs = obs
        
        self._stats["significant_count"] += len(result.significant_observations)
        
        # Clear buffer after processing
        self.observation_buffer.clear()
        
        # Log results
        print(f"[Thinking] Cycle #{self._cycle_count}: "
              f"{len(observations)} buffered, "
              f"{len(result.significant_observations)} significant")
        log_activity("THINKING", f"Cycle #{self._cycle_count}: {len(observations)} buffered, {len(result.significant_observations)} significant")
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current thinking system status for API/UI."""
        return {
            "state": self.state.value,
            "observations_buffered": len(self.observation_buffer),
            "idle_seconds": self.idle_detector.get_idle_duration(),
            "can_notify": self.can_notify(),
            "last_cycle_ago": time.time() - self._last_thinking_cycle,
            "stats": self._stats.copy()
        }
    
    def get_pending_thoughts(self) -> List[str]:
        """Get any pending thoughts Rin wants to share."""
        thoughts = self._pending_thoughts.copy()
        self._pending_thoughts.clear()
        return thoughts
    
    def add_thought(self, thought: str):
        """Add a thought for potential sharing."""
        self._pending_thoughts.append(thought)
    
    def mark_notification_sent(self):
        """Record that a notification was sent."""
        self._last_notification_time = time.time()
        self._stats["notifications_sent"] += 1
    
    def increment_gemini_calls(self):
        """Track Gemini API usage."""
        self._gemini_call_count += 1
        self._stats["gemini_consulted"] += 1
    
    def should_consult_gemini(self, obs: Observation) -> bool:
        """
        Two-tier decision: Should we consult Gemini about this observation?
        Returns True only if significance score meets Gemini threshold.
        """
        if obs.significance_score >= self.gemini_threshold:
            return True
        
        # Below Gemini threshold - edge-filtered
        self._stats["edge_filtered"] += 1
        return False
    
    def save_thought_for_later(self, content: str, reason: str, context: str = None):
        """
        Save a thought for when user asks 'what are you thinking?'
        Used when edge logic decides not to notify immediately.
        """
        thought = SavedThought(
            content=content,
            reason=reason,
            timestamp=time.time(),
            context=context
        )
        self._saved_thoughts.append(thought)
        self._stats["thoughts_saved"] += 1
        
        # Keep only last 10 thoughts
        if len(self._saved_thoughts) > 10:
            self._saved_thoughts = self._saved_thoughts[-10:]
            
        log_system_change("THINKING_MEMORY", "thought_saved", f"[{reason}] {content[:50]}...")
        
        print(f"[Thinking] Saved thought for later: {content[:50]}...")
    
    def get_saved_thoughts(self) -> List[SavedThought]:
        """Get saved thoughts (deferred notifications)."""
        return self._saved_thoughts.copy()
    
    def clear_saved_thoughts(self):
        """Clear saved thoughts after sharing."""
        self._saved_thoughts.clear()
    
    def _hash_context(self, window_title: str, app_name: str) -> str:
        """Generate a hash for context deduplication."""
        content = f"{app_name}:{window_title}".lower()
        return hashlib.md5(content.encode()).hexdigest()[:16]


# Singleton instance
thinking_engine = ThinkingEngine()
