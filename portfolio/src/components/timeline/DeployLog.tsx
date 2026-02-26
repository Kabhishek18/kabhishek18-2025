'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { experienceSchema } from '@/lib/schemas/experience';

export default function DeployLog() {
    return (
        <div className="w-full border-t system-border pt-12 mt-12 mb-24 font-mono">

            <div className="text-muted mb-8 uppercase tracking-widest text-xs flex items-center gap-2">
                <span className="w-2 h-2 bg-accent rounded-sm animate-pulse" />
                tail -f /var/log/career/deployment.log
            </div>

            <div className="relative border-l system-border ml-3 md:ml-4 flex flex-col gap-8 pb-8">

                {experienceSchema.map((log, index) => {

                    const isSuccess = log.event === 'DEPLOY' || log.event === 'UPDATE';
                    const isWarning = log.event === 'WARN';
                    const iconColor = isSuccess ? 'bg-accent' : isWarning ? 'bg-yellow-500' : 'bg-muted';
                    const textColor = isSuccess ? 'text-accent' : isWarning ? 'text-yellow-500' : 'text-muted';

                    return (
                        <motion.div
                            key={log.id}
                            initial={{ opacity: 0, y: 10 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{ delay: index * 0.15 }}
                            className="relative pl-8 md:pl-12 group"
                        >
                            {/* Node Point */}
                            <div className={`absolute -left-[5px] top-1.5 w-[9px] h-[9px] ${iconColor} border border-background shadow-[0_0_8px_var(--accent-color)] ${isSuccess ? 'shadow-accent/50' : 'shadow-none'}`} />

                            {/* Horizontal Connector */}
                            <div className="absolute left-0 top-2.5 w-6 md:w-8 h-px bg-border group-hover:bg-accent/50 transition-colors" />

                            <div className="flex flex-col gap-1 max-w-3xl">
                                {/* Timestamp & Event */}
                                <div className="flex flex-wrap items-center gap-2 md:gap-4 text-xs font-bold">
                                    <span className="text-muted tracking-tighter">[{log.timestamp}]</span>
                                    <span className={`px-1.5 py-0.5 text-[10px] ${iconColor} text-background`}>
                                        {log.event}
                                    </span>
                                    <span className={`${textColor} uppercase`}>{log.title}</span>
                                </div>

                                {/* Log Message */}
                                <div className="mt-2 text-sm md:text-base text-foreground/90 leading-relaxed border-l-2 system-border pl-4 py-1 group-hover:border-accent/40 transition-colors">
                                    <span className="opacity-0 animate-[blink_0.1s_ease-in-out_forwards]" style={{ animationDelay: `${(index * 0.15) + 0.2}s` }}>
                                        {log.message}
                                    </span>
                                </div>

                                {/* Metadata */}
                                {log.duration && (
                                    <div className="mt-2 flex gap-4 text-xs text-muted">
                                        <span className="border system-border px-1.5 py-0.5">TIME_ELAPSED: {log.duration}</span>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    );
                })}

                {/* Typing cursor indicating active tracking */}
                <div className="relative pl-8 md:pl-12 mt-4">
                    <div className="absolute -left-[3px] top-1.5 w-[5px] h-[5px] rounded-full bg-border" />
                    <span className="w-2 h-4 bg-accent animate-blink inline-block" />
                </div>

            </div>
        </div>
    );
}
