const CHAT_API_URL = 'http://localhost:5000/api/chat/';

// Find the HTML elements
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('chat-send');
const chatMessages = document.getElementById('chat-messages');

// Main function to send the message
async function sendMessage(text) {
    if (!text) return;

    // Show message on the screen
    chatMessages.innerHTML += `<div style="color: white; margin-bottom: 8px;"><b>You:</b> ${text}</div>`;
    chatInput.value = ''; // Clear the box
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom

    try {
        // Send the text to Python
        const response = await fetch(CHAT_API_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();

        // Show the Python server's answer on the screen
        chatMessages.innerHTML += `<div style="color: #ff6b35; margin-bottom: 12px;"><b>AI:</b> ${data.response}</div>`;
        chatMessages.scrollTop = chatMessages.scrollHeight;

    } catch (error) {
        chatMessages.innerHTML += `<div style="color: red; margin-bottom: 12px;"><b>Error:</b> Could not reach Python server.</div>`;
    }
}

// Listen for clicks on the Send button
sendBtn.addEventListener('click', () => {
    sendMessage(chatInput.value.trim());
});

// Listen for the Enter key
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage(chatInput.value.trim());
    }
});

// Connect the Quick Action buttons at the top
function quickAsk(question) {
    sendMessage(question);
}