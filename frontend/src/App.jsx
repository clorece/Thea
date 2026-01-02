import React, { useState, useEffect } from 'react';
import { checkHealth, captureScreen } from './services/api';
import ChatInterface from './components/ChatInterface';
import ReactionOverlay from './components/ReactionOverlay';

function App() {
    const [status, setStatus] = useState('Checking connection...');
    const [activeWindow, setActiveWindow] = useState('Unknown');
    const [lastImage, setLastImage] = useState(null);
    const [isWatching, setIsWatching] = useState(false);

    useEffect(() => {
        const connect = async () => {
            const result = await checkHealth();
            if (result.status === 'ok') {
                setStatus('System Online (Connected to Neural Core)');
                setIsWatching(true);
            } else {
                setStatus('Connection Failed: Neural Core Offline');
            }
        };
        connect();

        // Poll every 5 seconds
        const interval = setInterval(connect, 5000);
        return () => clearInterval(interval);
    }, []);

    // Observation Loop
    useEffect(() => {
        let watchInterval;
        if (isWatching) {
            watchInterval = setInterval(async () => {
                // Request analysis (Backend handles rate limiting)
                const data = await captureScreen(true);
                if (data.status === 'ok') {
                    setLastImage(`data:image/jpeg;base64,${data.image}`);
                    setActiveWindow(data.window);
                }
            }, 2000); // Check every 2 seconds
        }
        return () => clearInterval(watchInterval);
    }, [isWatching]);

    return (
        <div style={{
            height: '100vh',
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(20px)',
            color: 'white',
            borderRadius: '20px',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            fontFamily: 'Segoe UI, sans-serif',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            WebkitAppRegion: 'drag',
            overflow: 'hidden',
            position: 'relative'
        }}>
            <h1 style={{ margin: '0 0 10px 0', fontSize: '24px', fontWeight: '300', letterSpacing: '1px' }}>THEA</h1>

            {/* Status Bar */}
            <div style={{
                margin: '10px 0',
                padding: '8px 16px',
                background: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '12px',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                width: '90%',
                justifyContent: 'space-between'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: status.includes('Online') ? '#4ade80' : '#ef4444',
                        boxShadow: status.includes('Online') ? '0 0 10px #4ade80' : 'none'
                    }} />
                    <span>{status.split('(')[0]}</span>
                </div>
                <div style={{ opacity: 0.7 }}>{activeWindow.substring(0, 30)}...</div>
            </div>

            {/* Vision Feed (The Mirror) */}
            <div style={{
                flex: 1,
                width: '100%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                margin: '20px 0',
                background: 'rgba(0,0,0,0.3)',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.05)',
                overflow: 'hidden',
                position: 'relative'
            }}>
                {/* Reaction Overlay sits on top of the feed or screen */}
                <ReactionOverlay isWatching={isWatching} />

                {lastImage ? (
                    <img src={lastImage} style={{ maxWidth: '100%', maxHeight: '200px', objectFit: 'contain' }} alt="Vision Feed" />
                ) : (
                    <div style={{ color: '#666', fontSize: '14px' }}>Vision Offline</div>
                )}
            </div>

            {/* Controls */}
            <div style={{ WebkitAppRegion: 'no-drag', display: 'flex', gap: '10px', width: '100%' }}>
                <button
                    onClick={() => setIsWatching(!isWatching)}
                    style={{
                        flex: 1,
                        padding: '12px 0',
                        background: isWatching ? '#ef4444' : 'white',
                        color: isWatching ? 'white' : 'black',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontWeight: '600',
                        transition: 'all 0.2s'
                    }}>
                    {isWatching ? 'Stop Observing' : 'Start Observation'}
                </button>
            </div>

            {/* Chat Interface (Floating) */}
            <div style={{ WebkitAppRegion: 'no-drag' }}>
                <ChatInterface />
            </div>
        </div>
    );
}

export default App;
