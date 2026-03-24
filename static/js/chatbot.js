document.addEventListener("DOMContentLoaded", () => {
    // Inject the Chat Widget HTML into the container
    const container = document.getElementById('chatbot-container');
    container.innerHTML = `
        <div id="chat-widget">
            <div id="chat-header">
                <div><i class="bi bi-robot me-2"></i> Lifeline Assistant</div>
                <button id="chat-close" class="btn-close btn-close-white" style="font-size: 0.8rem;"></button>
            </div>
            <div id="chat-messages">
                <div class="msg-bubble msg-bot">
                    Hi there! I'm the Lifeline AI Assistant. How can I help you regarding blood donation today?
                </div>
                <div class="mt-2 text-center mb-2">
                    <button class="btn btn-sm btn-outline-danger px-3 rounded-pill fw-bold bg-white shadow-sm" 
                            onclick="const inp=document.getElementById('chat-input'); inp.value='Emergency blood near me (1km)'; document.getElementById('chat-send').click();">
                        <i class="bi bi-geo-alt-fill me-1"></i> Scan within 1 km
                    </button>
                </div>
            </div>
            <div id="chat-input-area">
                <input type="text" id="chat-input" placeholder="Type your question..." autocomplete="off">
                <button id="chat-send"><i class="bi bi-send-fill"></i></button>
            </div>
        </div>
        <div id="chat-toggle">
            <i class="bi bi-chat-dots-fill"></i>
        </div>
    `;

    const chatWidget = document.getElementById('chat-widget');
    const chatToggle = document.getElementById('chat-toggle');
    const chatClose = document.getElementById('chat-close');
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSend = document.getElementById('chat-send');

    // Toggle Chat Widget
    chatToggle.addEventListener('click', () => {
        chatWidget.classList.add('open');
        chatToggle.style.transform = 'scale(0)';
    });

    chatClose.addEventListener('click', () => {
        chatWidget.classList.remove('open');
        chatToggle.style.transform = 'scale(1)';
    });

    // Send Message
    const sendMessage = async () => {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add user msg to UI
        addMessage(text, 'user');
        chatInput.value = '';

        // Typing indicator
        const typingId = 'typing-' + Date.now();
        addTypingIndicator(typingId);

        try {
            const response = await fetch('/chatbot/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            
            removeTypingIndicator(typingId);
            addMessage(data.reply, 'bot');
        } catch (err) {
            removeTypingIndicator(typingId);
            addMessage("Unable to reach the server. Please try again.", 'bot');
        }
    };

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `msg-bubble msg-${sender}`;
        // Basic markdown formatting for bold and line breaks (very simple parser)
        let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\n/g, '<br>');
        div.innerHTML = formatted;
        
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function addTypingIndicator(id) {
        const div = document.createElement('div');
        div.className = 'msg-bubble msg-bot text-muted';
        div.id = id;
        div.innerHTML = '<span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span> Thinking...';
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }
});
