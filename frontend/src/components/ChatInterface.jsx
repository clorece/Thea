import React, { useState, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { sendMessage } from '../services/api';
import { Send } from 'lucide-react';
import rinPfp from '../assets/rin-pfp.jpg';

export default function ChatInterface({ onReaction, incomingMessage }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    // Handle external incoming messages (from queue/split)
    useEffect(() => {
        if (incomingMessage) {
            setMessages(prev => [...prev, { role: 'model', content: incomingMessage }]);
        }
    }, [incomingMessage]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsTyping(true);

        const data = await sendMessage(userMsg);

        setIsTyping(false);

        // Backend now returns a List[str] (usually just [chunks[0]])
        if (data.response && Array.isArray(data.response)) {
            const newMsgs = data.response.map(text => ({ role: 'model', content: text }));
            setMessages(prev => [...prev, ...newMsgs]);

            // Notify overlay about first chunk
            if (onReaction && newMsgs.length > 0) {
                onReaction(newMsgs[0].content);
            }
        } else if (data.response) {
            // Fallback for string
            setMessages(prev => [...prev, { role: 'model', content: data.response }]);
            if (onReaction) onReaction(data.response);
        }
    };

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            width: '100%',
            position: 'relative',
            overflow: 'hidden' // Contain children
        }}>

            {/* Messages Area */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '10px 6px', // Align with NotificationCenter
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                // marginTop removed (layout is now flex)
            }}>
                <div style={{ flex: 1 }} />

                {messages.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        color: 'rgba(255,255,255,0.3)',
                        fontSize: '13px',
                        marginBottom: 'auto'
                    }}>
                        Start a conversation...
                    </div>
                )}

                <AnimatePresence>
                    {messages.map((msg, idx) => (
                        <motion.div
                            key={idx}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, ease: 'easeOut' }}
                            style={{
                                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                maxWidth: '85%'
                            }}
                        >
                            {msg.role === 'model' && (
                                <img
                                    src={rinPfp}
                                    alt="Rin"
                                    style={{
                                        width: '36px',
                                        height: '36px',
                                        borderRadius: '50%',
                                        objectFit: 'cover',
                                        border: '1px solid rgba(255,255,255,0.1)'
                                    }}
                                />
                            )}
                            <div style={{
                                background: msg.role === 'user' ? '#3b82f6' : 'rgba(255,255,255,0.08)',
                                padding: '8px 12px',
                                borderRadius: '12px',
                                fontSize: '14px',
                                lineHeight: '1.4',
                                color: 'white',
                                borderBottomRightRadius: msg.role === 'user' ? '2px' : '12px',
                                borderBottomLeftRadius: msg.role === 'model' ? '2px' : '12px'
                            }}>
                                {msg.content}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {isTyping && (
                    <div style={{ alignSelf: 'flex-start', color: 'rgba(255,255,255,0.5)', fontSize: '12px', marginLeft: '8px' }}>
                        Processing...
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area (Fixed Bottom) */}
            <div style={{
                paddingTop: '12px',
                paddingBottom: '4px', // Little bottom clearance
                borderTop: '1px solid rgba(255,255,255,0.05)',
                display: 'flex',
                gap: '8px',
                background: 'transparent' // Let the app background show
            }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Message Rin..."
                    style={{
                        flex: 1,
                        background: 'rgba(0,0,0,0.2)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '20px',
                        padding: '10px 16px',
                        color: 'white',
                        outline: 'none',
                        fontSize: '14px'
                    }}
                />
                <button
                    onClick={handleSend}
                    disabled={isTyping}
                    style={{
                        background: 'rgba(255,255,255,0.1)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '50%',
                        width: '40px',
                        height: '40px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: isTyping ? 'default' : 'pointer',
                        opacity: isTyping ? 0.5 : 1,
                        color: 'white',
                        transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => !isTyping && (e.currentTarget.style.background = 'rgba(255,255,255,0.2)')}
                    onMouseLeave={(e) => !isTyping && (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
                >
                    <Send size={18} />
                </button>
            </div>
        </div>
    );
}
