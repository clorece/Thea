import React, { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import rinPfp from '../assets/rin-pfp.jpg';

export default function NotificationCenter({ notifications = [] }) {
    return (
        <div style={{
            position: 'relative', // Wrapper
            width: '100%',
            alignSelf: 'center',
            height: '140px',
            flexShrink: 0,
            marginBottom: '10px', // Increased spacing
            zIndex: 900,
            WebkitAppRegion: 'no-drag' // Allow interaction
        }}>
            {/* Scrollable Content Container with Smart Mask */}
            <div style={{
                width: '100%',
                height: '100%',
                overflowY: 'auto',
                overflowX: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                paddingBottom: '20px',
                paddingRight: '6px', // Space for content vs scrollbar
                pointerEvents: 'auto',

                // Smart Mask: Fade content (left), Keep scrollbar visible (right)
                maskImage: `
                    linear-gradient(to bottom, black 85%, transparent 100%),
                    linear-gradient(to bottom, black, black)
                `,
                maskSize: 'calc(100% - 10px) 100%, 10px 100%',
                maskPosition: '0 0, 100% 0',
                maskRepeat: 'no-repeat',

                // Webkit Prefix for compatibility
                WebkitMaskImage: `
                    linear-gradient(to bottom, black 85%, transparent 100%),
                    linear-gradient(to bottom, black, black)
                `,
                WebkitMaskSize: 'calc(100% - 10px) 100%, 10px 100%',
                WebkitMaskPosition: '0 0, 100% 0',
                WebkitMaskRepeat: 'no-repeat'
            }}>
                <AnimatePresence initial={false} mode='popLayout'>
                    {notifications.map((notif) => (
                        <motion.div
                            key={notif.id}
                            layout
                            initial={{ opacity: 0, y: -20, scale: 0.9 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                            style={{
                                background: notif.type === 'recommendation' ? 'rgba(234, 179, 8, 0.15)' : 'rgba(0, 0, 0, 0.6)',
                                backdropFilter: 'blur(12px)',
                                padding: '10px 14px',
                                borderRadius: '16px',
                                border: notif.type === 'recommendation' ? '1px solid rgba(234, 179, 8, 0.4)' : '1px solid rgba(255,255,255,0.1)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '12px',
                                boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
                                flexShrink: 0
                            }}
                        >
                            <img
                                src={rinPfp}
                                alt="Rin"
                                style={{
                                    width: '28px',
                                    height: '28px',
                                    borderRadius: '50%',
                                    objectFit: 'cover',
                                    border: '1px solid rgba(255,255,255,0.2)'
                                }}
                            />
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <span style={{ color: 'white', fontSize: '13px', lineHeight: '1.3' }}>
                                    {notif.description || notif.content}
                                </span>
                                {notif.type !== 'reaction' && (
                                    <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', textTransform: 'uppercase' }}>
                                        {notif.type}
                                    </span>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>
        </div>
    );
}
