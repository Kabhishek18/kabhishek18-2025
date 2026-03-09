import Image from "next/image";

export default function WebApps() {
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
                        <span className="text-primary">~/projects/web_apps</span>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:p-10 space-y-10">

                    <section className="border-l-2 border-primary pl-6 py-2">
                        <p className="text-primary text-sm mb-2 font-mono">&gt; load_module ai_systems.so</p>
                        <h1 className="text-4xl md:text-5xl font-bold uppercase tracking-tighter text-white mb-4 leading-none">
                            INTELLIGENT SYSTEMS<br />
                            <span className="text-gray-600">{`//`} GEN_AI_&_ML_PIPELINES</span>
                        </h1>
                        <p className="text-gray-400 max-w-2xl text-lg font-light leading-relaxed">
                            A curated selection of robust AI integrations, LLM-powered agents, and scalable machine learning architectures engineered for production environments.
                        </p>
                    </section>

                    <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">

                        {/* App Card 1 */}
                        <div className="border border-terminal-gray bg-background-dark/50 hover:border-primary transition-colors group flex flex-col h-full">
                            <div className="p-4 border-b border-terminal-gray flex justify-between items-center group-hover:bg-primary/5 transition-colors">
                                <h3 className="font-bold text-lg group-hover:text-primary">Simkey (HERKEY)</h3>
                                <span className="material-symbols-outlined text-gray-500 group-hover:text-primary">memory</span>
                            </div>
                            <div className="p-6 flex-1 flex flex-col gap-4">
                                <p className="text-sm text-gray-400 leading-relaxed">
                                    Architected and deployed an advanced AI-driven matching engine scaling to millions of users. Engineered custom RAG pipelines and highly optimized semantic vector search.
                                </p>
                                <div className="flex flex-wrap gap-2 mt-auto pt-4">
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">PyTorch</span>
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">LangChain</span>
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">Pinecone</span>
                                </div>
                            </div>
                        </div>

                        {/* App Card 2 */}
                        <div className="border border-terminal-gray bg-background-dark/50 hover:border-primary transition-colors group flex flex-col h-full">
                            <div className="p-4 border-b border-terminal-gray flex justify-between items-center group-hover:bg-primary/5 transition-colors">
                                <h3 className="font-bold text-lg group-hover:text-primary">HERKEY 4.0</h3>
                                <span className="material-symbols-outlined text-gray-500 group-hover:text-primary">hub</span>
                            </div>
                            <div className="p-6 flex-1 flex flex-col gap-4">
                                <p className="text-sm text-gray-400 leading-relaxed">
                                    Spearheaded the backend machine learning infrastructure for India's largest women's career network. Automated data pipelines yielding a 40% reduction in inference latency.
                                </p>
                                <div className="flex flex-wrap gap-2 mt-auto pt-4">
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">AWS SageMaker</span>
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">FastAPI</span>
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">PostgreSQL</span>
                                </div>
                            </div>
                        </div>

                        {/* App Card 3 */}
                        <div className="border border-terminal-gray bg-background-dark/50 hover:border-primary transition-colors group flex flex-col h-full">
                            <div className="p-4 border-b border-terminal-gray flex justify-between items-center group-hover:bg-primary/5 transition-colors">
                                <h3 className="font-bold text-lg group-hover:text-primary">AIRBUS PLM</h3>
                                <span className="material-symbols-outlined text-gray-500 group-hover:text-primary">model_training</span>
                            </div>
                            <div className="p-6 flex-1 flex flex-col gap-4">
                                <p className="text-sm text-gray-400 leading-relaxed">
                                    Developed predictive analytics and reporting models within the Capgemini team to process and derive insights from massive Product Lifecycle Management datasets.
                                </p>
                                <div className="flex flex-wrap gap-2 mt-auto pt-4">
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">TensorFlow</span>
                                    <span className="px-2 py-1 bg-white/5 border border-terminal-gray text-xs font-mono text-gray-300">Big Data BI</span>
                                </div>
                            </div>
                        </div>

                    </section>
                </div>
            </main>
        </div>
    );
}
