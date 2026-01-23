// API Base URL
const API_BASE = '/v1';

// State
let currentChatId = null;
let chats = [];
let currentModel = 'dental-duckduckgo';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const btnNewChat = document.getElementById('btnNewChat');
const modelSelect = document.getElementById('modelSelect');
const chatList = document.getElementById('chatList');
const chatTitle = document.getElementById('chatTitle');
const currentModelSpan = document.getElementById('currentModel');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadChats();
    loadConfig();
    setupEventListeners();
});

// Load config from localStorage
function loadConfig() {
    const saved = localStorage.getItem('dentalChatbot_config');
    if (saved) {
        const config = JSON.parse(saved);
        // Config will be sent with each request
        console.log('Loaded config:', config);
    }
}

// Event Listeners
function setupEventListeners() {
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    btnNewChat.addEventListener('click', createNewChat);
    modelSelect.addEventListener('change', (e) => {
        currentModel = e.target.value;
        updateModelIndicator();
    });
}

// Load chat history from localStorage
function loadChats() {
    const saved = localStorage.getItem('dentalChatbot_chats');
    if (saved) {
        chats = JSON.parse(saved);
        renderChatList();
    }
}

// Save chats to localStorage
function saveChats() {
    localStorage.setItem('dentalChatbot_chats', JSON.stringify(chats));
}

// Render chat list
function renderChatList() {
    chatList.innerHTML = '';
    
    if (chats.length === 0) {
        chatList.innerHTML = '<div class="chat-item-empty">No chats yet. Start a new conversation!</div>';
        return;
    }
    
    chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = `chat-item ${chat.id === currentChatId ? 'active' : ''}`;
        item.textContent = chat.title || `Chat ${chat.id.substring(0, 8)}`;
        item.addEventListener('click', () => loadChat(chat.id));
        chatList.appendChild(item);
    });
}

// Create new chat
function createNewChat() {
    currentChatId = null;
    chatTitle.textContent = 'New Chat';
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <h3>Welcome to Dental Chatbot! 👋</h3>
            <p>Ask me anything about dental health, teeth, gums, or oral hygiene.</p>
            <p>Select a search model and start chatting!</p>
        </div>
    `;
    messageInput.value = '';
    messageInput.focus();
    renderChatList();
}

// Load existing chat
function loadChat(chatId) {
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;
    
    currentChatId = chatId;
    chatTitle.textContent = chat.title || `Chat ${chatId.substring(0, 8)}`;
    
    // Render messages
    chatMessages.innerHTML = '';
    chat.messages.forEach(msg => {
        addMessageToUI(msg.role, msg.content, msg.timestamp);
    });
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
    renderChatList();
}

// Format message content: convert line breaks and markdown links
function formatMessageContent(content) {
    if (!content) return '';
    
    // Step 0: Handle if content already has <br> tags (from backend or previous processing)
    // Convert existing <br> or &lt;br&gt; back to newlines first
    let workingContent = content
        .replace(/&lt;br&gt;/gi, '\n')  // Handle escaped <br>
        .replace(/<br\s*\/?>/gi, '\n')  // Handle <br> or <br/>
        .replace(/&lt;br\s*\/?&gt;/gi, '\n');  // Handle escaped <br/>
    
    // Step 1: Preserve markdown links with placeholders
    const linkPlaceholder = '___LINK_PLACEHOLDER___';
    const linkMap = new Map();
    let linkCounter = 0;
    
    workingContent = workingContent.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(match, text, url) {
        const placeholder = `${linkPlaceholder}${linkCounter}`;
        linkMap.set(placeholder, { text: text, url: url });
        linkCounter++;
        return placeholder;
    });
    
    // Step 2: Preserve bold text with placeholders
    const boldPlaceholder = '___BOLD_PLACEHOLDER___';
    const boldMap = new Map();
    let boldCounter = 0;
    
    workingContent = workingContent.replace(/\*\*([^\*]+)\*\*/g, function(match, text) {
        const placeholder = `${boldPlaceholder}${boldCounter}`;
        boldMap.set(placeholder, text);
        boldCounter++;
        return placeholder;
    });
    
    // Step 3: Convert --- to horizontal rule placeholder
    const hrPlaceholder = '___HR_PLACEHOLDER___';
    workingContent = workingContent.replace(/^---$/gm, hrPlaceholder);
    
    // Step 4: Use a unique, safe marker for line breaks that won't be escaped
    // Use a marker that contains no special regex characters
    const brMarker = '___BR_MARKER___';
    workingContent = workingContent.replace(/\r\n|\r|\n/g, brMarker);
    
    // Step 5: Split by double+ markers to create paragraphs
    const doubleBrPattern = new RegExp(brMarker + '{2,}', 'g');
    const paragraphs = workingContent.split(doubleBrPattern);
    const result = [];
    
    for (let para of paragraphs) {
        para = para.trim();
        if (!para) continue;
        
        // Check if it's a horizontal rule
        if (para === hrPlaceholder) {
            result.push('<hr>');
            continue;
        }
        
        // Escape HTML (markers won't be affected as they don't contain < or >)
        para = para
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        // NOW replace markers with <br> tags (after escaping, so <br> won't be escaped again)
        // Use simple string replace since we know the exact marker
        para = para.split(brMarker).join('<br>');
        
        // Restore bold placeholders
        boldMap.forEach((text, placeholder) => {
            const escapedText = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            para = para.replace(placeholder, `<strong>${escapedText}</strong>`);
        });
        
        // Restore link placeholders
        linkMap.forEach((linkData, placeholder) => {
            const escapedText = linkData.text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const escapedUrl = linkData.url.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            para = para.replace(
                placeholder,
                `<a href="${escapedUrl}" target="_blank" rel="noopener noreferrer" class="source-link">${escapedText}</a>`
            );
        });
        
        // Wrap in <p> tag
        result.push(`<p>${para}</p>`);
    }
    
    let formatted = result.join('');
    
    // Final cleanup: Replace ANY remaining placeholders or markers (multiple passes to be sure)
    // This handles edge cases where placeholders might not have been replaced
    let previousFormatted = '';
    while (formatted !== previousFormatted) {
        previousFormatted = formatted;
        formatted = formatted.replace(/___BR_PLACEHOLDER___/g, '<br>');
        formatted = formatted.replace(/BR_PLACEHOLDER___/g, '<br>');  // Handle partial placeholder
        formatted = formatted.replace(/___BR_MARKER___/g, '<br>');
        formatted = formatted.replace(/BR_MARKER___/g, '<br>');  // Handle partial marker
        formatted = formatted.replace(/___HR_PLACEHOLDER___/g, '<hr>');
    }
    
    // Fallback: If no paragraphs were created, treat as single paragraph
    if (!formatted.includes('<p>') && !formatted.includes('<hr>')) {
        // Start fresh with original content
        let fallbackContent = content
            .replace(/&lt;br&gt;/gi, '\n')
            .replace(/<br\s*\/?>/gi, '\n')
            .replace(/&lt;br\s*\/?&gt;/gi, '\n');
        
        // Preserve links and bold
        fallbackContent = fallbackContent.replace(/\[([^\]]+)\]\(([^)]+)\)/g, 
            '<a href="$2" target="_blank" rel="noopener noreferrer" class="source-link">$1</a>');
        fallbackContent = fallbackContent.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
        
        // Escape HTML
        fallbackContent = fallbackContent
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        // Restore links and bold (they were escaped, need to restore)
        fallbackContent = fallbackContent
            .replace(/&lt;a href="([^"]+)" target="_blank" rel="noopener noreferrer" class="source-link"&gt;([^&]+)&lt;\/a&gt;/g, 
                '<a href="$1" target="_blank" rel="noopener noreferrer" class="source-link">$2</a>')
            .replace(/&lt;strong&gt;([^&]+)&lt;\/strong&gt;/g, '<strong>$1</strong>');
        
        // Convert newlines to <br>
        fallbackContent = fallbackContent.replace(/\r\n|\r|\n/g, '<br>');
        
        formatted = `<p>${fallbackContent}</p>`;
    }
    
    return formatted;
}

// Add message to UI
function addMessageToUI(role, content, timestamp = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Format and set content
    const formattedContent = formatMessageContent(content);
    
    // Debug: Check for any remaining placeholders
    if (formattedContent.includes('___BR_PLACEHOLDER___') || formattedContent.includes('___BR_MARKER___')) {
        console.error('[DEBUG] Placeholder still found in formatted content!', formattedContent.substring(0, 200));
    }
    if (formattedContent.includes('&lt;br&gt;')) {
        console.error('[DEBUG] <br> tags are escaped! This should not happen.');
    }
    if (formattedContent.includes('<br>')) {
        console.log('[DEBUG] <br> tags found in formatted content (good)');
    }
    
    contentDiv.innerHTML = formattedContent;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send message
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Clear input
    messageInput.value = '';
    sendButton.disabled = true;
    
    // Add user message to UI
    addMessageToUI('user', message);
    
    // Show loading
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = '<div class="message-content loading">Thinking...</div>';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        // Get or create chat
        if (!currentChatId) {
            currentChatId = generateChatId();
            chats.push({
                id: currentChatId,
                title: message.substring(0, 50),
                messages: [],
                createdAt: Date.now()
            });
            saveChats();
            renderChatList();
            chatTitle.textContent = message.substring(0, 50);
        }
        
        // Find current chat
        const currentChat = chats.find(c => c.id === currentChatId);
        
        // Add user message to chat (for UI display)
        currentChat.messages.push({
            role: 'user',
            content: message,
            timestamp: Date.now()
        });
        
        // Get current config and include in request
        const config = getCurrentConfig();
        
        // Call API - Only send the NEW user message
        // Backend will retrieve full context from memory using chat_id
        const response = await fetch(`${API_BASE}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: currentModel,
                // Only send the new user message - backend will get context from memory
                messages: [{
                    role: 'user',
                    content: message
                }],
                chat_id: currentChatId,
                // Include config in request so backend can use it
                config: config
            })
        });
        
        const data = await response.json();
        
        // Remove loading
        loadingDiv.remove();
        
        // Handle error response
        if (data.error) {
            showError(data.error.message || 'An error occurred');
            return;
        }
        
        // Get assistant response
        const assistantMessage = data.choices[0].message.content;
        
        // Add assistant message to UI
        addMessageToUI('assistant', assistantMessage);
        
        // Add assistant message to chat
        currentChat.messages.push({
            role: 'assistant',
            content: assistantMessage,
            timestamp: Date.now()
        });
        
        // Update chat title if first message
        if (currentChat.messages.length === 2) {
            currentChat.title = message.substring(0, 50);
            chatTitle.textContent = currentChat.title;
            renderChatList();
        }
        
        // Save chats
        saveChats();
        
    } catch (error) {
        loadingDiv.remove();
        showError(`Error: ${error.message}`);
        console.error('Error sending message:', error);
    } finally {
        sendButton.disabled = false;
        messageInput.focus();
    }
}

// Show error message
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Remove error after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Update model indicator
function updateModelIndicator() {
    const modelNames = {
        'dental-google': 'Google Search',
        'dental-duckduckgo': 'DuckDuckGo Search'
    };
    currentModelSpan.textContent = modelNames[currentModel] || currentModel;
}

// Generate chat ID
function generateChatId() {
    return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// Initialize model indicator
updateModelIndicator();
