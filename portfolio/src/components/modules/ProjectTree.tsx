'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { projectsSchema, ProjectModule } from '@/lib/schemas/projects';

export default function ProjectTree() {
    const [activeProject, setActiveProject] = useState<ProjectModule | null>(null);

    return (
        <div className="w-full flex flex-col md:flex-row gap-8 border-t system-border pt-12 mt-12">

            {/* Directory Tree */}
            <div className="w-full md:w-1/2 flex flex-col font-mono text-sm md:text-base">
                <div className="text-muted mb-4 uppercase tracking-widest text-xs">
                    &gt; ls -la ./modules/active
                </div>

                <div className="flex flex-col gap-1">
                    {projectsSchema.map((project, index) => {
                        const isLast = index === projectsSchema.length - 1;
                        const prefix = isLast ? '└──' : '├──';
                        const isActive = activeProject?.id === project.id;

                        return (
                            <div
                                key={project.id}
                                className="flex items-start group cursor-pointer"
                                onMouseEnter={() => setActiveProject(project)}
                                onClick={() => setActiveProject(project)}
                            >
                                <span className="text-muted mr-2 whitespace-pre">{prefix}</span>
                                <span className={`transition-colors ${isActive ? 'text-accent bg-accent/10 px-1' : 'text-foreground group-hover:text-accent'}`}>
                                    {project.type === 'DIR' ? '[DIR]' : '[FILE]'} {project.name}
                                </span>
                                <span className="ml-auto text-muted text-xs opacity-0 group-hover:opacity-100 transition-opacity hidden sm:block">
                                    {project.size}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* File Preview Pane */}
            <div className="w-full md:w-1/2 min-h-64 border system-border p-4 bg-foreground/5 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-accent/20" />
                <div className="text-muted uppercase tracking-widest text-[10px] sm:text-xs mb-4 border-b system-border pb-2 flex justify-between">
                    <span>MODULE_INSPECTOR</span>
                    <span>{activeProject ? 'ACTIVE' : 'AWAITING_INPUT'}</span>
                </div>

                <AnimatePresence mode="wait">
                    {activeProject ? (
                        <motion.div
                            key={activeProject.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 10 }}
                            className="flex flex-col gap-4 font-mono text-sm"
                        >
                            <div className="flex flex-col gap-1">
                                <span className="text-xs text-muted">ID: {activeProject.id}</span>
                                <span className="text-xl font-bold text-accent uppercase">{activeProject.name}</span>
                            </div>

                            <p className="text-foreground/80 leading-relaxed border-l-2 border-accent pl-3 py-1">
                                {activeProject.description}
                            </p>

                            <div className="flex flex-col gap-2 mt-2">
                                <span className="text-xs text-muted uppercase">Tech_Stack:</span>
                                <div className="flex flex-wrap gap-2">
                                    {activeProject.tech.map(t => (
                                        <span key={t} className="bg-background border system-border px-2 py-1 text-xs text-foreground">
                                            {t}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <div className="flex gap-4 mt-4 text-xs">
                                <span className={`px-2 py-1 ${activeProject.status === 'ONLINE' ? 'bg-accent/20 text-accent' : 'bg-muted/20 text-muted'}`}>
                                    STAT: {activeProject.status}
                                </span>
                                <span className="text-muted py-1 border-b border-muted border-dashed">
                                    MODIFIED: {new Date(activeProject.lastModified).toLocaleDateString()}
                                </span>
                            </div>

                        </motion.div>
                    ) : (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="w-full h-full flex items-center justify-center text-muted"
                        >
                            <span className="animate-pulse">_ SELECT MODULE _</span>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

        </div>
    );
}
