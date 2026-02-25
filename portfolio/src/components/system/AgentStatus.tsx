'use client';

import React, { useEffect, useState } from 'react';
import { useTheme } from './ThemeEngine';

export default function AgentStatus() {
    const [scrollPos, setScrollPos] = useState(0);
    const [bitrate, setBitrate] = useState(124);
    const { theme } = useTheme();

    // Track scroll position of the main content area
    useEffect(() => {
        const handleScroll = () => {
            const scrollY = window.scrollY;
            const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const percentage = height > 0 ? Math.round((scrollY / height) * 100) : 0;
            setScrollPos(percentage);
        };

        window.addEventListener('scroll', handleScroll);

        // Simulate bitrate fluctuation
        const interval = setInterval(() => {
            setBitrate(prev => {
                const fluctuation = Math.floor(Math.random() * 20) - 10;
                return Math.max(64, Math.min(256, prev + fluctuation));
            });
        }, 2000);

        return () => {
            window.removeEventListener('scroll', handleScroll);
            clearInterval(interval);
        };
    }, []);

    const timeString = new Date().toLocaleTimeString('en-US', { hour12: false });

    return (
        <div className="w-full h-full p-4 flex flex-col text-xs md:text-sm font-mono tracking-tight gap-6">

            {/* Header */}
            <div className="flex flex-col gap-1 border-b system-border pb-4">
                <span className="text-accent font-bold">AGENT_STATUS</span>
                <span className="text-muted">ID: KAB-18-SYS</span>
                <span className="text-muted mt-2">UPTIME: {timeString}</span>
            </div>

            {/* Metrics */}
            <div className="flex flex-col gap-3">
                <div className="flex justify-between">
                    <span className="text-muted">SCROLL_POS:</span>
                    <span className="text-foreground">{scrollPos}%</span>
                </div>
                <div className="w-full h-1 bg-border relative">
                    <div
                        className="absolute top-0 left-0 h-full bg-accent transition-all duration-100"
                        style={{ width: `${scrollPos}%` }}
                    />
                </div>

                <div className="flex justify-between mt-2">
                    <span className="text-muted">BITRATE:</span>
                    <span className="text-foreground">~{bitrate} kbps</span>
                </div>

                <div className="flex justify-between mt-2">
                    <span className="text-muted">THEME_PROFILE:</span>
                    <span className="text-foreground">{theme.toUpperCase()}</span>
                </div>
            </div>

            {/* Spacer */}
            <div className="flex-1" />

            {/* System Warning / Info */}
            <div className="border system-border p-3 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                    <span className="font-bold text-foreground">SYSTEM NOMINAL</span>
                </div>
                <span className="text-muted text-[10px] uppercase leading-tight mt-1">
                    Archiving memories. Compiling experience. Monitoring continuous deployment logic.
                </span>
            </div>

        </div>
    );
}
