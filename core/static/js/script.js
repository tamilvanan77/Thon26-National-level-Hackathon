function escapeHtml(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function appendMessage(thread, role, text) {
    const roleLabel = role === "user" ? "You" : "AI";
    const roleClass = role === "user" ? "chat-msg-user" : "chat-msg-ai";
    const safeText = escapeHtml(text);

    thread.insertAdjacentHTML(
        "beforeend",
        `
        <div class="chat-msg ${roleClass}">
            <div class="chat-msg-label">${roleLabel}</div>
            <div class="chat-msg-text">${safeText}</div>
        </div>
        `
    );
    thread.scrollTop = thread.scrollHeight;
}

function sendAssistantMessage(input, thread, endpoint) {
    const message = input.value.trim();
    if (!message) return;

    appendMessage(thread, "user", message);
    input.value = "";

    fetch(`${endpoint}?message=${encodeURIComponent(message)}`)
        .then((response) => response.json())
        .then((data) => {
            appendMessage(thread, "ai", data.reply || "No response received.");
        })
        .catch(() => {
            appendMessage(thread, "ai", "Unable to connect right now. Please try again.");
        });
}

function bindAssistant(inputId, threadId, sendButtonId, endpoint) {
    const input = document.getElementById(inputId);
    const thread = document.getElementById(threadId);
    const sendButton = document.getElementById(sendButtonId);
    if (!input || !thread || !sendButton) return;

    sendButton.addEventListener("click", function () {
        sendAssistantMessage(input, thread, endpoint);
    });

    input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendAssistantMessage(input, thread, endpoint);
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    const chatBtn = document.getElementById("floating-chat-btn");
    const chatBox = document.getElementById("floating-chatbox");

    if (chatBtn && chatBox) {
        chatBtn.addEventListener("click", function () {
            chatBox.classList.toggle("is-open");
        });
    }

    bindAssistant(
        "floating-chat-input",
        "floating-chat-content",
        "floating-chat-send",
        "/chatbot-api/"
    );
});

window.CareCureChat = {
    bindInlineAssistant: function (config) {
        bindAssistant(config.inputId, config.threadId, config.sendButtonId, "/chatbot-api/");
    },
};
