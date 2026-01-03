import React, { useState, useEffect } from 'react';
import { checkHealth, captureScreen, getUpdates, getProactiveInsight, acknowledgeInsight } from './services/api';
import ChatInterface from './components/ChatInterface';
import NotificationCenter from './components/NotificationCenter';
import rinPfp from './assets/rin-pfp.jpg';

function App() {
    const [status, setStatus] = useState('Checking connection...');
    const [activeWindow, setActiveWindow] = useState('Unknown');
    const [lastImage, setLastImage] = useState(null);
    const [isWatching, setIsWatching] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const [showFeed, setShowFeed] = useState(false);
    const [userIdle, setUserIdle] = useState(false);
    const [idleTime, setIdleTime] = useState(0);
    const [isAlwaysOnTop, setIsAlwaysOnTop] = useState(false);
    const [isListening, setIsListening] = useState(true); // Audio listening state
    const [externalChatMessage, setExternalChatMessage] = useState(null);

    // Notification History
    const [notifications, setNotifications] = useState([]);

    const addNotification = (notif) => {
        const entry = {
            ...notif,
            id: Date.now() + Math.random(),
            timestamp: Date.now()
        };
        setNotifications(prev => [entry, ...prev].slice(0, 5));
    };


    useEffect(() => {
        const connect = async () => {
            const result = await checkHealth();
            if (result.status === 'ok') {
                setStatus('System Online (Connected to Neural Core)');
                setIsWatching(true);
            } else {
                setStatus('Connection Failed: Neural Core Offline');
            }

            // Check ears status
            try {
                const { getEarsStatus } = await import('./services/api');
                const earsStatus = await getEarsStatus();
                setIsListening(earsStatus.listening);
            } catch (e) { }
        };
        connect();

        // Poll every 5 seconds
        const interval = setInterval(connect, 5000);
        return () => clearInterval(interval);
    }, []);

    // Idle Detection Logic
    useEffect(() => {
        if (!window.electronAPI) return;

        const checkIdle = async () => {
            try {
                const idleSeconds = await window.electronAPI.getSystemIdleTime();
                setIdleTime(idleSeconds);

                if (idleSeconds > 120 && !userIdle) {
                    setUserIdle(true);
                } else if (idleSeconds < 2 && userIdle) {
                    setUserIdle(false);
                    // Welcome back greeting
                    const { sendMessage } = await import('./services/api');
                    const data = await sendMessage("[System]: User returned after break. Greet them.");
                    if (data.response) {
                        const texts = Array.isArray(data.response) ? data.response : [data.response];
                        texts.forEach(text => addNotification({ type: 'chat', content: '💬', description: text }));
                    }
                }
            } catch (e) {
                console.error("Idle Check Error:", e);
            }
        };

        const timer = setInterval(checkIdle, 1000);
        return () => clearInterval(timer);
    }, [userIdle]);

    // Reaction Polling - enqueue reactions
    useEffect(() => {
        if (!isWatching || isPaused) return;

        const poll = async () => {
            const update = await getUpdates();
            if (update && (update.type === 'reaction' || update.type === 'proactive' || update.type === 'chat')) {
                if (update.type === 'chat') {
                    setExternalChatMessage(update.description);
                }

                addNotification({
                    ...update,
                    contextHash: activeWindow
                });
            }
        };

        const interval = setInterval(poll, 1000);
        return () => clearInterval(interval);
    }, [isWatching, isPaused, activeWindow]);

    // Proactive Insight Polling - enqueue insights
    useEffect(() => {
        if (!isWatching || isPaused) return;

        const pollInsights = async () => {
            const insight = await getProactiveInsight();
            if (insight && insight.has_insight) {
                addNotification({
                    type: 'insight',
                    content: '💡',
                    description: insight.message
                });
                // Mark as delivered
                acknowledgeInsight(insight.id, 'displayed');
            }
        };

        // Check immediately on mount
        pollInsights();

        // Then poll every 30 seconds
        const interval = setInterval(pollInsights, 30000);
        return () => clearInterval(interval);
    }, [isWatching, isPaused]);

    // Scene change detection - clear stale reactions
    useEffect(() => {
        // We could clear stale items from list here if desired
        setActiveWindow(activeWindow);
    }, [activeWindow]);

    const handleChatReaction = (content) => {
        const text = typeof content === 'string' ? content : (content?.description || '');
        if (text) addNotification({ type: 'chat', content: '💬', description: text });
    };

    const handleRestart = async () => {
        setIsWatching(false);
        setIsPaused(false);
        setLastImage(null);
        setActiveWindow('Restarting...');

        // Brief delay to simulate restart/allow state to clear
        setTimeout(async () => {
            const result = await checkHealth();
            if (result.status === 'ok') {
                setStatus('System Online (Connected to Neural Core)');
                setIsWatching(true);
            } else {
                setStatus('Restart Failed');
            }
        }, 800);
    };

    const toggleAlwaysOnTop = () => {
        const newState = !isAlwaysOnTop;
        setIsAlwaysOnTop(newState);
        if (window.electronAPI) {
            // 'screen-saver' level is needed to stay on top of fullscreen games
            window.electronAPI.setAlwaysOnTop(true, newState ? 'screen-saver' : 'normal');
        }
    };

    // Observation Loop
    useEffect(() => {
        let watchInterval;
        if (isWatching && !isPaused && !userIdle) {
            watchInterval = setInterval(async () => {
                // Request analysis (Backend handles rate limiting)
                const data = await captureScreen(true);
                if (data.status === 'ok') {
                    setLastImage(`data:image/jpeg;base64,${data.image}`);
                    setActiveWindow(data.window);
                }
            }, 1000); // Check every 1 second
        }
        return () => clearInterval(watchInterval);
    }, [isWatching, isPaused, userIdle]);

    // Fixed Window Size
    useEffect(() => {
        // Ensure we are at correct size
        if (window.electronAPI) {
            window.electronAPI.resizeWindow({ width: 450, height: 750 });
        }
    }, []);

    return (
        <div id="app-root" style={{
            height: '750px',    // Fixed height
            width: '100%',
            background: 'rgba(0, 0, 0, 0.65)',
            backdropFilter: 'blur(20px)',
            color: 'white',
            borderRadius: '20px',
            padding: '16px',

            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            fontFamily: 'Segoe UI, sans-serif',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            WebkitAppRegion: 'drag',
            overflow: 'hidden', // Disable scrollbars
            position: 'relative'
        }}>

            {/* Header / Controls Column */}
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                width: '100%',
                marginBottom: '16px',
                gap: '8px',
                zIndex: 50, // Ensure header is above chat
                WebkitAppRegion: 'drag' // Allow dragging from header area
            }}>
                {/* Profile Picture */}
                <img
                    src={rinPfp}
                    alt="Rin"
                    style={{
                        width: '80px',
                        height: '80px',
                        borderRadius: '50%',
                        objectFit: 'cover',
                        border: '2px solid rgba(255,255,255,0.1)',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                    }}
                />

                {/* Title */}
                <h1 style={{
                    margin: 0,
                    fontSize: '24px',
                    fontWeight: '300',
                    letterSpacing: '1px',
                    textShadow: '0 2px 4px rgba(0,0,0,0.3)'
                }}>RIN</h1>

                {/* Controls Row */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    WebkitAppRegion: 'no-drag' // Buttons clickable
                }}>

                    {/* Main Controls Group */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                        {/* Power (Shutdown) */}
                        {/* Power (Shutdown) */}
                        <button
                            onClick={() => {
                                // 1. Fire backend shutdown (don't await, just send it)
                                import('./services/api').then(({ shutdownBackend }) => {
                                    shutdownBackend().catch(err => console.log("Backend shutdown ignored:", err));
                                }).catch(() => { });

                                // 2. Quit Electron UI content locally
                                setTimeout(() => {
                                    console.log("Quitting App...");
                                    if (window.electronAPI && window.electronAPI.quitApp) {
                                        window.electronAPI.quitApp();
                                    } else {
                                        window.close();
                                    }
                                }, 100);
                            }}
                            title="Shut Down System"
                            style={{
                                width: '32px',
                                height: '32px',
                                background: 'rgba(239, 68, 68, 0.15)',
                                color: '#ef4444',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                transition: 'all 0.2s',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)';
                                e.currentTarget.style.border = '1px solid rgba(239, 68, 68, 0.6)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)';
                                e.currentTarget.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                            }}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path>
                                <line x1="12" y1="2" x2="12" y2="12"></line>
                            </svg>
                        </button>

                        {/* Pause */}
                        <button
                            onClick={() => setIsPaused(!isPaused)}
                            disabled={!isWatching}
                            title={isPaused ? "Resume" : "Pause"}
                            style={{
                                width: '32px',
                                height: '32px',
                                background: isPaused ? 'rgba(250, 204, 21, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                color: isPaused ? '#facc15' : 'white',
                                border: isPaused ? '1px solid rgba(250, 204, 21, 0.5)' : '1px solid rgba(255, 255, 255, 0.1)',
                                borderRadius: '8px',
                                cursor: isWatching ? 'pointer' : 'not-allowed',
                                opacity: isWatching ? 1 : 0.5,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                transition: 'all 0.2s',
                            }}>
                            {isPaused ? (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                                </svg>
                            ) : (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <rect x="6" y="4" width="4" height="16"></rect>
                                    <rect x="14" y="4" width="4" height="16"></rect>
                                </svg>
                            )}
                        </button>

                        {/* Restart */}
                        <button
                            onClick={handleRestart}
                            disabled={!isWatching}
                            title="Restart System"
                            style={{
                                width: '32px',
                                height: '32px',
                                background: 'rgba(255, 255, 255, 0.1)',
                                color: 'white',
                                border: '1px solid rgba(255, 255, 255, 0.1)',
                                borderRadius: '8px',
                                cursor: isWatching ? 'pointer' : 'not-allowed',
                                opacity: isWatching ? 1 : 0.5,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                transition: 'all 0.2s',
                            }}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21.5 2v6h-6"></path>
                                <path d="M22 11.5A10 10 0 0 0 3.2 7.2M2.5 22v-6h6"></path>
                                <path d="M2 12.5A10 10 0 0 0 20.8 16.8"></path>
                            </svg>
                        </button>

                        {/* Ears Toggle */}
                        <button
                            onClick={async () => {
                                try {
                                    const { toggleEars } = await import('./services/api');
                                    const newState = !isListening;
                                    const result = await toggleEars(newState);
                                    setIsListening(result.listening);
                                } catch (e) {
                                    console.error("Failed to toggle ears:", e);
                                }
                            }}
                            title={isListening ? "Mute Ears" : "Enable Ears"}
                            style={{
                                width: '32px',
                                height: '32px',
                                background: isListening ? 'rgba(74, 222, 128, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                                color: isListening ? '#4ade80' : 'white',
                                border: isListening ? '1px solid rgba(74, 222, 128, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                transition: 'all 0.2s',
                            }}
                        >
                            {isListening ? (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                                    <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
                                </svg>
                            ) : (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5 }}>
                                    <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                                    <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
                                    <line x1="1" y1="1" x2="23" y2="23"></line>
                                </svg>
                            )}
                        </button>

                        {/* Dev Mode Toggle (Hidden for User Mode) */}
                        {/* <button
                            onClick={() => setShowFeed(!showFeed)}
                            style={{
                                width: '32px',
                                height: '32px',
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                color: showFeed ? '#fff' : 'rgba(255,255,255,0.3)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}
                            title={showFeed ? "Hide Debug View" : "Show Debug View"}
                        >
                            {showFeed ? (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                    <circle cx="12" cy="12" r="3"></circle>
                                </svg>
                            ) : (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                                    <line x1="1" y1="1" x2="23" y2="23"></line>
                                </svg>
                            )}
                        </button> */}
                    </div>

                    {/* Status & Timer Group */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {/* Debug Timer */}
                        {showFeed && (
                            <span style={{
                                fontSize: '10px',
                                fontFamily: 'monospace',
                                color: 'rgba(255,255,255,0.5)',
                                transition: 'opacity 0.2s'
                            }}>
                                SYS:{idleTime}s
                            </span>
                        )}

                        <div style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: userIdle ? '#facc15' : (status.includes('Online') ? '#4ade80' : '#ef4444'),
                            boxShadow: userIdle ? '0 0 10px #facc15' : (status.includes('Online') ? '0 0 10px #4ade80' : 'none'),
                            transition: 'all 0.3s ease'
                        }} title={userIdle ? "System Idle (Rest Mode)" : status} />
                    </div>

                    {/* Always On Top Toggle */}
                    <button
                        onClick={toggleAlwaysOnTop}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '14px',
                            opacity: isAlwaysOnTop ? 1 : 0.5,
                            filter: isAlwaysOnTop ? 'drop-shadow(0 0 5px #4ade80)' : 'none',
                            transition: 'all 0.3s'
                        }}
                        title="Force Always On Top (Overlay Games)"
                    >
                        📌
                    </button>
                </div>
            </div>

            {/* Notification Center (Controlled by list state) */}
            <NotificationCenter notifications={notifications} />

            {/* Main Content Area (Chat) */}
            <div style={{
                flex: 1,
                width: '100%',
                WebkitAppRegion: 'no-drag',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}>
                <ChatInterface onReaction={handleChatReaction} incomingMessage={externalChatMessage} />
            </div>

            {/* Vision Feed (The Mirror) - At Bottom */}{showFeed && (
                <div style={{
                    height: '280px', // Fixed height when visible
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    marginTop: '16px',
                    background: 'rgba(0,0,0,0.3)',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.05)',
                    overflow: 'hidden',
                    position: 'relative',
                    flexShrink: 0 // Prevent shrinking
                }}>

                    {lastImage ? (
                        <img src={lastImage} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', opacity: isPaused ? 0.5 : 1 }} alt="Vision Feed" />
                    ) : (
                        <div style={{ color: '#666', fontSize: '14px' }}>Vision Offline</div>
                    )}

                    {isPaused && (
                        <div style={{
                            position: 'absolute',
                            top: '50%',
                            left: '50%',
                            transform: 'translate(-50%, -50%)',
                            background: 'rgba(0,0,0,0.6)',
                            padding: '8px 16px',
                            borderRadius: '20px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}>
                            <div style={{ width: '8px', height: '8px', background: '#facc15', borderRadius: '50%' }} />
                            <span style={{ fontSize: '12px', fontWeight: '600' }}>PAUSED</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}


export default App;
