const API_URL = 'http://127.0.0.1:8000';

export const checkHealth = async () => {
    try {
        const response = await fetch(`${API_URL}/health`);
        return await response.json();
    } catch (error) {
        console.error('Backend health check failed:', error);
        return { status: 'error', error: error.message };
    }
};

export const sendMessage = async (text) => {
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        return await response.json();
    } catch (error) {
        console.error('Chat failed:', error);
        return { response: "I can't hear you right now." };
    }
};

export const getUpdates = async () => {
    try {
        const response = await fetch(`${API_URL}/updates`);
        return await response.json();
    } catch (error) {
        return { type: 'none' };
    }
};

export const captureScreen = async (analyze = false) => {
    try {
        const response = await fetch(`${API_URL}/capture?analyze=${analyze}`);
        return await response.json();
    } catch (error) {
        console.error('Capture failed:', error);
        return { status: 'error', error: error.message };
    }
};

export const getProactiveInsight = async () => {
    try {
        const response = await fetch(`${API_URL}/knowledge/proactive`);
        return await response.json();
    } catch (error) {
        return { has_insight: false };
    }
};

export const acknowledgeInsight = async (insightId, feedback = 'acknowledged') => {
    try {
        await fetch(`${API_URL}/knowledge/insight/${insightId}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback })
        });
    } catch (error) {
        console.error('Failed to acknowledge insight:', error);
    }
};

export async function shutdownBackend() {
    try {
        await fetch(`${API_BASE}/shutdown`);
    } catch (e) {
        console.log('Backend shutdown command sent (or failed if already off)');
    }
}
