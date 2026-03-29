import React from 'react';
import Link from 'next/link';

export async function generateStaticParams() {
    return [
        { slug: 'neural-net-visualizer' },
        { slug: 'terminal-ui' },
    ];
}

export default function BlogDetail({ params }: { params: { slug: string } }) {

    return (
        <>
            <style dangerouslySetInnerHTML={{
                __html: `
        .binary-dither {
          filter: grayscale(100%) contrast(150%) brightness(80%);
          mix-blend-mode: hard-light;
        }
        .monochromatic-heatmap {
          filter: sepia(100%) hue-rotate(90deg) saturate(300%) contrast(150%);
          mix-blend-mode: screen;
        }
        /* Glitch Decompression Effect */
        .glitch-architecture {
          position: relative;
        }
        .glitch-architecture::before {
          content: "";
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(255, 176, 0, 0.1) 2px,
            rgba(255, 176, 0, 0.1) 4px
          );
          pointer-events: none;
          z-index: 10;
        }
        .glitch-architecture:hover img {
          animation: glitch-anim 0.2s linear infinite alternate-reverse;
        }
        @keyframes glitch-anim {
          0% { transform: translate(0) }
          20% { transform: translate(-2px, 2px) }
          40% { transform: translate(-2px, -2px) }
          60% { transform: translate(2px, 2px) }
          80% { transform: translate(2px, -2px) }
          100% { transform: translate(0) }
        }
        .image-hover-interference:hover {
          filter: invert(10%) sepia(100%) hue-rotate(350deg) saturate(500%) contrast(200%);
        }
        .line-numbers {
            user-select: none;
            text-align: right;
            padding-right: 1.5rem;
            color: #4b5563;
        }
      `}} />

            <div className="flex-1 flex overflow-hidden">

                {/* Left Sidebar (Explorer) */}
                <aside className="hidden lg:flex w-48 flex-shrink-0 border-r border-zinc-800 flex-col bg-black">
                    <div className="p-4 text-[10px] text-gray-500 uppercase tracking-widest border-b border-zinc-800">Explorer</div>
                    <nav className="p-2 text-xs font-mono">
                        <Link href="/blog" className="flex items-center gap-2 py-1 text-gray-400 hover:text-white cursor-pointer pl-2">
                            <span className="text-[#FFB000]">&lt;</span>
                            <span>cd ..</span>
                        </Link>
                        <div className="flex items-center gap-2 py-1 text-gray-400 mt-2">
                            <span className="material-symbols-outlined text-sm">folder_open</span>
                            <span>blog_dir/</span>
                        </div>
                        <div className="pl-4 space-y-1">
                            <div className="flex items-center gap-2 py-1 text-[#FFB000] bg-[#FFB000]/10 border-l-2 border-[#FFB000] pl-2 -ml-[2px]">
                                <span className="material-symbols-outlined text-sm">description</span>
                                <span className="truncate">{params?.slug || 'neural-net-visualizer'}.md</span>
                            </div>
                            <div className="flex items-center gap-2 py-1 text-gray-500 hover:text-white cursor-pointer pl-2">
                                <span className="material-symbols-outlined text-sm">description</span>
                                <span className="truncate">terminal-ui.md</span>
                            </div>
                        </div>
                    </nav>
                </aside>

                {/* Main Editor Content */}
                <main className="flex-1 flex flex-col relative bg-black overflow-hidden border-r border-zinc-800">
                    <div className="bg-zinc-900/50 px-4 py-2 text-xs border-b border-zinc-800 flex items-center gap-2 text-gray-400 font-mono">
                        <Link href="/blog" className="lg:hidden material-symbols-outlined text-[#FFB000] hover:text-white mr-2 text-base">arrow_back</Link>
                        <span className="text-[#FFB000] hidden sm:inline">$</span>
                        <span className="hidden sm:inline">cat /blog_dir/{params?.slug || 'neural-net-visualizer'}.md</span>
                        <span className="sm:hidden text-white truncate max-w-[200px]">{params?.slug}.md</span>
                    </div>

                    <div className="flex-1 overflow-y-auto flex custom-scrollbar pb-20">
                        {/* Line Numbers */}
                        <div className="line-numbers py-6 px-2 sm:px-4 text-[10px] sm:text-xs font-mono min-w-[40px] sm:min-w-[60px] bg-[#050505] border-r border-zinc-800">
                            1<br />2<br />3<br />4<br />5<br />6<br />7<br />8<br />9<br />10<br />11<br />12<br />13<br />14<br />15<br />16<br />17<br />18<br />19<br />20<br />21<br />22<br />23<br />24<br />25<br />26<br />27<br />28<br />29<br />30<br />31<br />32<br />33<br />34<br />35
                        </div>

                        {/* Article Content */}
                        <div className="flex-1 p-6 md:p-10 max-w-4xl font-mono text-sm">

                            {/* JSON Frontmatter metadata */}
                            <div className="mb-10 text-zinc-400">
                                <span className="text-[#FFB000]">{'{'}</span><br />
                                <span className="pl-4">&quot;title&quot;: &quot;<span className="text-white">Neural Net Visualization Patterns</span>&quot;,</span><br />
                                <span className="pl-4">&quot;author&quot;: &quot;<span className="text-white">Kabhishek18</span>&quot;,</span><br />
                                <span className="pl-4">&quot;checksum&quot;: &quot;<span className="text-[#FFB000]">0x8F92A</span>&quot;,</span><br />
                                <span className="pl-4">&quot;tags&quot;: [&quot;<span className="text-zinc-200">AI</span>&quot;, &quot;<span className="text-zinc-200">Terminal</span>&quot;]</span><br />
                                <span className="text-[#FFB000]">{'}'}</span>
                            </div>

                            <div className="prose prose-invert max-w-none space-y-8 font-mono">
                                <h1 className="text-3xl font-bold text-white border-b border-dashed border-[#FFB000] pb-2 uppercase tracking-tight">
                                    # Abstract: High-Dimensional Artifacts
                                </h1>

                                {/* Glitch-Architecture Hero Image */}
                                <div className="border border-zinc-800 p-2 bg-[#050505]">
                                    <div className="relative glitch-architecture h-64 md:h-96 overflow-hidden cursor-crosshair">
                                        <img
                                            src="https://images.unsplash.com/photo-1620721200059-009cf1097e3c?q=80&w=1200&auto=format&fit=crop"
                                            alt="Neural Network Geometric Wireframe"
                                            className="w-full h-full object-cover binary-dither image-hover-interference transition-all duration-300"
                                        />
                                        <div className="absolute top-2 left-2 bg-black/80 border border-[#FFB000] px-2 py-1 text-[10px] text-[#FFB000]">
                                            FIG_1: DECOMPRESSION_ARTIFACT_09
                                        </div>
                                    </div>
                                </div>

                                <p className="leading-relaxed text-zinc-300">
                                    The decompression of high-dimensional neural network state data into a human-readable 3D viewport inevitably introduces rendering artifacts. By utilizing <span className="text-[#FFB000]">isometric wireframe mapping</span> and raw heatmap data, we can accurately expose the hidden layers of the model without sacrificing visual precision.
                                </p>

                                <h2 className="text-xl font-bold text-white uppercase tracking-wider mt-12 mb-6">
                                    &gt; Monochromatic Heatmap Extraction Let
                                </h2>

                                <p className="text-zinc-500 italic border-l-2 border-[#FFB000] pl-4">
                                    &quot;When you stare into the weights, the weights stare back into you.&quot; - SYS_ADMIN
                                </p>

                                {/* Monochromatic Technical Diagram */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 my-8">
                                    <div className="border border-zinc-800 bg-[#050505] p-2 aspect-square relative hover:border-[#FFB000] transition-colors group">
                                        <img
                                            src="https://images.unsplash.com/photo-1550745165-9bc0b252726f?q=80&w=600&auto=format&fit=crop"
                                            alt="Monochromatic Layer Heatmap"
                                            className="w-full h-full object-cover monochromatic-heatmap opacity-80 group-hover:opacity-100 transition-opacity"
                                        />
                                        <div className="absolute bottom-2 right-2 text-[10px] text-[#00FF41] bg-black px-1 font-bold">
                                            DATA_SET_A [ACTIVE]
                                        </div>
                                    </div>
                                    <div className="flex flex-col justify-center space-y-4">
                                        <div className="text-xs text-zinc-400 border-b border-zinc-800 pb-2">
                                            <span className="text-[#FFB000]">PARAM_01</span>: Thermal Distribution across hidden nodes.
                                        </div>
                                        <div className="bg-zinc-900/50 p-4 border border-zinc-800 text-xs">
                                            <span className="text-zinc-600">{`// Compute shader allocation`}</span><br />
                                            <span className="text-[#FFB000]">void</span> main() {'{'}<br />
                                            <span className="pl-4 text-zinc-300">vec4 tensor_val = texture2D(u_data, v_uv);</span><br />
                                            <span className="pl-4 text-zinc-300">gl_FragColor = apply_thermal(tensor_val);</span><br />
                                            {'}'}
                                        </div>
                                    </div>
                                </div>

                                <p className="leading-relaxed text-zinc-300">
                                    Notice the structural integrity remains intact even when subjected to extreme noise scaling. This approach ensures maximum stability across low-spec hardware rendering cycles while fitting perfectly into the overarching CLI aesthetic.
                                </p>

                                <div className="mt-12 pt-8 border-t border-zinc-800 flex items-center text-xs text-zinc-500 justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-[#FFB000] font-bold">kabhishek18@terminal:~/blog$</span>
                                        <span className="text-white animate-pulse">_</span>
                                    </div>
                                    <div>
                                        [EOF]
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Bottom Editor Bar */}
                    <div className="absolute bottom-0 left-0 right-0 h-8 border-t border-zinc-800 bg-[#050505] flex items-center px-4 justify-between text-[10px] uppercase text-zinc-500 font-bold z-20">
                        <div className="flex gap-4">
                            <span>Line: 24/50</span>
                            <span>Col: 1</span>
                            <span>MD_EXT</span>
                        </div>
                        <div className="flex gap-4">
                            <span className="text-[#FFB000] hover:text-white cursor-pointer">[SAVE: ^O]</span>
                            <Link href="/blog" className="text-[#FFB000] hover:text-white cursor-pointer">[EXIT: ^X]</Link>
                        </div>
                    </div>
                </main>

                {/* Right Sidebar (Agent Status / Document Metadata) */}
                <aside className="hidden xl:flex w-72 flex-col bg-black p-6 space-y-8 overflow-y-auto">
                    <div>
                        <h3 className="text-xs font-bold text-white uppercase mb-4 border-b border-zinc-800 pb-2 flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm text-[#FFB000]">info</span>
                            Document_Metadata
                        </h3>
                        <div className="space-y-3 text-[11px] font-mono">
                            <div className="flex justify-between">
                                <span className="text-zinc-500">FORMAT:</span>
                                <span className="text-white">Markdown</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-zinc-500">SIZE:</span>
                                <span className="text-white">42.5 KB</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-zinc-500">ENCODING:</span>
                                <span className="text-white">UTF-8</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-zinc-500">OWNER:</span>
                                <span className="text-white">admin_k18</span>
                            </div>
                            <div className="flex justify-between mt-4 border-t border-zinc-800 pt-3">
                                <span className="text-zinc-500">CHECKSUM:</span>
                                <span className="text-[#FFB000]">0x8F92A</span>
                            </div>
                        </div>
                    </div>
                    <div>
                        <h3 className="text-xs font-bold text-white uppercase mb-4 border-b border-zinc-800 pb-2 flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm text-[#FFB000]">monitoring</span>
                            Reading_Progress
                        </h3>
                        <div className="space-y-4">
                            <div>
                                <div className="flex justify-between text-[10px] text-zinc-500 mb-1 font-mono">
                                    <span>SCROLL_DEPTH</span>
                                    <span>42%</span>
                                </div>
                                <div className="w-full bg-zinc-900 h-1">
                                    <div className="bg-[#FFB000] h-1 w-[42%]"></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between text-[10px] text-zinc-500 mb-1 font-mono">
                                    <span>NETWORK_IO</span>
                                    <span>128 kb/s</span>
                                </div>
                                <div className="w-full bg-zinc-900 h-1 overflow-hidden relative">
                                    <div className="absolute inset-0 bg-[#FFB000]/20 animate-pulse"></div>
                                    <div className="bg-[#FFB000] h-1 w-[65%] relative z-10 transition-all duration-1000"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="flex-1 flex flex-col justify-end">
                        <div className="bg-[#FFB000]/5 border border-[#FFB000]/20 p-3 text-[10px] text-[#FFB000] font-mono leading-tight">
                            <p>&gt; System monitoring active</p>
                            <p>&gt; Rendering buffer... [OK]</p>
                            <p>&gt; Connection secure</p>
                            <p className="text-white animate-pulse">_</p>
                        </div>
                    </div>
                </aside>

            </div>
        </>
    );
}
