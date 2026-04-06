// assistant.js — Wildfire chat sidebar
// Posts to /api/events/<id>/chat with streaming text/plain response.

const chatInput    = document.getElementById('chat-input');
const sendBtn      = document.getElementById('chat-send');
const chatMessages = document.getElementById('chat-messages');

// Conversation history sent to backend for context
let chatHistory = [];

function appendMessage(role, text) {
    const color = role === 'user' ? '#fff' : '#ff6b35';
    const label = role === 'user' ? 'You' : 'AI';
    const div = document.createElement('div');
    div.style.cssText = `color:${color};margin-bottom:10px;line-height:1.5;`;
    div.innerHTML = `<b>${label}:</b> ${text}`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
}

async function sendMessage(text) {
    if (!text.trim()) return;
    chatInput.value = '';

    appendMessage('user', text);
    chatHistory.push({ role: 'user', content: text });

    // Need event id and current timestep from wildfire.js globals
    const eventId  = (typeof currentEvent !== 'undefined' && currentEvent) ? currentEvent.id : 1;
    const tsId     = (typeof currentTs    !== 'undefined' && currentTs)    ? currentTs.id    : null;

    const aiDiv = appendMessage('assistant', '…');

    try {
        const res = await fetch(`/api/events/${eventId}/chat`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message:     text,
                timestep_id: tsId,
                history:     chatHistory.slice(-10),   // last 10 turns for context
            }),
        });

        if (!res.ok) {
            aiDiv.innerHTML = `<b>AI:</b> <span style="color:#ef4444">Error ${res.status} — chat not available.</span>`;
            return;
        }

        // Stream the response token by token
        const reader  = res.body.getReader();
        const decoder = new TextDecoder();
        let full = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            full += decoder.decode(value, { stream: true });
            aiDiv.innerHTML = `<b>AI:</b> ${full}`;
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        chatHistory.push({ role: 'assistant', content: full });

    } catch (err) {
        aiDiv.innerHTML = `<b>AI:</b> <span style="color:#ef4444">Could not reach server.</span>`;
        console.error('[assistant] chat error:', err);
    }
}

sendBtn.addEventListener('click', () => sendMessage(chatInput.value));
chatInput.addEventListener('keypress', e => { if (e.key === 'Enter') sendMessage(chatInput.value); });

function quickAsk(question) { sendMessage(question); }
