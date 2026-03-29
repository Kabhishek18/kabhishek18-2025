'use client';

import Link from "next/link";
import Image from "next/image";

export default function Contact() {
    return (
        <div className="min-h-screen bg-background-dark text-white font-sans flex overflow-hidden">
            {/* Sidebar / Terminal Directory Tree */}
            <aside className="w-64 border-r border-terminal-gray hidden md:flex flex-col bg-background-dark/95 backdrop-blur z-10 shrink-0">
                <div className="p-4 border-b border-terminal-gray">
                    <div className="flex items-center gap-2 text-primary">
                        <span className="material-symbols-outlined">terminal</span>
                        <span className="font-bold tracking-widest text-sm">TERM_V.1.0</span>
                    </div>
                </div>

                {/* User Image Area */}
                <div className="p-4 flex justify-center border-b border-terminal-gray bg-white/5">
                    <div className="w-full aspect-square bg-[#EAEAEA] relative overflow-hidden">
                        <Image
                            src="/static/avatar.png"
                            alt="User Avatar"
                            fill
                            className="object-cover grayscale"
                        />
                        {/* Scanline effect */}
                        <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] pointer-events-none mix-blend-overlay"></div>
                    </div>
                </div>

                <nav className="p-4 flex flex-col gap-6">
                    {/* User Profile Info */}
                    <div className="flex flex-col gap-2 pb-2">
                        <h3 className="text-sm font-bold text-white uppercase">KUMAR ABHISHEK</h3>
                        <p className="text-xs text-gray-400">Role: The Digital Architect</p>
                    </div>

                    {/* Directory Tree */}
                    <div className="flex flex-col gap-1 text-sm font-mono">
                        <div className="text-gray-500 uppercase text-xs tracking-wider mb-2">./ROOT_DIRECTORY</div>
                        <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1" href="/">
                            <span className="text-gray-600">├──</span>
                            <span className="material-symbols-outlined text-[18px] group-hover:text-primary">home</span>
                            <span>home.exe</span>
                        </a>
                        <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1" href="/#projects">
                            <span className="text-gray-600">├──</span>
                            <span className="material-symbols-outlined text-[18px] group-hover:text-primary">folder_open</span>
                            <span>projects/</span>
                        </a>
                        <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1 pl-4 border-l border-gray-800 ml-[7px]" href="/web_apps">
                            <span className="text-gray-600">├──</span>
                            <span className="material-symbols-outlined text-[18px] group-hover:text-primary">html</span>
                            <span>web_apps</span>
                        </a>
                        <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1 pl-4 border-l border-gray-800 ml-[7px]" href="/blog">
                            <span className="text-gray-600">└──</span>
                            <span className="material-symbols-outlined text-[18px] group-hover:text-primary">article</span>
                            <span>blog_dir</span>
                        </a>
                        <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1 mt-2" href="/static/resume.pdf" target="_blank" rel="noopener noreferrer">
                            <span className="text-gray-600">├──</span>
                            <span className="material-symbols-outlined text-[18px] group-hover:text-primary">description</span>
                            <span>resume.pdf</span>
                        </a>
                        <a className="group flex items-center gap-2 text-primary transition-colors py-1" href="/contact">
                            <span className="text-gray-600">├──</span>
                            <span className="material-symbols-outlined text-[18px]">call</span>
                            <span className="font-bold">contact.exe</span>
                        </a>
                        <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1" href="/logs">
                            <span className="text-gray-600">├──</span>
                            <span className="material-symbols-outlined text-[18px] group-hover:text-primary">history</span>
                            <span>logs/</span>
                        </a>
                        <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1" href="/config">
                            <span className="text-gray-600">└──</span>
                            <span className="material-symbols-outlined text-[18px] group-hover:text-primary">settings</span>
                            <span>config</span>
                        </a>
                    </div>
                </nav>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 flex flex-col w-full bg-background-dark relative">
                {/* Top Bar */}
                <header className="h-14 border-b border-terminal-gray flex items-center justify-between px-6 bg-background-dark/95 backdrop-blur sticky top-0 z-20">
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                        <span className="md:hidden material-symbols-outlined text-primary hover:text-white mr-2 text-xl cursor-not-allowed hidden">menu</span>
                        <span className="hidden sm:inline">root</span>
                        <span className="hidden sm:inline">@</span>
                        <span className="text-white hidden sm:inline">kabhishek18</span>
                        <span className="hidden sm:inline">:</span>
                        <span className="text-primary">~/portfolio/contact</span>
                    </div>
                    <div className="flex gap-4 text-xs font-mono text-primary">
                        <span className="hidden sm:inline-block">CPU: 12%</span>
                        <span className="hidden sm:inline-block">RAM: 4.2GB</span>
                        <span className="animate-pulse">● LIVE</span>
                    </div>
                </header>

                {/* Content Scrollable */}
                <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:p-10 space-y-10">

                    {/* Contact Header */}
                    <section className="border-l-2 border-primary pl-6 py-2">
                        <p className="text-primary text-sm mb-2 font-mono">&gt; init_communications_protocol...</p>
                        <h1 className="text-4xl md:text-5xl font-bold uppercase tracking-tighter text-white mb-4 leading-none">
                            ESTABLISH CONNECTION<br />
                            <span className="text-gray-600">{`//`} ENCRYPTED_CHANNEL</span>
                        </h1>
                        <p className="text-gray-400 max-w-2xl text-lg font-light leading-relaxed mb-6">
                            Looking to collaborate on a scalable distributed system, architect an AI-driven solution, or just want to say hi? Ping me through the secure channels below.
                        </p>
                    </section>

                    {/* Contact Grid */}
                    <section className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                        {/* Direct Links */}
                        <div className="flex flex-col gap-6 font-mono text-sm max-w-md">
                            <a href="mailto:kabhishek18@gmail.com" className="group flex items-center justify-between p-4 border border-terminal-gray hover:border-primary transition-all bg-white/5">
                                <div className="flex items-center gap-4">
                                    <span className="material-symbols-outlined text-primary text-2xl">mail</span>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">EMAIL</span>
                                        <span className="text-white group-hover:text-primary transition-colors">kabhishek18@gmail.com</span>
                                    </div>
                                </div>
                                <span className="text-xs text-gray-600 group-hover:text-primary">&gt; SEND</span>
                            </a>

                            <a href="https://www.linkedin.com/in/kabhishek18" target="_blank" rel="noopener noreferrer" className="group flex items-center justify-between p-4 border border-terminal-gray hover:border-primary transition-all bg-white/5">
                                <div className="flex items-center gap-4">
                                    <span className="material-symbols-outlined text-primary text-2xl">link</span>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">LINKEDIN</span>
                                        <span className="text-white group-hover:text-primary transition-colors">/in/kabhishek18</span>
                                    </div>
                                </div>
                                <span className="text-xs text-gray-600 group-hover:text-primary">&gt; VISIT</span>
                            </a>

                            <a href="http://github.com/Kabhishek18/" target="_blank" rel="noopener noreferrer" className="group flex items-center justify-between p-4 border border-terminal-gray hover:border-primary transition-all bg-white/5">
                                <div className="flex items-center gap-4">
                                    <span className="material-symbols-outlined text-primary text-2xl">code</span>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">GITHUB</span>
                                        <span className="text-white group-hover:text-primary transition-colors">Kabhishek18</span>
                                    </div>
                                </div>
                                <span className="text-xs text-gray-600 group-hover:text-primary">&gt; DECRYPT</span>
                            </a>

                            <div className="group flex items-center justify-between p-4 border border-terminal-gray bg-white/5">
                                <div className="flex items-center gap-4">
                                    <span className="material-symbols-outlined text-primary text-2xl">smartphone</span>
                                    <div className="flex flex-col">
                                        <span className="text-gray-500 text-xs">PHONE(INDIA)</span>
                                        <span className="text-white">+91-7053948103</span>
                                    </div>
                                </div>
                                <span className="text-xs text-gray-600">&gt; SECURE</span>
                            </div>
                        </div>

                        {/* Terminal Form Box */}
                        <div className="border border-terminal-gray p-6 bg-background-dark/50 relative">
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/50 to-transparent"></div>
                            <h3 className="text-primary text-sm font-mono mb-6 uppercase flex items-center gap-2">
                                <span className="material-symbols-outlined text-xl">send</span>
                                TRANSMIT_MESSAGE.sh
                            </h3>
                            <form className="flex flex-col gap-4 font-mono text-sm" action="#" method="POST" onSubmit={(e) => e.preventDefault()}>
                                <div className="flex flex-col gap-2">
                                    <label htmlFor="name" className="text-gray-500">&gt; Name_</label>
                                    <input type="text" id="name" className="bg-transparent border border-terminal-gray focus:border-primary p-2 text-white outline-none w-full" placeholder="Enter identification" />
                                </div>
                                <div className="flex flex-col gap-2">
                                    <label htmlFor="email" className="text-gray-500">&gt; Email_</label>
                                    <input type="email" id="email" className="bg-transparent border border-terminal-gray focus:border-primary p-2 text-white outline-none w-full" placeholder="Enter return address" />
                                </div>
                                <div className="flex flex-col gap-2">
                                    <label htmlFor="message" className="text-gray-500">&gt; Payload_</label>
                                    <textarea id="message" rows={5} className="bg-transparent border border-terminal-gray focus:border-primary p-2 text-white outline-none w-full resize-none custom-scrollbar" placeholder="Enter message payload"></textarea>
                                </div>
                                <button type="submit" className="mt-4 border border-primary text-primary hover:bg-primary hover:text-black py-3 px-6 transition-all uppercase flex items-center justify-center gap-2 font-bold group">
                                    <span className="material-symbols-outlined group-hover:animate-bounce">rocket_launch</span>
                                    EXECUTE_SEND
                                </button>
                            </form>
                        </div>
                    </section>

                </div>

                {/* Bottom Bar */}
                <footer className="h-10 border-t border-terminal-gray flex items-center justify-between px-6 text-[10px] font-mono text-gray-600 bg-background-dark shrink-0">
                    <span>© 2026 KABHISHEK18. ALL SYSTEMS NOMINAL.</span>
                    <div className="flex gap-4 uppercase tracking-widest hidden sm:flex">
                        <span>[CONTACT]</span>
                        <a href="http://github.com/Kabhishek18/" className="hover:text-primary transition-colors">[GITHUB]</a>
                        <a href="https://www.linkedin.com/in/kabhishek18" className="hover:text-primary transition-colors">[LINKEDIN]</a>
                    </div>
                </footer>
            </main>
        </div>
    );
}
