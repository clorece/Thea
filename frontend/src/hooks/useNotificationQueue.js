import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Smart Notification Queue Hook
 * 
 * Priority levels:
 * 1 = Insight (highest)
 * 2 = Chat
 * 3 = Reaction/Observation (lowest)
 * 
 * Features:
 * - Priority-based ordering
 * - Minimum display time enforcement
 * - Scene change awareness (stale reaction removal)
 * - Queue size limit
 */

const PRIORITY = {
    insight: 1,
    chat: 2,
    proactive: 1,  // same as insight
    reaction: 3,
    observation: 3
};

const DISPLAY_TIMES = {
    insight: 8000,
    chat: 6000,
    proactive: 8000,
    reaction: 5000,
    observation: 5000
};

const MIN_DISPLAY_TIME = 3000;  // Minimum time any notification shows
const MAX_QUEUE_SIZE = 5;

export function useNotificationQueue() {
    const [queue, setQueue] = useState([]);
    const [current, setCurrent] = useState(null);
    const [isDisplaying, setIsDisplaying] = useState(false);

    const displayTimeoutRef = useRef(null);
    const minTimeoutRef = useRef(null);
    const canAdvanceRef = useRef(true);
    const currentContextRef = useRef(null);  // Track current window context

    // Add notification to queue
    const enqueue = useCallback((notification) => {
        const { type, content, description, contextHash } = notification;

        const entry = {
            id: Date.now() + Math.random(),
            type: type || 'reaction',
            content,
            description,
            contextHash: contextHash || currentContextRef.current,
            priority: PRIORITY[type] || 3,
            displayTime: DISPLAY_TIMES[type] || 5000,
            timestamp: Date.now()
        };

        setQueue(prev => {
            // Add to queue
            let newQueue = [...prev, entry];

            // Sort by priority (lower = higher priority), then by timestamp
            newQueue.sort((a, b) => {
                if (a.priority !== b.priority) {
                    return a.priority - b.priority;
                }
                return a.timestamp - b.timestamp;
            });

            // Limit queue size (drop oldest low-priority items)
            if (newQueue.length > MAX_QUEUE_SIZE) {
                // Keep high priority, drop from end (lowest priority, oldest)
                newQueue = newQueue.slice(0, MAX_QUEUE_SIZE);
            }

            return newQueue;
        });
    }, []);

    // Dismiss current notification
    const dismiss = useCallback(() => {
        if (displayTimeoutRef.current) {
            clearTimeout(displayTimeoutRef.current);
        }
        if (minTimeoutRef.current) {
            clearTimeout(minTimeoutRef.current);
        }
        setCurrent(null);
        setIsDisplaying(false);
        canAdvanceRef.current = true;
    }, []);

    // Clear stale reactions when scene changes
    const clearStale = useCallback((newContextHash) => {
        currentContextRef.current = newContextHash;

        setQueue(prev => prev.filter(item => {
            // Keep insights and chat (not context-dependent)
            if (item.priority <= 2) return true;
            // Keep reactions that match new context or have no context
            if (!item.contextHash || item.contextHash === newContextHash) return true;
            // Discard stale reactions
            return false;
        }));
    }, []);

    // Process queue - show next notification when ready
    useEffect(() => {
        // If currently displaying or queue empty, don't advance
        if (isDisplaying || queue.length === 0 || !canAdvanceRef.current) {
            return;
        }

        // Get next notification
        const next = queue[0];
        if (!next) return;

        // Remove from queue and display
        setQueue(prev => prev.slice(1));
        setCurrent(next);
        setIsDisplaying(true);
        canAdvanceRef.current = false;

        // Set minimum display time
        minTimeoutRef.current = setTimeout(() => {
            canAdvanceRef.current = true;
        }, MIN_DISPLAY_TIME);

        // Set full display timeout
        displayTimeoutRef.current = setTimeout(() => {
            setCurrent(null);
            setIsDisplaying(false);
            canAdvanceRef.current = true;
        }, next.displayTime);

    }, [queue, isDisplaying]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (displayTimeoutRef.current) clearTimeout(displayTimeoutRef.current);
            if (minTimeoutRef.current) clearTimeout(minTimeoutRef.current);
        };
    }, []);

    return {
        current,           // Currently displaying notification
        isDisplaying,      // Whether something is showing
        queueLength: queue.length,
        enqueue,           // Add to queue
        dismiss,           // Force dismiss current
        clearStale,        // Remove stale reactions on scene change
        setContext: (hash) => { currentContextRef.current = hash; }
    };
}

export default useNotificationQueue;
