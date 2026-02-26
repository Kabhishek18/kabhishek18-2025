"use client";

export default function Config() {
    return (
        <div className="min-h-screen bg-background-dark text-white font-sans flex overflow-hidden">
            {/* Sidebar hidden for brevity */}

            <main className="flex-1 flex flex-col w-full bg-background-dark relative">
                <header className="h-14 border-b border-terminal-gray flex items-center gap-4 px-6 bg-background-dark/95 backdrop-blur sticky top-0 z-20">
                    <a href="/" className="text-primary hover:text-white transition-colors flex items-center gap-1 bg-terminal-gray/20 px-2 py-1 border border-terminal-gray hover:border-primary shrink-0">
                        <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                        <span className="text-xs font-mono">cd ..</span>
                    </a>
                    <div className="flex items-center gap-2 text-sm text-gray-400">
                        <span className="hidden sm:inline">root</span>
                        <span className="hidden sm:inline">@</span>
                        <span className="text-white hidden sm:inline">kabhishek18</span>
                        <span className="hidden sm:inline">:</span>
                        <span className="text-primary">~/system/config</span>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:p-10 space-y-10 font-mono">

                    <section className="border-l-2 border-primary pl-6 py-2">
                        <p className="text-primary text-sm mb-2">&gt; sudo nano /etc/kabhishek18/config.json</p>
                        <h1 className="text-4xl md:text-5xl font-bold uppercase tracking-tighter text-white mb-4 leading-none font-sans">
                            SYSTEM CONFIGURATION<br />
                            <span className="text-gray-600">{`//`} PREFERENCES & ENVIRONMENT VARIABLES</span>
                        </h1>
                    </section>

                    <form className="max-w-3xl space-y-8" onSubmit={(e) => e.preventDefault()}>

                        <div className="space-y-4">
                            <h2 className="text-xl font-bold border-b border-terminal-gray pb-2 text-white">NETWORK & SECURITY</h2>

                            <div className="flex items-center justify-between p-4 border border-terminal-gray hover:border-primary transition-colors bg-white/5">
                                <div>
                                    <h3 className="text-white font-bold">Intrusion Detection System (IDS)</h3>
                                    <p className="text-xs text-gray-500 mt-1">Actively monitor and block unauthorized payload injections.</p>
                                </div>
                                <div className="relative inline-block w-12 mr-2 align-middle select-none">
                                    <input type="checkbox" name="toggle1" id="toggle1" className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 border-gray-600 appearance-none cursor-pointer transition-transform duration-200 ease-in-out checked:transform checked:translate-x-6 checked:border-primary" defaultChecked />
                                    <label htmlFor="toggle1" className="toggle-label block overflow-hidden h-6 rounded-full bg-gray-600 cursor-pointer"></label>
                                </div>
                            </div>

                            <div className="flex items-center justify-between p-4 border border-terminal-gray hover:border-primary transition-colors bg-white/5">
                                <div>
                                    <h3 className="text-white font-bold">End-to-End Encryption</h3>
                                    <p className="text-xs text-gray-500 mt-1">Enforce strict PGP encryption for all incoming communications.</p>
                                </div>
                                <div className="relative inline-block w-12 mr-2 align-middle select-none">
                                    <input type="checkbox" name="toggle2" id="toggle2" className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 border-gray-600 appearance-none cursor-pointer transition-transform duration-200 ease-in-out checked:transform checked:translate-x-6 checked:border-primary" defaultChecked />
                                    <label htmlFor="toggle2" className="toggle-label block overflow-hidden h-6 rounded-full bg-gray-600 cursor-pointer"></label>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h2 className="text-xl font-bold border-b border-terminal-gray pb-2 text-white">AI / LLM INTEGRATION</h2>

                            <div className="flex flex-col gap-2 p-4 border border-terminal-gray bg-white/5">
                                <label className="text-white font-bold">Primary Neural Network Protocol</label>
                                <div className="flex items-center gap-4 mt-2">
                                    <select className="bg-transparent border border-terminal-gray text-primary p-2 w-full max-w-xs focus:outline-none focus:border-primary cursor-pointer">
                                        <option value="gpt4o">OpenAI GPT-4o (Prod)</option>
                                        <option value="claude">Anthropic Claude 3.5</option>
                                        <option value="ollama">Local Llama 3 / Ollama</option>
                                        <option value="gemini">Google Gemini Pro</option>
                                    </select>
                                </div>
                            </div>

                            <div className="flex items-center justify-between p-4 border border-terminal-gray hover:border-primary transition-colors bg-white/5">
                                <div>
                                    <h3 className="text-white font-bold">Vector Database Sync</h3>
                                    <p className="text-xs text-gray-500 mt-1">Keep Pinecone indexes updated in real-time with application state.</p>
                                </div>
                                <div className="relative inline-block w-12 mr-2 align-middle select-none">
                                    <input type="checkbox" name="toggle3" id="toggle3" className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 border-gray-600 appearance-none cursor-pointer transition-transform duration-200 ease-in-out checked:transform checked:translate-x-6 checked:border-primary" defaultChecked />
                                    <label htmlFor="toggle3" className="toggle-label block overflow-hidden h-6 rounded-full bg-gray-600 cursor-pointer"></label>
                                </div>
                            </div>
                        </div>

                        <div className="pt-4">
                            <button type="submit" className="border border-primary text-primary hover:bg-primary hover:text-black py-3 px-8 transition-all uppercase flex items-center justify-center gap-2 font-bold group">
                                <span className="material-symbols-outlined group-hover:rotate-180 transition-transform">sync</span>
                                APPLY_CONFIGURATION
                            </button>
                        </div>

                    </form>

                </div>
            </main>

            {/* Basic styles for generic toggles to work in tailwind */}
            <style dangerouslySetInnerHTML={{
                __html: `
        .toggle-checkbox:checked { right: 0; background-color: #00ffcc; border-color: #00ffcc; }
        .toggle-checkbox:checked + .toggle-label { background-color: rgba(0, 255, 204, 0.2); }
      `}} />

        </div>
    );
}
