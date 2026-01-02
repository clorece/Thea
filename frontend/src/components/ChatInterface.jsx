import React, { useState, useEffect, useRef } from 'react';
import { sendMessage } from '../services/api';
import { MessageSquare, X, Send } from 'lucide-react';

export default function ChatInterface() {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setIsTyping(true);

        const data = await sendMessage(userMsg);

        setIsTyping(false);
        setMessages(prev => [...prev, { role: 'model', content: data.response }]);
    };

    return (
        <>
            {/* Toggle Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    position: 'absolute',
                    bottom: '20px',
                    right: '20px',
                    background: 'rgba(255, 255, 255, 0.15)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '50%',
                    width: '50px',
                    height: '50px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    cursor: 'pointer',
                    backdropFilter: 'blur(10px)',
                    zIndex: 1000
                }}
            >
                {isOpen ? <X size={24} /> : <MessageSquare size={24} />}
            </button>

            {/* Chat Window */}
            {isOpen && (
                <div style={{
                    position: 'absolute',
                    bottom: '80px',
                    right: '20px',
                    width: '350px',
                    height: '500px',
                    background: 'rgba(20, 20, 20, 0.95)',
                    backdropFilter: 'blur(20px)',
                    borderRadius: '16px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    zIndex: 1000,
                    boxShadow: '0 10px 40px rgba(0,0,0,0.5)'
                }}>
                    {/* Header */}
                    <div style={{
                        padding: '16px',
                        borderBottom: '1px solid rgba(255,255,255,0.1)',
                        fontWeight: '600',
                        fontSize: '14px',
                        color: 'rgba(255,255,255,0.9)'
                    }}>
                        Chat with Thea
                    </div>

                    {/* Messages */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px'
                    }}>
                        {messages.length === 0 && (
                            <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: '13px', marginTop: '40px' }}>
                                Say hello! I'm watching.
                            </div>
                        )}
                        {messages.map((msg, idx) => (
                            <div key={idx} style={{
                                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                background: msg.role === 'user' ? '#3b82f6' : 'rgba(255,255,255,0.1)',
                                padding: '8px 12px',
                                borderRadius: '12px',
                                maxWidth: '80%',
                                fontSize: '14px',
                                lineHeight: '1.4',
                                color: 'white',
                                borderBottomRightRadius: msg.role === 'user' ? '2px' : '12px',
                                borderBottomLeftRadius: msg.role === 'model' ? '2px' : '12px'
                            }}>
                                {msg.content}
                            </div>
                        ))}
                        {isTyping && (
                            <div style={{ alignSelf: 'flex-start', color: 'rgba(255,255,255,0.5)', fontSize: '12px' }}>
                                Thea is thinking...
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div style={{
                        padding: '16px',
                        borderTop: '1px solid rgba(255,255,255,0.1)',
                        display: 'flex',
                        gap: '8px'
                    }}>
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Type a message..."
                            style={{
                                flex: 1,
                                background: 'rgba(255,255,255,0.05)',
                                border: '1px solid rgba(255,255,255,0.1)',
                                borderRadius: '8px',
                                padding: '8px 12px',
                                color: 'white',
                                outline: 'none'
                            }}
                        />
                        <button
                            onClick={handleSend}
                            disabled={isTyping}
                            style={{
                                background: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                width: '36px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                opacity: isTyping ? 0.5 : 1
                            }}
                        >
                            <Send size={16} color="black" />
                        </button>
                    </div>
                </div>
            )}
        </>
    );
}
