"use client";
import { useEffect, useState, useRef } from 'react';
import Link from "next/link";
import Image from "next/image";

export default function Logs() {
    const [logs, setLogs] = useState<string[]>([
        "[SYS] INITIALIZING CORE MODULES...",
        "[SYS] LOADING KERNEL DRIVERS [OK]",
        "[NET] ETH0 LINK UP AT 1000MBPS FULL-DUPLEX",
        "[SEC] FIREWALL RULES LOADED",
    ]);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Only scroll to bottom locally if simulating
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    useEffect(() => {
        // We will generate the Javascript script string to run natively 
        // when served as a fully static Django template snippet
    }, []);

    return (
        <div className="min-h-screen bg-background-dark text-white font-sans flex overflow-hidden">
            {/* Sidebar hidden for brevity but the script output will copy it */}
            {/* ... We rely on Django's structure or just full static for NextJS preview ... */}

            <main className="flex-1 flex flex-col w-full bg-background-dark relative">
                <header className="h-14 border-b border-terminal-gray flex items-center justify-between px-6 bg-background-dark/95 backdrop-blur sticky top-0 z-20">
                    <div className="flex items-center gap-2">
                        <a href="/" className="text-primary hover:text-white transition-colors flex items-center gap-1 bg-terminal-gray/20 px-2 py-1 border border-terminal-gray hover:border-primary mr-2 shrink-0">
                            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                            <span className="text-xs font-mono">cd ..</span>
                        </a>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <span className="md:hidden material-symbols-outlined text-primary hover:text-white mr-2 text-xl cursor-not-allowed hidden">menu</span>
                            <span className="hidden sm:inline">root</span>
                            <span className="hidden sm:inline">@</span>
                            <span className="text-white hidden sm:inline">kabhishek18</span>
                            <span className="hidden sm:inline">:</span>
                            <span className="text-primary">~/system/logs</span>
                        </div>
                    </div>
                    <div className="flex gap-4 text-xs font-mono text-primary">
                        <span className="hidden sm:inline-block">CPU: 88%</span>
                        <span className="hidden sm:inline-block">RAM: 14.1GB</span>
                        <span className="animate-pulse">● TAILING</span>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4 font-mono text-sm" id="log-terminal-output">
                    <div className="text-primary opacity-80 mb-4">&gt; tail -f /var/log/syslog</div>

                    {logs.map((log, i) => (
                        <div key={i} className="text-gray-300 break-all border-l-2 border-terminal-gray pl-4 hover:border-primary transition-colors">
                            <span className="text-gray-500 mr-4">[{new Date().toISOString().split('T')[1].slice(0, 12)}]</span>
                            {log.includes('[ERR]') ? <span className="text-red-500">{log}</span> :
                                log.includes('[SEC]') ? <span className="text-yellow-500">{log}</span> :
                                    log.includes('[OK]') ? <span className="text-green-500">{log}</span> : log}
                        </div>
                    ))}
                    <div ref={endRef} />
                </div>
            </main>

            {/* Script injected that convert_jsx.py will keep */}
            <script dangerouslySetInnerHTML={{
                __html: `
        document.addEventListener('DOMContentLoaded', () => {
          const container = document.getElementById('log-terminal-output');
          if (!container) return;
          
          const logMessages = [
            "[NET] TCP CONNECTION ESTABLISHED FROM 192.168.1.45",
            "[SYS] GARBAGE COLLECTION TRIGGERED (240ms)",
            "[SEC] [ERR] UNAUTHORIZED ACCESS ATTEMPT DETECTED",
            "[DB] QUERY EXECUTED IN 4ms",
            "[API] RATE LIMIT CHECK [OK]",
            "[SYS] KERNEL PANIC AVERTED",
            "[WARN] HIGH MEMORY USAGE DETECTED",
            "[AUTH] TOKEN VALIDATED FOR USER kb18",
            "[OK] SYNCHRONIZATION COMPLETE"
          ];
          
          setInterval(() => {
            const dateStr = new Date().toISOString().split('T')[1].slice(0, 12);
            const msg = logMessages[Math.floor(Math.random() * logMessages.length)];
            
            let htmlMsg = msg;
            if (msg.includes('[ERR]')) htmlMsg = '<span class="text-red-500">' + msg + '</span>';
            else if (msg.includes('[SEC]') || msg.includes('[WARN]')) htmlMsg = '<span class="text-yellow-500">' + msg + '</span>';
            else if (msg.includes('[OK]')) htmlMsg = '<span class="text-green-500">' + msg + '</span>';
            
            const div = document.createElement('div');
            div.className = "text-gray-300 break-all border-l-2 border-terminal-gray pl-4 hover:border-primary transition-colors animate-fade-in";
            div.innerHTML = '<span class="text-gray-500 mr-4">[' + dateStr + ']</span> ' + htmlMsg;
            
            container.appendChild(div);
            
            // Auto scroll
            container.scrollTop = container.scrollHeight;
            
            // Keep only latest 100 logs
            if (container.children.length > 105) {
              container.removeChild(container.children[1]); // keep the > tail -f line
            }
          }, 1500 + Math.random() * 2000);
        });
      `}} />
        </div>
    );
}
