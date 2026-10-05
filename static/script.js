let allResources = [];

const navItems = document.querySelectorAll(".nav-item");

const pageSections = document.querySelectorAll(".page-section");

const uploadButton = document.getElementById(
    "upload-button"
);

const heroUploadButton = document.getElementById(
    "hero-upload-button"
);

const fileInput = document.getElementById(
    "file-input"
);

const resourceSearch = document.getElementById(
    "resource-search"
);

const categoryFilter = document.getElementById(
    "category-filter"
);

const recentResourcesContainer =
    document.getElementById(
        "recent-resources"
    );

const resourceGrid =
    document.getElementById(
        "resource-grid"
    );

const totalResources =
    document.getElementById(
        "total-resources"
    );

const totalCategories =
    document.getElementById(
        "total-categories"
    );

const assistantResourceFilter =
    document.getElementById(
        "assistant-resource-filter"
    );

const questionInput =
    document.getElementById(
        "question"
    );

const askButton =
    document.getElementById(
        "ask-button"
    );

const clearQuestionButton =
    document.getElementById(
        "clear-question"
    );

const clearChatButton =
    document.getElementById(
        "clear-chat"
    );

const chatHistory =
    document.getElementById(
        "chat-history"
    );

const clearAllButton =
    document.getElementById(
        "clear-all-resources"
    );


// ============================================================
// INITIAL LOAD
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {
        loadResources();
    }
);


// ============================================================
// NAVIGATION
// ============================================================

navItems.forEach(
    (item) => {
        item.addEventListener(
            "click",
            () => {
                const page = item.dataset.page;

                showPage(page);
            }
        );
    }
);


document
    .querySelectorAll("[data-page-target]")
    .forEach(
        (button) => {
            button.addEventListener(
                "click",
                () => {
                    showPage(
                        button.dataset.pageTarget
                    );
                }
            );
        }
    );


function showPage(pageName) {

    navItems.forEach(
        (item) => {
            item.classList.toggle(
                "active",
                item.dataset.page === pageName
            );
        }
    );

    pageSections.forEach(
        (section) => {
            section.classList.toggle(
                "active",
                section.id === `${pageName}-page`
            );
        }
    );
}


// ============================================================
// UPLOAD
// ============================================================

if (uploadButton) {

    uploadButton.addEventListener(
        "click",
        () => {
            fileInput.click();
        }
    );
}


if (heroUploadButton) {

    heroUploadButton.addEventListener(
        "click",
        () => {
            fileInput.click();
        }
    );
}


if (fileInput) {

    fileInput.addEventListener(
        "change",
        async () => {

            if (!fileInput.files.length) {
                return;
            }

            const file = fileInput.files[0];

            if (
                file.type !== "application/pdf" &&
                !file.name
                    .toLowerCase()
                    .endsWith(".pdf")
            ) {

                showMessage(
                    "Please select a PDF file.",
                    true
                );

                fileInput.value = "";

                return;
            }

            const formData = new FormData();

            formData.append(
                "file",
                file
            );

            try {

                showMessage(
                    "Uploading resource..."
                );

                const response = await fetch(
                    "/api/resources",
                    {
                        method: "POST",
                        body: formData,
                        cache: "no-store"
                    }
                );

                const responseText =
                    await response.text();

                let data;

                try {

                    data = JSON.parse(
                        responseText
                    );

                } catch {

                    throw new Error(
                        "The server returned an unexpected response."
                    );
                }

                if (!response.ok) {

                    throw new Error(
                        data.error ||
                        "Upload failed."
                    );
                }

                showMessage(
                    `${data.name} uploaded successfully.`
                );

                await loadResources();

            } catch (error) {

                showMessage(
                    error.message,
                    true
                );

            } finally {

                fileInput.value = "";
            }
        }
    );
}


// ============================================================
// LOAD RESOURCES
// ============================================================

async function loadResources() {

    try {

        const response = await fetch(
            "/api/resources",
            {
                method: "GET",
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache"
                }
            }
        );

        const responseText =
            await response.text();

        let data;

        try {

            data = JSON.parse(
                responseText
            );

        } catch {

            throw new Error(
                "The server returned an unexpected response."
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error ||
                "Failed to load resources."
            );
        }

        // Completely replace the old in-memory list.
        allResources = Array.isArray(data)
            ? [...data]
            : [];

        // Clear previous rendered content.
        if (resourceGrid) {
            resourceGrid.innerHTML = "";
        }

        if (recentResourcesContainer) {
            recentResourcesContainer.innerHTML = "";
        }

        updateDashboard();

        populateCategoryFilter();

        populateAssistantFilter();

        renderResources();

        renderRecentResources();

    } catch (error) {

        // Make sure old resources cannot remain
        // visible if loading fails.
        allResources = [];

        if (resourceGrid) {
            resourceGrid.innerHTML = "";
        }

        if (recentResourcesContainer) {
            recentResourcesContainer.innerHTML = "";
        }

        updateDashboard();

        populateCategoryFilter();

        populateAssistantFilter();

        if (
            error.message !==
            "Authentication required."
        ) {

            showMessage(
                error.message,
                true
            );
        }
    }
}


// ============================================================
// PAGE RESTORE / ACCOUNT SWITCH
// ============================================================

window.addEventListener(
    "pageshow",
    () => {
        loadResources();
    }
);


// ============================================================
// DASHBOARD
// ============================================================

function updateDashboard() {

    if (totalResources) {

        totalResources.textContent =
            allResources.length;
    }

    const categories = [
        ...new Set(
            allResources
                .map(
                    (resource) =>
                        resource.category
                )
                .filter(Boolean)
        )
    ];

    if (totalCategories) {

        totalCategories.textContent =
            categories.length;
    }
}


// ============================================================
// CATEGORY FILTER
// ============================================================

function populateCategoryFilter() {

    if (!categoryFilter) {
        return;
    }

    const currentValue =
        categoryFilter.value;

    const categories = [
        ...new Set(
            allResources
                .map(
                    (resource) =>
                        resource.category
                )
                .filter(Boolean)
        )
    ].sort();

    categoryFilter.innerHTML = `
        <option value="">
            All Categories
        </option>
    `;

    categories.forEach(
        (category) => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                category;

            option.textContent =
                category;

            categoryFilter.appendChild(
                option
            );
        }
    );

    if (
        categories.includes(
            currentValue
        )
    ) {

        categoryFilter.value =
            currentValue;
    }
}


// ============================================================
// ASSISTANT RESOURCE FILTER
// ============================================================

function populateAssistantFilter() {

    if (!assistantResourceFilter) {
        return;
    }

    const currentValue =
        assistantResourceFilter.value;

    assistantResourceFilter.innerHTML = `
        <option value="">
            All Resources
        </option>
    `;

    allResources.forEach(
        (resource) => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                resource.name;

            option.textContent =
                resource.name;

            assistantResourceFilter.appendChild(
                option
            );
        }
    );

    const exists =
        allResources.some(
            (resource) =>
                resource.name === currentValue
        );

    if (exists) {

        assistantResourceFilter.value =
            currentValue;
    }
}


// ============================================================
// RENDER RESOURCES
// ============================================================

function renderResources() {

    if (!resourceGrid) {
        return;
    }

    const searchTerm = (
        resourceSearch?.value || ""
    )
        .trim()
        .toLowerCase();

    const selectedCategory =
        categoryFilter?.value || "";

    const filteredResources =
        allResources.filter(
            (resource) => {

                const name = (
                    resource.name || ""
                ).toLowerCase();

                const category = (
                    resource.category || ""
                ).toLowerCase();

                const matchesSearch =
                    !searchTerm ||
                    name.includes(searchTerm) ||
                    category.includes(searchTerm);

                const matchesCategory =
                    !selectedCategory ||
                    resource.category ===
                        selectedCategory;

                return (
                    matchesSearch &&
                    matchesCategory
                );
            }
        );

    if (!filteredResources.length) {

        resourceGrid.innerHTML = `
            <div class="empty-state">

                <div class="empty-state-icon">
                    📚
                </div>

                <h3>
                    No resources found
                </h3>

                <p>
                    Upload a PDF or change your search filters.
                </p>

            </div>
        `;

        return;
    }

    resourceGrid.innerHTML =
        filteredResources
            .map(
                (resource) =>
                    createResourceCard(resource)
            )
            .join("");
}


// ============================================================
// RECENT RESOURCES
// ============================================================

function renderRecentResources() {

    if (!recentResourcesContainer) {
        return;
    }

    const recentResources =
        [...allResources]
            .sort(
                (a, b) =>
                    new Date(
                        b.uploaded_at || 0
                    ) -
                    new Date(
                        a.uploaded_at || 0
                    )
            )
            .slice(
                0,
                4
            );

    if (!recentResources.length) {

        recentResourcesContainer.innerHTML = `
            <div class="empty-state">

                <div class="empty-state-icon">
                    📄
                </div>

                <h3>
                    No resources yet
                </h3>

                <p>
                    Upload your first PDF to get started.
                </p>

            </div>
        `;

        return;
    }

    recentResourcesContainer.innerHTML =
        recentResources
            .map(
                (resource) =>
                    createResourceCard(
                        resource
                    )
            )
            .join("");
}


// ============================================================
// RESOURCE CARD
// ============================================================

function createResourceCard(resource) {

    const filename =
        resource.name ||
        "Untitled PDF";

    const category =
        resource.category ||
        "General Study";

    const size =
        formatFileSize(
            resource.size
        );

    const uploadedAt =
        resource.uploaded_at ||
        "";

    return `
        <article class="resource-card">

            <div class="resource-card-top">

                <div class="pdf-icon">
                    PDF
                </div>

                <span class="category-badge">
                    ${escapeHtml(category)}
                </span>

            </div>


            <div class="resource-card-body">

                <h3
                    class="resource-title"
                    title="${escapeHtml(filename)}"
                >
                    ${escapeHtml(filename)}
                </h3>

                <div class="resource-meta">

                    <span>
                        📦 ${size}
                    </span>

                    <span>
                        🕒 ${escapeHtml(uploadedAt)}
                    </span>

                </div>

            </div>


            <div class="resource-card-actions">

                <button
                    type="button"
                    class="card-button"
                    onclick='previewResource(${JSON.stringify(filename)})'
                >
                    Preview
                </button>

                <button
                    type="button"
                    class="card-button"
                    onclick='downloadResource(${JSON.stringify(filename)})'
                >
                    Download
                </button>

                <button
                    type="button"
                    class="card-button"
                    onclick='summarizeResource(${JSON.stringify(filename)})'
                >
                    Summary
                </button>

                <button
                    type="button"
                    class="card-button danger"
                    onclick='deleteResource(${JSON.stringify(filename)})'
                >
                    Delete
                </button>

            </div>

        </article>
    `;
}


// ============================================================
// FILE SIZE
// ============================================================

function formatFileSize(bytes) {

    if (
        bytes === undefined ||
        bytes === null ||
        Number.isNaN(Number(bytes))
    ) {

        return "Unknown size";
    }

    const size =
        Number(bytes);

    if (size < 1024) {

        return `${size} B`;
    }

    if (size < 1024 * 1024) {

        return `${(
            size / 1024
        ).toFixed(1)} KB`;
    }

    if (size < 1024 * 1024 * 1024) {

        return `${(
            size / (1024 * 1024)
        ).toFixed(1)} MB`;
    }

    return `${(
        size / (1024 * 1024 * 1024)
    ).toFixed(1)} GB`;
}


// ============================================================
// PDF PREVIEW
// ============================================================

function previewResource(filename) {

    const modal =
        document.getElementById(
            "preview-modal"
        );

    const frame =
        document.getElementById(
            "preview-frame"
        );

    const title =
        document.getElementById(
            "preview-title"
        );

    if (
        !modal ||
        !frame ||
        !title
    ) {

        return;
    }

    title.textContent =
        filename;

    frame.src =
        `/api/resources/${encodeURIComponent(filename)}/preview`;

    modal.classList.add(
        "active"
    );
}


function closePreview() {

    const modal =
        document.getElementById(
            "preview-modal"
        );

    const frame =
        document.getElementById(
            "preview-frame"
        );

    if (modal) {

        modal.classList.remove(
            "active"
        );
    }

    if (frame) {

        frame.src = "";
    }
}


const previewModal =
    document.getElementById(
        "preview-modal"
    );

const previewClose =
    document.getElementById(
        "preview-close"
    );


if (previewClose) {

    previewClose.addEventListener(
        "click",
        closePreview
    );
}


if (previewModal) {

    previewModal.addEventListener(
        "click",
        (event) => {

            if (
                event.target ===
                previewModal
            ) {

                closePreview();
            }
        }
    );
}


document.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key ===
            "Escape"
        ) {

            closePreview();
        }
    }
);


// ============================================================
// DOWNLOAD
// ============================================================

function downloadResource(filename) {

    window.location.href =
        `/api/resources/${encodeURIComponent(filename)}/download`;
}


// ============================================================
// DELETE ONE RESOURCE
// ============================================================

async function deleteResource(filename) {

    try {

        const response = await fetch(
            `/api/resources/${encodeURIComponent(filename)}`,
            {
                method: "DELETE",
                cache: "no-store"
            }
        );

        const responseText =
            await response.text();

        let data;

        try {

            data = JSON.parse(
                responseText
            );

        } catch {

            throw new Error(
                "The server returned an unexpected response."
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error ||
                "Failed to delete resource."
            );
        }

        showMessage(
            `${filename} deleted.`
        );

        await loadResources();

    } catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}


// ============================================================
// SEARCH
// ============================================================

if (resourceSearch) {

    resourceSearch.addEventListener(
        "input",
        renderResources
    );
}


if (categoryFilter) {

    categoryFilter.addEventListener(
        "change",
        renderResources
    );
}


// ============================================================
// CLEAR ALL
// ============================================================

if (clearAllButton) {

    clearAllButton.addEventListener(
        "click",
        async () => {

            if (!allResources.length) {

                showMessage(
                    "There are no resources to delete.",
                    true
                );

                return;
            }

            clearAllButton.disabled = true;

            clearAllButton.textContent =
                "Clearing...";

            try {

                const response = await fetch(
                    "/api/resources",
                    {
                        method: "DELETE",
                        cache: "no-store"
                    }
                );

                const responseText =
                    await response.text();

                let data;

                try {

                    data = JSON.parse(
                        responseText
                    );

                } catch {

                    throw new Error(
                        "The server returned an unexpected response."
                    );
                }

                if (!response.ok) {

                    throw new Error(
                        data.error ||
                        "Failed to clear resources."
                    );
                }

                showMessage(
                    "All resources deleted."
                );

                await loadResources();

            } catch (error) {

                showMessage(
                    error.message,
                    true
                );

            } finally {

                clearAllButton.disabled =
                    false;

                clearAllButton.textContent =
                    "Clear All";
            }
        }
    );
}


// ============================================================
// ASK AI
// ============================================================

async function askAI() {

    const question = (
        questionInput?.value || ""
    ).trim();

    if (!question) {

        showMessage(
            "Please enter a question.",
            true
        );

        return;
    }

    const selectedResource =
        assistantResourceFilter?.value || "";

    appendUserMessage(
        question
    );

    questionInput.value = "";

    const thinkingMessage =
        appendThinkingMessage();

    askButton.disabled = true;

    askButton.textContent =
        "Thinking...";

    try {

        const response = await fetch(
            "/api/ask",
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify({
                    question,
                    resource:
                        selectedResource
                })
            }
        );

        const responseText =
            await response.text();

        let data;

        try {

            data = JSON.parse(
                responseText
            );

        } catch {

            throw new Error(
                "The server returned an unexpected response."
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error ||
                "The AI assistant could not answer."
            );
        }

        removeThinkingMessage(
            thinkingMessage
        );

        appendAIMessage(
            data.answer,
            data.sources || []
        );

    } catch (error) {

        removeThinkingMessage(
            thinkingMessage
        );

        appendAIMessage(
            error.message,
            []
        );

    } finally {

        askButton.disabled = false;

        askButton.textContent =
            "Ask AI ✨";
    }
}


if (askButton) {

    askButton.addEventListener(
        "click",
        askAI
    );
}


if (questionInput) {

    questionInput.addEventListener(
        "keydown",
        (event) => {

            if (
                event.ctrlKey &&
                event.key === "Enter"
            ) {

                event.preventDefault();

                askAI();
            }
        }
    );
}


// ============================================================
// CHAT
// ============================================================

function appendUserMessage(message) {

    if (!chatHistory) {
        return;
    }

    removeEmptyChat();

    const bubble =
        document.createElement(
            "div"
        );

    bubble.className =
        "chat-message user-message";

    bubble.innerHTML = `
        <div class="chat-avatar">
            You
        </div>

        <div class="chat-content">

            <div class="chat-label">
                You
            </div>

            <div class="chat-bubble">
                ${escapeHtml(message)}
            </div>

        </div>
    `;

    chatHistory.appendChild(
        bubble
    );

    scrollChatToBottom();
}


function appendAIMessage(
    message,
    sources
) {

    if (!chatHistory) {
        return;
    }

    removeEmptyChat();

    const bubble =
        document.createElement(
            "div"
        );

    bubble.className =
        "chat-message ai-message";

    const sourceTags =
        sources.length
            ? `
                <div class="source-tags">

                    ${sources
                        .map(
                            (source) => `
                                <span class="source-tag">
                                    📄 ${escapeHtml(source)}
                                </span>
                            `
                        )
                        .join("")}

                </div>
            `
            : "";

    bubble.innerHTML = `
        <div class="chat-avatar ai">
            ✨
        </div>

        <div class="chat-content">

            <div class="chat-label">
                StudyHub AI
            </div>

            <div class="chat-bubble">
                ${formatAIText(message)}
            </div>

            ${sourceTags}

        </div>
    `;

    chatHistory.appendChild(
        bubble
    );

    scrollChatToBottom();
}


function appendThinkingMessage() {

    if (!chatHistory) {
        return null;
    }

    removeEmptyChat();

    const bubble =
        document.createElement(
            "div"
        );

    bubble.className =
        "chat-message ai-message thinking-message";

    bubble.innerHTML = `
        <div class="chat-avatar ai">
            ✨
        </div>

        <div class="chat-content">

            <div class="chat-label">
                StudyHub AI
            </div>

            <div class="chat-bubble thinking-bubble">
                Thinking...
            </div>

        </div>
    `;

    chatHistory.appendChild(
        bubble
    );

    scrollChatToBottom();

    return bubble;
}


function removeThinkingMessage(
    element
) {

    if (
        element &&
        element.parentNode
    ) {

        element.parentNode.removeChild(
            element
        );
    }
}


if (clearQuestionButton) {

    clearQuestionButton.addEventListener(
        "click",
        () => {

            if (questionInput) {

                questionInput.value = "";

                questionInput.focus();
            }
        }
    );
}


if (clearChatButton) {

    clearChatButton.addEventListener(
        "click",
        () => {

            if (!chatHistory) {
                return;
            }

            chatHistory.innerHTML = `
                <div class="empty-chat">

                    <div class="empty-chat-icon">
                        ✨
                    </div>

                    <h3>
                        Ask anything about your resources
                    </h3>

                    <p>
                        Questions will be answered using
                        your uploaded study materials.
                    </p>

                </div>
            `;
        }
    );
}


// ============================================================
// SUMMARY
// ============================================================

async function summarizeResource(
    filename
) {

    try {

        showMessage(
            "Generating summary..."
        );

        const response = await fetch(
            `/api/resources/${encodeURIComponent(filename)}/summary`,
            {
                method: "GET",
                cache: "no-store"
            }
        );

        const responseText =
            await response.text();

        let data;

        try {

            data = JSON.parse(
                responseText
            );

        } catch {

            throw new Error(
                "The server returned an unexpected response."
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error ||
                "Failed to generate summary."
            );
        }

        const summaryWindow =
            window.open(
                "",
                "_blank"
            );

        if (!summaryWindow) {

            throw new Error(
                "Please allow popups to view the summary."
            );
        }

        summaryWindow.document.write(`
            <!DOCTYPE html>

            <html lang="en">

            <head>

                <meta charset="UTF-8">

                <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1.0"
                >

                <title>
                    ${escapeHtml(filename)} - Summary
                </title>

                <style>

                    * {
                        box-sizing: border-box;
                    }

                    body {

                        margin: 0;

                        padding: 40px 20px;

                        background: #f3f6fa;

                        font-family:
                            Arial,
                            Helvetica,
                            sans-serif;

                        color: #1f2937;

                        line-height: 1.7;
                    }

                    .summary-container {

                        max-width: 900px;

                        margin: 0 auto;

                        background: #ffffff;

                        border-radius: 18px;

                        padding: 40px;

                        box-shadow:
                            0 20px 50px
                            rgba(30, 58, 95, 0.10);
                    }

                    h1 {

                        margin-top: 0;

                        color: #1e3a5f;
                    }

                    h2,
                    h3 {

                        color: #1e3a5f;
                    }

                    ul {

                        padding-left: 24px;
                    }

                    strong {

                        color: #1e3a5f;
                    }

                    @media (max-width: 700px) {

                        .summary-container {

                            padding: 24px;
                        }
                    }

                </style>

            </head>

            <body>

                <div class="summary-container">

                    <h1>
                        ${escapeHtml(filename)}
                    </h1>

                    <div>
                        ${formatAIText(data.summary)}
                    </div>

                </div>

            </body>

            </html>
        `);

        summaryWindow.document.close();

    } catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}


// ============================================================
// CHAT HELPERS
// ============================================================

function removeEmptyChat() {

    const emptyChat =
        chatHistory?.querySelector(
            ".empty-chat"
        );

    if (emptyChat) {
        emptyChat.remove();
    }
}


function scrollChatToBottom() {

    if (!chatHistory) {
        return;
    }

    chatHistory.scrollTop =
        chatHistory.scrollHeight;
}


// ============================================================
// AI TEXT FORMATTING
// ============================================================

function formatAIText(text) {

    const safeText =
        escapeHtml(
            text || ""
        );

    return safeText
        .replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        )
        .replace(
            /^### (.*)$/gm,
            "<h3>$1</h3>"
        )
        .replace(
            /^## (.*)$/gm,
            "<h2>$1</h2>"
        )
        .replace(
            /^# (.*)$/gm,
            "<h1>$1</h1>"
        )
        .replace(
            /^[-•] (.*)$/gm,
            "<li>$1</li>"
        )
        .replace(
            /\n\n/g,
            "<br><br>"
        )
        .replace(
            /\n/g,
            "<br>"
        );
}


// ============================================================
// MESSAGE
// ============================================================

function showMessage(
    message,
    isError = false
) {

    const existing =
        document.querySelector(
            ".app-message"
        );

    if (existing) {
        existing.remove();
    }

    const element =
        document.createElement(
            "div"
        );

    element.className =
        `app-message ${
            isError
                ? "error"
                : "success"
        }`;

    element.textContent =
        message;

    document.body.appendChild(
        element
    );

    setTimeout(
        () => {

            element.classList.add(
                "hide"
            );

            setTimeout(
                () => {

                    element.remove();

                },
                300
            );

        },
        3000
    );
}


// ============================================================
// HTML ESCAPING
// ============================================================

function escapeHtml(value) {

    return String(
        value ?? ""
    )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );
}