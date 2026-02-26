"use client";

export default function Error400() {
    return (
        <div className="min-h-screen bg-background-dark text-white font-sans flex overflow-hidden">
            <main className="flex-1 flex flex-col w-full bg-background-dark relative items-center justify-center p-6">
                <div className="text-center font-mono max-w-lg mx-auto border border-terminal-gray bg-black p-10 relative shadow-[0_0_15px_rgba(0,255,204,0.1)]">
                    <div className="absolute top-0 left-0 w-full h-1 bg-red-500"></div>

                    <h1 className="text-8xl md:text-9xl font-bold text-red-500 mb-2 tracking-tighter shadow-red-500/20 drop-shadow-lg">400</h1>

                    <div className="bg-red-500/10 text-red-400 py-2 px-4 mb-6 border border-red-500/30 inline-block font-bold tracking-widest text-sm uppercase">
                        &gt; SYS_ERR: BAD_REQUEST
                    </div>

                    <p className="text-gray-400 mb-10 leading-relaxed text-sm">
                        The payload provided was malformed or failed validation checks. Please verify your transmission protocol and try again.
                    </p>

                    <a href="/" className="inline-flex items-center gap-2 border border-primary text-primary hover:bg-primary hover:text-black py-3 px-8 transition-all uppercase font-bold group text-sm">
                        <span className="material-symbols-outlined group-hover:rotate-180 transition-transform">terminal</span>
                        RETURN_TO_MAINFRAME
                    </a>
                </div>
            </main>
        </div>
    );
}
