'use client';

import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <>
      {/* Scanline Overlay */}
      <div className="scanlines"></div>

      {/* Main Layout Container */}
      <div className="flex-1 flex flex-col md:flex-row h-full w-full border-b border-terminal-gray">

        {/* Sidebar Navigation (Directory Tree) */}
        <aside className="hidden md:block w-64 flex-shrink-0 border-r border-terminal-gray bg-background-dark z-10">
          <div className="p-4 border-b border-terminal-gray">
            <div className="flex items-center gap-2 text-primary">
              <span className="material-symbols-outlined">terminal</span>
              <span className="font-bold tracking-widest text-sm">TERM_V.1.0</span>
            </div>
          </div>
          {/* User Profile Image */}
          <div className="relative w-full aspect-square overflow-hidden bg-terminal-gray grayscale hover:grayscale-0 transition-all border-b border-terminal-gray">
            <img alt="User Avatar" className="w-full h-full object-cover object-top" data-alt="Pixelated avatar of a developer" src="/static/avatar.png" />
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
              <a className="group flex items-center gap-2 text-white hover:text-primary transition-colors py-1" href="/contact">
                <span className="text-gray-600">├──</span>
                <span className="material-symbols-outlined text-[18px] group-hover:text-primary">call</span>
                <span>contact.exe</span>
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
              <span className="text-primary">~/portfolio</span>
            </div>
            <div className="flex gap-4 text-xs font-mono text-primary">
              <span className="hidden sm:inline-block">CPU: 12%</span>
              <span className="hidden sm:inline-block">RAM: 4.2GB</span>
              <span className="animate-pulse">● LIVE</span>
            </div>
          </header>

          {/* Content Scrollable */}
          <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:p-10 space-y-16">

            {/* Hero Section */}
            <section className="border-l-2 border-primary pl-6 py-2">
              <p className="text-primary text-sm mb-2 font-mono">&gt; initialize_sequence_alpha_01...</p>
              <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold uppercase tracking-tighter text-white mb-4 leading-none">
                KUMAR ABHISHEK<br />
                <span className="text-gray-600">{`//`} THE DIGITAL ARCHITECT</span>
              </h1>
              <p className="text-gray-400 max-w-2xl text-lg font-light leading-relaxed">
                Senior AI & ML Engineer with 7.8+ years of experience architecting scalable distributed systems and intelligent generative pipelines. Expert in Python, Django, and deploying production-grade RAG architectures (LangChain, Ollama). Renowned for mastering complex data architectures and engineering ultra-low-latency, resilient machine learning models at scale.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-4 max-w-lg">
                <div className="flex items-center bg-terminal-gray/30 border border-primary/50 w-full p-2">
                  <span className="text-primary mr-2 font-bold">&gt;</span>
                  <input className="bg-transparent border-none text-white w-full focus:ring-0 placeholder-gray-600 font-mono text-sm outline-none" placeholder="run contact_protocol.exe" type="text" />
                  <div className="w-3 h-5 bg-primary cursor-blink"></div>
                </div>
              </div>
            </section>

            {/* Stats Grid */}
            <section className="grid grid-cols-2 md:grid-cols-4 border-t border-terminal-gray">
              <div className="p-4 border-r border-b border-terminal-gray hover:bg-white/5 transition-colors group">
                <span className="text-xs text-gray-500 uppercase tracking-widest block mb-1 group-hover:text-primary">Experience</span>
                <span className="text-2xl font-bold text-white">7.8 YRS</span>
              </div>
              <div className="p-4 border-r border-b border-terminal-gray hover:bg-white/5 transition-colors group">
                <span className="text-xs text-gray-500 uppercase tracking-widest block mb-1 group-hover:text-primary">Commits</span>
                <span className="text-2xl font-bold text-white">8,492</span>
              </div>
              <div className="p-4 border-r border-b border-terminal-gray hover:bg-white/5 transition-colors group">
                <span className="text-xs text-gray-500 uppercase tracking-widest block mb-1 group-hover:text-primary">Projects</span>
                <span className="text-2xl font-bold text-white">42</span>
              </div>
              <div className="p-4 border-b border-terminal-gray hover:bg-white/5 transition-colors group">
                <span className="text-xs text-gray-500 uppercase tracking-widest block mb-1 group-hover:text-primary">Status</span>
                <span className="text-2xl font-bold text-primary">ONLINE</span>
              </div>
            </section>

            {/* System Logs (Experience) */}
            <section>
              <div className="flex items-center justify-between mb-6 border-b border-terminal-gray pb-2">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">history</span>
                  SYSTEM_LOGS
                </h2>
                <span className="text-xs text-gray-500 font-mono">[MODE: CHRONOLOGICAL]</span>
              </div>
              <div className="font-mono text-sm space-y-1">
                {/* Log Entry 1: HerKey */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 hover:bg-terminal-gray/20 p-2 border-l border-transparent hover:border-primary transition-all">
                  <div className="md:col-span-2 text-gray-500">2023-05-01 <span className="text-gray-700">PRESENT</span></div>
                  <div className="md:col-span-2 text-primary">SYS_LEAD</div>
                  <div className="md:col-span-8 text-gray-300">
                    <span className="text-white font-bold">Senior Software Tech Lead @ HERKEY</span>
                    <br /><span className="text-gray-500">&gt; Orchestrated HERKEY 4.0 migration with 99.9% uptime. Architected Agentic AI (Simkey) using LangChain & Ollama. Optimized Data Engineering ELT workflows.</span>
                  </div>
                </div>
                {/* Log Entry 2: Capgemini */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 hover:bg-terminal-gray/20 p-2 border-l border-transparent hover:border-primary transition-all">
                  <div className="md:col-span-2 text-gray-500">2021-08-01 <span className="text-gray-700">2023-04-30</span></div>
                  <div className="md:col-span-2 text-blue-400">SYS_UPDATE</div>
                  <div className="md:col-span-8 text-gray-300">
                    <span className="text-white font-bold">Senior Software Developer @ Capgemini</span>
                    <br /><span className="text-gray-500">&gt; Led AIRBUS PLM Engineering ADB integration. Developed AI-driven anomaly detection models. Modernized legacy DQC architectures.</span>
                  </div>
                </div>
                {/* Log Entry 3: Softwill */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 hover:bg-terminal-gray/20 p-2 border-l border-transparent hover:border-primary transition-all">
                  <div className="md:col-span-2 text-gray-500">2019-06-01 <span className="text-gray-700">2020-10-31</span></div>
                  <div className="md:col-span-2 text-yellow-500">NET_BUILD</div>
                  <div className="md:col-span-8 text-gray-300">
                    <span className="text-white font-bold">Full Stack Developer @ SOFTWILL Infotech</span>
                    <br /><span className="text-gray-500">&gt; Deployed ERP/CRM full-stack solutions. Integrated STRIPE payment gateways and built complex RBAC systems.</span>
                  </div>
                </div>
                {/* Log Entry 4: Bird Global */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 hover:bg-terminal-gray/20 p-2 border-l border-transparent hover:border-primary transition-all">
                  <div className="md:col-span-2 text-gray-500">2017-08-01 <span className="text-gray-700">2019-05-31</span></div>
                  <div className="md:col-span-2 text-gray-400">INIT_BOOT</div>
                  <div className="md:col-span-8 text-gray-300">
                    <span className="text-white font-bold">Junior Associate Engineer @ Bird Global</span>
                    <br /><span className="text-gray-500">&gt; Engineered ETL workflows reducing data processing time by 40%. Built resilient REST APIs and Celery tasks.</span>
                  </div>
                </div>
              </div>
            </section>

            {/* Core Competencies (Skills) */}
            <section>
              <div className="flex items-center justify-between mb-6 border-b border-terminal-gray pb-2">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">memory</span>
                  CORE_COMPETENCIES
                </h2>
                <span className="text-xs text-gray-500 font-mono">cat /sys/skills.var</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-sm">

                <div className="border border-terminal-gray p-4 bg-background-dark/50 group hover:border-primary transition-colors">
                  <h3 className="text-primary text-xs uppercase tracking-widest mb-3 border-b border-terminal-gray pb-1 group-hover:border-primary">Backend_Engineering</h3>
                  <ul className="text-gray-400 space-y-1">
                    <li>Python</li>
                    <li>Django / Flask</li>
                    <li>Microservices</li>
                    <li>RESTful APIs</li>
                  </ul>
                </div>

                <div className="border border-terminal-gray p-4 bg-background-dark/50 group hover:border-yellow-500 transition-colors">
                  <h3 className="text-yellow-500 text-xs uppercase tracking-widest mb-3 border-b border-terminal-gray pb-1 group-hover:border-yellow-500">AI_&_Machine_Learning</h3>
                  <ul className="text-gray-400 space-y-1">
                    <li>LLMs / LangChain</li>
                    <li>RAG / Ollama</li>
                    <li>Hugging Face</li>
                    <li>TensorFlow / PyTorch</li>
                  </ul>
                </div>

                <div className="border border-terminal-gray p-4 bg-background-dark/50 group hover:border-blue-400 transition-colors">
                  <h3 className="text-blue-400 text-xs uppercase tracking-widest mb-3 border-b border-terminal-gray pb-1 group-hover:border-blue-400">Data_&_Cloud_Infra</h3>
                  <ul className="text-gray-400 space-y-1">
                    <li>AWS EC2 / S3</li>
                    <li>Docker / Kubernetes</li>
                    <li>MongoDB / Redis / SQL</li>
                    <li>Celery / ETL Pipelines</li>
                  </ul>
                </div>

                <div className="border border-terminal-gray p-4 bg-background-dark/50 group hover:border-white transition-colors">
                  <h3 className="text-white text-xs uppercase tracking-widest mb-3 border-b border-terminal-gray pb-1 group-hover:border-white">Frontend_&_Misc</h3>
                  <ul className="text-gray-400 space-y-1">
                    <li>JavaScript</li>
                    <li>React Native</li>
                    <li>HTML5 / CSS3</li>
                    <li>Agile / CI/CD</li>
                  </ul>
                </div>

              </div>
            </section>

            {/* Project Directory (Cards) */}
            <section>
              <div className="flex items-center justify-between mb-6 border-b border-terminal-gray pb-2">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">folder_special</span>
                  PROJECT_DIRECTORY
                </h2>
                <span className="text-xs text-gray-500 font-mono">ls -la ./projects</span>
              </div>
              <div id="github-projects-container" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0 border border-terminal-gray">
                {/* Repositories will be injected here via github_fetcher.js */}
                <div className="p-6 text-gray-500 font-mono col-span-full">
                  &gt; Fetching remote repositories from GitHub...
                  <span className="animate-pulse inline-block w-2 bg-primary h-4 ml-1"></span>
                </div>
              </div>
            </section>

            <footer className="border-t border-terminal-gray pt-8 pb-4 text-xs font-mono text-gray-500 flex justify-between items-center">
              <div>
                <p>© 2026 KABHISHEK18. ALL SYSTEMS NOMINAL.</p>
              </div>
              <div className="flex gap-4">
                <a className="hover:text-primary transition-colors" href="https://github.com/Kabhishek18?tab=repositories" target="_blank" rel="noopener noreferrer">[GITHUB]</a>
                <a className="hover:text-primary transition-colors" href="https://www.linkedin.com/in/kabhishek18/" target="_blank" rel="noopener noreferrer">[LINKEDIN]</a>
                <a className="hover:text-primary" href="#">[TWITTER]</a>
              </div>
            </footer>
          </div>
        </main>

        {/* Right Sidebar (Agent Status) */}
        <aside className="flex w-full xl:w-72 border-t md:border-t-0 border-l-0 md:border-l border-terminal-gray bg-background-dark flex-col z-10">
          <div className="p-4 border-b border-terminal-gray">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <span className="w-2 h-2 bg-primary rounded-full animate-pulse"></span>
              Agent_Status
            </h3>
          </div>
          <div className="p-4 flex flex-col xl:flex flex-1 gap-6">
            {/* Data Visualizer Placeholder */}
            <div className="h-32 border border-terminal-gray bg-black relative overflow-hidden p-2">
              <div className="absolute top-0 left-0 w-full h-full opacity-20 bg-[url('https://placeholder.pics/svg/300')] bg-cover" data-alt="Abstract data noise pattern"></div>
              <div className="relative z-10 flex flex-col h-full justify-between">
                <div className="flex justify-between text-xs text-primary font-mono">
                  <span>NET_IO</span>
                  <span id="net-io-speed">842 KB/s</span>
                </div>
                <div id="net-io-bars" className="flex items-end gap-[2px] h-16">
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '40%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '60%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '30%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '80%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '50%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '90%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '20%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '70%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '45%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '65%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '35%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '85%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '55%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '75%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '25%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '95%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '40%' }}></div>
                  <div className="w-1 bg-primary transition-all duration-300" style={{ height: '60%' }}></div>
                </div>
              </div>
              <script dangerouslySetInnerHTML={{
                __html: `
                document.addEventListener('DOMContentLoaded', () => {
                  setInterval(() => {
                    const bars = document.getElementById('net-io-bars');
                    const speed = document.getElementById('net-io-speed');
                    if (bars && speed) {
                      const currentSpeed = Math.floor(Math.random() * 800) + 200;
                      speed.innerText = currentSpeed + ' KB/s';
                      
                      Array.from(bars.children).forEach(bar => {
                        const newHeight = Math.floor(Math.random() * 90) + 10;
                        bar.style.height = newHeight + '%';
                      });
                    }
                  }, 1500);
                });
              `}} />
            </div>

            {/* Metrics */}
            <div className="space-y-4 font-mono text-xs">
              <div>
                <div className="flex justify-between text-gray-400 mb-1">
                  <span>SYS_LOAD</span>
                  <span>42%</span>
                </div>
                <div className="w-full bg-terminal-gray h-1">
                  <div className="bg-primary h-1 w-[42%]"></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-gray-400 mb-1">
                  <span>MEM_USAGE</span>
                  <span>64%</span>
                </div>
                <div className="w-full bg-terminal-gray h-1">
                  <div className="bg-yellow-500 h-1 w-[64%]"></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-gray-400 mb-1">
                  <span>DISK_SWAP</span>
                  <span>12%</span>
                </div>
                <div className="w-full bg-terminal-gray h-1">
                  <div className="bg-blue-500 h-1 w-[12%]"></div>
                </div>
              </div>
            </div>

            {/* Console Output */}
            <div className="flex-1 bg-black border border-terminal-gray p-2 font-mono text-[10px] text-gray-500 overflow-hidden flex flex-col justify-end">
              <p>&gt; scanning ports...</p>
              <p>&gt; port 80 [OPEN]</p>
              <p>&gt; port 443 [OPEN]</p>
              <p>&gt; fetching assets...</p>
              <p>&gt; rendering 3d_mesh.obj</p>
              <p className="text-primary">&gt; connection established</p>
              <p className="text-white animate-pulse">_</p>
            </div>
          </div>
        </aside>
      </div>
    </>
  );
}
