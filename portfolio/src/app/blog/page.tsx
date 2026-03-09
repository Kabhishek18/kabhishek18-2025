'use client';

import React from 'react';
import Link from 'next/link';

export default function BlogIndex() {
    return (
        <>
            <style dangerouslySetInnerHTML={{
                __html: `
        .binary-dither {
          filter: grayscale(100%) contrast(150%) brightness(80%);
          mix-blend-mode: hard-light;
        }
        .amber-glow {
          box-shadow: 0 0 15px 2px rgba(255, 176, 0, 0.2);
          border: 1px solid #FFB000;
        }
        /* Hover-Interference Effect */
        .hover-interference {
          transition: all 0.1s steps(3);
        }
        .hover-interference:hover {
          transform: translate(-1px, 1px);
          filter: drop-shadow(2px 0 0 rgba(255,0,0,0.5)) drop-shadow(-2px 0 0 rgba(0,255,255,0.5));
          background-color: rgba(255, 176, 0, 0.05);
        }
        .image-hover-interference:hover {
          filter: invert(10%) sepia(100%) hue-rotate(350deg) saturate(500%) contrast(200%);
        }
      `}} />

            {/* Main Layout Container */}
            <div className="flex-1 flex flex-col md:flex-row h-full w-full border-b border-zinc-800">

                {/* Sidebar Navigation */}
                <aside className="hidden md:flex w-64 flex-shrink-0 border-r border-zinc-800 bg-black z-10 flex-col">
                    <div className="p-4 border-b border-zinc-800">
                        <div className="flex items-center gap-2 text-[#FFB000]">
                            <span className="material-symbols-outlined">terminal</span>
                            <span className="font-bold tracking-widest text-sm text-[#FFB000]">TERM_V.1.0</span>
                        </div>
                    </div>
                    <nav className="p-4 flex flex-col gap-6 font-mono text-sm">
                        <div className="text-gray-500 uppercase text-xs tracking-wider mb-2">./ROOT_DIRECTORY</div>
                        <Link href="/" className="group flex items-center gap-2 text-white hover:text-[#FFB000] transition-colors py-1">
                            <span className="text-gray-600">├──</span>
                            <span className="material-symbols-outlined text-[18px]">home</span>
                            <span>index.sh</span>
                        </Link>
                        <div className="flex flex-col gap-1">
                            <div className="group flex items-center gap-2 text-[#FFB000] py-1 bg-[#FFB000]/10 border-l-2 border-[#FFB000] pl-2 -ml-[2px]">
                                <span className="text-gray-600 hidden">├──</span>
                                <span className="material-symbols-outlined text-[18px]">article</span>
                                <span>blog_dir/</span>
                            </div>
                            <div className="pl-6 flex flex-col gap-1 mt-1 text-gray-400 text-xs">
                                <div className="flex justify-between hover:text-white cursor-pointer">
                                    <span>- UI/UX</span>
                                    <span>(12)</span>
                                </div>
                                <div className="flex justify-between hover:text-white cursor-pointer">
                                    <span>- TERMINAL</span>
                                    <span>(08)</span>
                                </div>
                                <div className="flex justify-between hover:text-white cursor-pointer">
                                    <span>- OP_SEC</span>
                                    <span>(04)</span>
                                </div>
                            </div>
                        </div>
                    </nav>
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col w-full bg-black relative">
                    {/* Top Bar */}
                    <header className="h-14 border-b border-zinc-800 flex items-center justify-between px-6 bg-black/95 backdrop-blur sticky top-0 z-20">
                        <div className="flex items-center gap-2 text-sm text-gray-400 font-mono">
                            <Link href="/" className="md:hidden material-symbols-outlined text-[#FFB000] hover:text-white mr-2 text-xl">menu</Link>
                            <span className="hidden sm:inline">root</span>
                            <span className="hidden sm:inline">@</span>
                            <span className="text-white hidden sm:inline">kabhishek18</span>
                            <span className="hidden sm:inline">:</span>
                            <span className="text-[#FFB000]">~/blog_dir</span>
                        </div>
                        <div className="flex flex-1 max-w-sm mx-6 items-center bg-zinc-900 border border-zinc-700 px-3 py-1">
                            <span className="text-[#FFB000] font-bold mr-2">&gt;</span>
                            <input type="text" placeholder="grep --search..." className="bg-transparent border-none text-white focus:ring-0 text-xs font-mono w-full outline-none placeholder-zinc-500" />
                        </div>
                    </header>

                    <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-12">

                        <section className="border-l-2 border-[#FFB000] pl-6 py-2">
                            <p className="text-[#FFB000] text-sm mb-2 font-mono">&gt; ./exec fetch_logs --sort=DESC</p>
                            <h1 className="text-4xl md:text-5xl font-bold uppercase tracking-tighter text-white mb-4 leading-none">
                                SYS_BLOG_FEED
                            </h1>
                            <p className="text-gray-400 max-w-2xl text-sm font-mono leading-relaxed">
                                Aggregated low-res data artifacts and architectural notes. Showing [3] matched checksums.
                            </p>
                        </section>

                        {/* Blog Feed */}
                        <section className="space-y-8">
                            {/* Post 1 */}
                            <Link href="/blog/neural-net-visualizer" className="block border border-zinc-800 bg-black p-4 hover-interference group relative overflow-hidden">
                                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 relative z-10">
                                    <div className="md:col-span-4 border border-zinc-800 bg-zinc-900 h-48 relative overflow-hidden image-hover-interference cursor-pointer">
                                        <img src="https://images.unsplash.com/photo-1620721200059-009cf1097e3c?q=80&w=600&auto=format&fit=crop" alt="Abstract net" className="w-full h-full object-cover binary-dither opacity-70 group-hover:opacity-100 transition-opacity" />
                                        <div className="absolute inset-0 border border-[#FFB000] opacity-0 group-hover:opacity-100 transition-opacity amber-glow pointer-events-none"></div>
                                    </div>
                                    <div className="md:col-span-8 flex flex-col justify-between">
                                        <div>
                                            <div className="flex items-center gap-4 text-xs font-mono text-[#FFB000] mb-3">
                                                <span className="border border-[#FFB000]/30 px-2 py-0.5 bg-[#FFB000]/10">CHK: 0x8F92A</span>
                                                <span className="text-zinc-500">SIZE: 42KB</span>
                                                <span className="text-zinc-500">TAGS: [NEURAL_NET]</span>
                                            </div>
                                            <h2 className="text-2xl font-bold text-white uppercase group-hover:text-[#FFB000] transition-colors mb-4 inline-block border-b border-transparent group-hover:border-[#FFB000] pb-1">
                                                Neural Net Visualization Patterns
                                            </h2>
                                            <p className="text-zinc-400 font-mono text-sm leading-relaxed mb-4">
                                                Extracting monochromatic heatmaps from raw tensor data. Analyzing decompression artifacts in high-dimensional isometric spaces.
                                            </p>
                                        </div>
                                        <div className="flex items-center text-xs font-mono text-zinc-600 uppercase">
                                            <span>&gt; INITIATE_READ()</span>
                                        </div>
                                    </div>
                                </div>
                            </Link>

                            {/* Post 2 */}
                            <Link href="/blog/terminal-ui-manifesto" className="block border border-zinc-800 bg-black p-4 hover-interference group relative overflow-hidden">
                                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 relative z-10">
                                    <div className="md:col-span-4 border border-zinc-800 bg-zinc-900 h-48 relative overflow-hidden image-hover-interference cursor-pointer">
                                        <img src="https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?q=80&w=600&auto=format&fit=crop" alt="Binary code" className="w-full h-full object-cover binary-dither opacity-70 group-hover:opacity-100 transition-opacity" />
                                        <div className="absolute inset-0 border border-[#FFB000] opacity-0 group-hover:opacity-100 transition-opacity amber-glow pointer-events-none"></div>
                                    </div>
                                    <div className="md:col-span-8 flex flex-col justify-between">
                                        <div>
                                            <div className="flex items-center gap-4 text-xs font-mono text-[#FFB000] mb-3">
                                                <span className="border border-[#FFB000]/30 px-2 py-0.5 bg-[#FFB000]/10">CHK: 0xB4D11</span>
                                                <span className="text-zinc-500">SIZE: 18KB</span>
                                                <span className="text-zinc-500">TAGS: [UI/UX]</span>
                                            </div>
                                            <h2 className="text-2xl font-bold text-white uppercase group-hover:text-[#FFB000] transition-colors mb-4 inline-block border-b border-transparent group-hover:border-[#FFB000] pb-1">
                                                Terminal UI Manifesto
                                            </h2>
                                            <p className="text-zinc-400 font-mono text-sm leading-relaxed mb-4">
                                                Replacing standard web design with rigid grids, monospace typography, and stark borders. An exploration of the command-line aesthetic.
                                            </p>
                                        </div>
                                        <div className="flex items-center text-xs font-mono text-zinc-600 uppercase">
                                            <span>&gt; INITIATE_READ()</span>
                                        </div>
                                    </div>
                                </div>
                            </Link>
                        </section>
                    </div>
                </main>
            </div>
        </>
    );
}
