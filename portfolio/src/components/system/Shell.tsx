'use client';

import React from 'react';
import AgentStatus from './AgentStatus';
import { useTheme } from './ThemeEngine';

export default function Shell({ children }: { children: React.ReactNode }) {
    const { theme, toggleTheme } = useTheme();

    return (
        <div className="relative w-full h-full min-h-screen bg-background text-foreground flex flex-col font-mono selection:bg-accent selection:text-background">
            {/* Top CLI Input Bar */}
            <header className="system-border border-b w-full h-12 flex items-center px-4 shrink-0 bg-background/80 backdrop-blur-sm z-50">
                <div className="flex items-center text-sm md:text-base w-full">
                    <span className="text-accent mr-2 font-bold">architect@system:~#</span>
                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            const input = (e.currentTarget.elements.namedItem('cli') as HTMLInputElement).value;
                            if (input.trim() === 'system --theme toggle') {
                                toggleTheme();
                            }
                            e.currentTarget.reset();
                        }}
                        className="flex-1 flex items-center"
                    >
                        <input
                            type="text"
                            name="cli"
                            placeholder="type 'system --theme toggle' and press enter"
                            className="bg-transparent border-none outline-none w-full text-foreground placeholder:text-muted/50"
                            autoComplete="off"
                            spellCheck="false"
                        />
                        <span className="w-2 h-4 md:h-5 bg-accent animate-blink shrink-0 ml-1"></span>
                    </form>
                </div>
            </header>

            {/* Main Grid Layout */}
            <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-12 overflow-hidden">

                {/* Core Content Area */}
                <main className="col-span-1 md:col-span-9 lg:col-span-10 h-full overflow-y-auto overflow-x-hidden no-scrollbar scanline-overlay relative flex flex-col">
                    {children}
                </main>

                {/* Sidebar Status Panel */}
                <aside className="hidden md:flex md:col-span-3 lg:col-span-2 system-border border-l h-full flex-col bg-background/95 relative z-40">
                    <AgentStatus />
                </aside>
            </div>

            {/* Mobile Agent Status (Bottom Bar) */}
            <div className="md:hidden system-border border-t h-10 w-full flex items-center px-4 text-xs justify-between text-muted bg-background shrink-0">
                <span>STATUS: ACTIVE</span>
                <span>SYS: {theme.toUpperCase()}</span>
            </div>
        </div>
    );
}
