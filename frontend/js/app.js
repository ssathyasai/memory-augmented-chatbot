
class ChatbotApp {
    constructor() {
        this.userId = localStorage.getItem("chatbot_user_id") || "sathya";
        this.messages = [
            { role: "assistant", content: "Hello! I am your memory-augmented AI assistant. Upload documents or start chatting." }
        ];
        this.uploadedDocs = [];
        this.memories = [];
        this.settings = {
            user_id: this.userId,
            display_name: this.userId,
            preferred_theme: "dark",
            transparency_enabled: true
        };
        this.isTyping = false;
        this.cacheElements();
        this.attachEventListeners();
        this.bootstrap();
    }

    cacheElements() {
        this.chatForm = document.getElementById("chat-form");
        this.chatInput = document.getElementById("chat-input");
        this.chatMessages = document.getElementById("chat-messages");
        this.sendButton = document.getElementById("send-button");
        this.navItems = document.querySelectorAll(".nav-item");
        this.pages = document.querySelectorAll(".page");
        this.pdfUpload = document.getElementById("pdf-upload");
        this.uploadStatus = document.getElementById("upload-status");
        this.docsList = document.getElementById("docs-list");
        this.memoryType = document.getElementById("memory-type");
        this.memoryContent = document.getElementById("memory-content");
        this.addMemoryBtn = document.getElementById("add-memory-btn");
        this.memorySearch = document.getElementById("memory-search");
        this.memoriesList = document.getElementById("memories-list");
        this.graphQueryInput = document.getElementById("graph-query-input");
        this.graphQueryBtn = document.getElementById("graph-query-btn");
        this.graphQueryResults = document.getElementById("graph-query-results");
        this.graphFromEntity = document.getElementById("graph-from-entity");
        this.graphRelationship = document.getElementById("graph-relationship");
        this.graphToEntity = document.getElementById("graph-to-entity");
        this.graphAddBtn = document.getElementById("graph-add-btn");
        this.graphRefreshBtn = document.getElementById("graph-refresh-btn");
        this.graphEntitiesList = document.getElementById("graph-entities-list");
        this.analyticsCards = document.getElementById("analytics-cards");
        this.settingsUserId = document.getElementById("settings-user-id");
        this.settingsDisplayName = document.getElementById("settings-display-name");
        this.settingsTheme = document.getElementById("settings-theme");
        this.settingsTransparency = document.getElementById("settings-transparency");
        this.saveSettingsBtn = document.getElementById("save-settings-btn");
    }

    attachEventListeners() {
        this.chatForm.addEventListener("submit", (event) => this.handleSubmit(event));
        this.chatInput.addEventListener("input", () => this.autoResizeTextarea());
        this.navItems.forEach((item) => item.addEventListener("click", (event) => this.handleNavClick(event, item)));
        this.pdfUpload.addEventListener("change", (event) => this.handlePdfUpload(event));
        this.addMemoryBtn.addEventListener("click", () => this.handleAddMemory());
        this.memorySearch.addEventListener("input", (event) => this.handleMemorySearch(event));
        this.graphQueryBtn.addEventListener("click", () => this.handleGraphSearch());
        this.graphAddBtn.addEventListener("click", () => this.handleGraphRelationshipCreate());
        this.graphRefreshBtn.addEventListener("click", () => this.loadGraphEntities());
        this.saveSettingsBtn.addEventListener("click", () => this.handleSaveSettings());
    }

    async bootstrap() {
        this.populateSettingsForm();
        await this.loadSettings();
        await Promise.all([
            this.loadDocuments(),
            this.loadMemories(),
            this.loadGraphEntities(),
            this.loadAnalytics()
        ]);
    }

    async apiFetch(url, options = {}) {
        const response = await fetch(url, options);
        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || `Request failed with status ${response.status}`);
        }
        return response.json();
    }

    autoResizeTextarea() {
        this.chatInput.style.height = "auto";
        this.chatInput.style.height = `${this.chatInput.scrollHeight}px`;
    }

    handleNavClick(event, item) {
        event.preventDefault();
        this.navItems.forEach((nav) => nav.classList.remove("active"));
        item.classList.add("active");
        this.pages.forEach((page) => page.classList.remove("active"));
        document.getElementById(`${item.dataset.page}-page`).classList.add("active");

        if (item.dataset.page === "analytics") {
            this.loadAnalytics();
        } else if (item.dataset.page === "knowledge-graph") {
            this.loadGraphEntities();
        } else if (item.dataset.page === "documents") {
            this.loadDocuments();
        } else if (item.dataset.page === "memory") {
            this.loadMemories();
        }
    }

    async loadDocuments() {
        this.uploadedDocs = await this.apiFetch(`/api/documents?user_id=${encodeURIComponent(this.userId)}`);
        this.renderDocsList();
    }

    async handlePdfUpload(event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) {
            return;
        }

        for (const file of files) {
            const formData = new FormData();
            formData.append("file", file);
            try {
                const data = await this.apiFetch(`/api/upload-pdf?user_id=${encodeURIComponent(this.userId)}`, {
                    method: "POST",
                    body: formData
                });
                this.showUploadStatus(
                    `Uploaded ${data.filename}: ${data.num_chunks} chunks, ${data.entities_extracted} entities, ${data.relationships_extracted} relationships.`,
                    "success"
                );
            } catch (error) {
                this.showUploadStatus(`Upload failed for ${file.name}: ${error.message}`, "error");
            }
        }

        this.pdfUpload.value = "";
        await Promise.all([this.loadDocuments(), this.loadGraphEntities(), this.loadAnalytics()]);
    }

    showUploadStatus(message, type) {
        this.uploadStatus.textContent = message;
        this.uploadStatus.className = `upload-status ${type}`;
    }

    renderDocsList() {
        this.docsList.innerHTML = "";
        if (this.uploadedDocs.length === 0) {
            const item = document.createElement("li");
            item.textContent = "No documents uploaded for this user yet.";
            this.docsList.appendChild(item);
            return;
        }

        this.uploadedDocs.forEach((doc) => {
            const item = document.createElement("li");
            item.textContent = `${doc.filename} (${doc.num_chunks} chunks)`;
            this.docsList.appendChild(item);
        });
    }

    async loadMemories() {
        this.memories = await this.apiFetch(`/api/memories?user_id=${encodeURIComponent(this.userId)}`);
        this.renderMemoriesList();
    }

    async handleAddMemory() {
        const payload = {
            user_id: this.userId,
            type: this.memoryType.value,
            content: this.memoryContent.value.trim(),
            metadata: {}
        };
        if (!payload.content) {
            return;
        }

        await this.apiFetch("/api/memories", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        this.memoryContent.value = "";
        await Promise.all([this.loadMemories(), this.loadAnalytics()]);
    }

    async handleMemorySearch(event) {
        const query = event.target.value.trim();
        if (!query) {
            await this.loadMemories();
            return;
        }
        this.memories = await this.apiFetch(
            `/api/memories/search?query=${encodeURIComponent(query)}&user_id=${encodeURIComponent(this.userId)}`
        );
        this.renderMemoriesList();
    }

    renderMemoriesList() {
        this.memoriesList.innerHTML = "";
        if (this.memories.length === 0) {
            const item = document.createElement("li");
            item.className = "stack-item";
            item.textContent = "No memories stored yet.";
            this.memoriesList.appendChild(item);
            return;
        }

        this.memories.forEach((memory) => {
            const item = document.createElement("li");
            item.className = "stack-item";
            item.innerHTML = `
                <div class="panel-header-row">
                    <strong>${memory.type}</strong>
                    <button type="button" data-memory-id="${memory.memory_id}">Delete</button>
                </div>
                <div>${memory.content}</div>
                <small>${new Date(memory.updated_at).toLocaleString()}</small>
            `;
            item.querySelector("button").addEventListener("click", async () => {
                await this.apiFetch(`/api/memories/${memory.memory_id}`, { method: "DELETE" });
                await Promise.all([this.loadMemories(), this.loadAnalytics()]);
            });
            this.memoriesList.appendChild(item);
        });
    }

    async loadGraphEntities() {
        const entities = await this.apiFetch(`/api/graph/entities?user_id=${encodeURIComponent(this.userId)}`);
        this.graphEntitiesList.innerHTML = "";
        if (entities.length === 0) {
            this.graphEntitiesList.innerHTML = '<div class="entity-card"><h4>Graph</h4><strong>0</strong><span>No entities yet.</span></div>';
            return;
        }

        entities.forEach((entity) => {
            const card = document.createElement("div");
            card.className = "entity-card";
            card.innerHTML = `
                <h4>${entity.entity_type}</h4>
                <strong>${entity.name}</strong>
                <span>${entity.relation_count} relationships</span>
            `;
            this.graphEntitiesList.appendChild(card);
        });
    }

    async handleGraphSearch() {
        const query = this.graphQueryInput.value.trim();
        if (!query) {
            return;
        }
        const results = await this.apiFetch(
            `/api/graph/query?query=${encodeURIComponent(query)}&user_id=${encodeURIComponent(this.userId)}`
        );
        this.graphQueryResults.innerHTML = "";
        if (results.length === 0) {
            this.graphQueryResults.innerHTML = '<div class="stack-item">No graph matches found.</div>';
            return;
        }

        results.forEach((result) => {
            const item = document.createElement("div");
            item.className = "stack-item";
            const relations = result.relations.length
                ? result.relations.map((rel) => `${rel.relation} -> ${rel.entity}`).join(", ")
                : "No outgoing relationships";
            item.innerHTML = `<strong>${result.entity}</strong><div>${relations}</div>`;
            this.graphQueryResults.appendChild(item);
        });
    }

    async handleGraphRelationshipCreate() {
        const payload = {
            user_id: this.userId,
            from_entity: this.graphFromEntity.value.trim(),
            to_entity: this.graphToEntity.value.trim(),
            relationship: this.graphRelationship.value.trim()
        };

        if (!payload.from_entity || !payload.to_entity || !payload.relationship) {
            return;
        }

        await this.apiFetch("/api/graph/relationships", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        this.graphFromEntity.value = "";
        this.graphToEntity.value = "";
        this.graphRelationship.value = "";
        await Promise.all([this.loadGraphEntities(), this.loadAnalytics()]);
    }

    async loadAnalytics() {
        const summary = await this.apiFetch(`/api/analytics/summary?user_id=${encodeURIComponent(this.userId)}`);
        const cards = [
            ["Uploaded Documents", summary.uploaded_documents],
            ["Total Chunks", summary.total_chunks],
            ["Memory Entries", summary.memory_entries],
            ["Graph Nodes", summary.knowledge_graph_nodes],
            ["Relationships", summary.knowledge_graph_relationships],
            ["Total Chats", summary.total_chats],
            ["Avg Response Time", `${summary.average_response_time.toFixed(2)}s`],
            ["Last Route", summary.last_route]
        ];
        this.analyticsCards.innerHTML = "";
        cards.forEach(([label, value]) => {
            const card = document.createElement("div");
            card.className = "metric-card";
            card.innerHTML = `<h4>${label}</h4><strong>${value}</strong>`;
            this.analyticsCards.appendChild(card);
        });
    }

    populateSettingsForm() {
        this.settingsUserId.value = this.userId;
        this.settingsDisplayName.value = this.settings.display_name;
        this.settingsTheme.value = this.settings.preferred_theme;
        this.settingsTransparency.checked = this.settings.transparency_enabled;
    }

    applyTheme(theme) {
        document.body.classList.remove("dark-theme", "light-theme");
        document.body.classList.add(theme === "light" ? "light-theme" : "dark-theme");
    }

    async loadSettings() {
        try {
            this.settings = await this.apiFetch(`/api/settings/${encodeURIComponent(this.userId)}`);
        } catch (error) {
            console.warn("Settings load fallback:", error.message);
        }
        this.applyTheme(this.settings.preferred_theme);
        this.populateSettingsForm();
    }

    async handleSaveSettings() {
        const newUserId = this.settingsUserId.value.trim() || this.userId;
        const payload = {
            user_id: newUserId,
            display_name: this.settingsDisplayName.value.trim() || newUserId,
            preferred_theme: this.settingsTheme.value,
            transparency_enabled: this.settingsTransparency.checked
        };

        this.settings = await this.apiFetch(`/api/settings/${encodeURIComponent(newUserId)}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        this.userId = newUserId;
        localStorage.setItem("chatbot_user_id", this.userId);
        this.applyTheme(this.settings.preferred_theme);
        await this.bootstrap();
    }

    async handleSubmit(event) {
        event.preventDefault();
        const messageText = this.chatInput.value.trim();
        if (!messageText || this.isTyping) {
            return;
        }

        this.addMessage("user", messageText);
        this.chatInput.value = "";
        this.autoResizeTextarea();
        this.sendButton.disabled = true;
        this.showTypingIndicator();

        try {
            const data = await this.apiFetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: this.userId,
                    messages: this.messages
                })
            });

            this.hideTypingIndicator();
            this.addMessage("assistant", data.message.content, data);
            await Promise.all([this.loadMemories(), this.loadAnalytics()]);
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessage("assistant", `Sorry, I hit an error: ${error.message}`);
        } finally {
            this.sendButton.disabled = false;
        }
    }

    addMessage(role, content, payload = null) {
        this.messages.push({ role, content });
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", role);

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = role === "user" ? "👤" : "🤖";

        const messageContent = document.createElement("div");
        messageContent.className = "message-content";
        messageContent.innerHTML = marked.parse(content);

        if (payload && role === "assistant" && this.settings.transparency_enabled) {
            const traceBlock = document.createElement("div");
            traceBlock.className = "trace-block";
            const routing = payload.routing || {};
            const pills = [
                `Route: ${routing.route || "general"}`,
                `Memory: ${payload.memories?.length || 0}`,
                `RAG: ${payload.sources?.length || 0}`,
                `Graph: ${payload.graph_results?.length || 0}`,
                `Tools: ${payload.tools_used?.length || 0}`,
                `Latency: ${payload.response_time?.toFixed(2) || "0.00"}s`
            ];
            pills.forEach((text) => {
                const pill = document.createElement("span");
                pill.className = "trace-pill";
                pill.textContent = text;
                traceBlock.appendChild(pill);
            });

            if (payload.sources?.length) {
                payload.sources.forEach((source) => {
                    const item = document.createElement("div");
                    item.className = "stack-item";
                    item.innerHTML = `<strong>${source.source}</strong><div>${source.content.slice(0, 220)}...</div>`;
                    traceBlock.appendChild(item);
                });
            }
            messageContent.appendChild(traceBlock);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        this.isTyping = true;
        const typingDiv = document.createElement("div");
        typingDiv.className = "message assistant typing-message";
        typingDiv.id = "typing-indicator";

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = "🤖";

        const typingIndicator = document.createElement("div");
        typingIndicator.className = "typing-indicator";
        for (let index = 0; index < 3; index += 1) {
            const dot = document.createElement("div");
            dot.className = "typing-dot";
            typingIndicator.appendChild(dot);
        }

        typingDiv.appendChild(avatar);
        typingDiv.appendChild(typingIndicator);
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        this.isTyping = false;
        const indicator = document.getElementById("typing-indicator");
        if (indicator) {
            indicator.remove();
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new ChatbotApp();
});
