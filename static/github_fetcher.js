document.addEventListener("DOMContentLoaded", function () {
    const container = document.getElementById("github-projects-container");
    if (!container) return;

    const GITHUB_USERNAME = "kabhishek18";
    const API_URL = `https://api.github.com/users/${GITHUB_USERNAME}/repos?sort=updated&per_page=100`;

    const getIconForLanguage = (language) => {
        const langMap = {
            'JavaScript': 'javascript',
            'TypeScript': 'code',
            'Python': 'smart_toy',
            'HTML': 'html',
            'CSS': 'css',
            'Java': 'coffee',
            'C++': 'memory',
            'C': 'terminal',
            'Go': 'speed',
            'Rust': 'settings',
            'Ruby': 'diamond',
            'PHP': 'php',
            'Shell': 'terminal',
        };
        return langMap[language] || 'terminal';
    };

    fetch(API_URL)
        .then(response => {
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error("GitHub API rate limit exceeded. Please try again later.");
                } else if (response.status === 404) {
                    throw new Error("GitHub user not found.");
                } else {
                    throw new Error(`Failed to fetch repositories (HTTP ${response.status}).`);
                }
            }
            return response.json();
        })
        .then(repos => {
            if (repos.length === 0) {
                container.innerHTML = `<div class="p-6 text-gray-500 font-mono col-span-full">&gt; No repositories found.</div>`;
                return;
            }

            let htmlContent = "";

            repos.forEach((repo, index) => {
                // Determine border classes based on index to match the grid layout
                let borderClass = "border-b border-terminal-gray";
                // Every 1st and 2nd in a row of 3 needs right border on desktop
                if ((index + 1) % 3 !== 0) {
                    borderClass += " md:border-r";
                }

                const langTags = repo.language
                    ? `<span class="text-xs bg-terminal-gray text-gray-300 px-2 py-1 font-mono">#${repo.language.toLowerCase()}</span>`
                    : `<span class="text-xs bg-terminal-gray text-gray-300 px-2 py-1 font-mono">#code</span>`;

                const iconString = getIconForLanguage(repo.language);
                const description = repo.description || "No description provided.";

                htmlContent += `
                    <article class="${borderClass} p-6 flex flex-col justify-between hover:bg-white/5 group transition-colors min-h-[300px]">
                      <div>
                        <div class="flex justify-between items-start mb-4">
                          <span class="text-primary material-symbols-outlined text-4xl">${iconString}</span>
                          <span class="text-xs border border-gray-700 px-2 py-1 text-gray-400">PUBLIC</span>
                        </div>
                        <h3 class="text-xl font-bold text-white mb-2 group-hover:text-primary transition-colors">${repo.name}</h3>
                        <p class="text-gray-400 text-sm font-mono mb-4">${description}</p>
                        <div class="flex flex-wrap gap-2 mb-6">
                            ${langTags}
                        </div>
                      </div>
                      <a href="${repo.html_url}" target="_blank" rel="noopener noreferrer" class="w-full border border-primary/50 text-primary hover:bg-primary hover:text-black font-mono text-sm py-2 px-4 transition-all uppercase flex items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-sm">rocket_launch</span>
                        View Repository
                      </a>
                    </article>
                `;
            });

            container.innerHTML = htmlContent;
        })
        .catch(error => {
            console.error("Error fetching GitHub repos:", error);
            container.innerHTML = `<div class="p-6 text-red-500 font-mono col-span-full">&gt; ERROR: ${error.message}</div>`;
        });
});
