// Configuration page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    setupEventListeners();
});

function setupEventListeners() {
    const form = document.getElementById('configForm');
    form.addEventListener('submit', saveConfig);
}

function loadConfig() {
    // Safely get elements first
    const chatModelEl = document.getElementById('ollamaChatModel');
    const guardrailModelEl = document.getElementById('ollamaGuardrailModel');
    
    if (!chatModelEl || !guardrailModelEl) {
        console.warn('Config form elements not found, skipping load');
        return;
    }
    
    // Load from localStorage
    const saved = localStorage.getItem('dentalChatbot_config');
    if (saved) {
        try {
        const config = JSON.parse(saved);
            
            // Clean up old config: remove gemini/google/search_tool fields
            // Migrate phi3:latest to qwen2.5:3b-instruct (new default)
            let guardrailModel = config.ollama_guardrail_model || 'qwen2.5:3b-instruct';
            if (guardrailModel === 'phi3:latest' || guardrailModel === 'phi-3') {
                guardrailModel = 'qwen2.5:3b-instruct';
            }
            
            const cleanConfig = {
                llm_provider: 'ollama',
                guardrail_provider: 'ollama',
                ollama_model: config.ollama_model || 'qwen2.5:7b-instruct',
                ollama_guardrail_model: guardrailModel
            };
            
            // Save cleaned config back to localStorage
            localStorage.setItem('dentalChatbot_config', JSON.stringify(cleanConfig));
            
            // Set values
            chatModelEl.value = cleanConfig.ollama_model;
            guardrailModelEl.value = cleanConfig.ollama_guardrail_model;
        } catch (error) {
            console.error('Error loading config:', error);
            // Use defaults if parse fails
            chatModelEl.value = 'qwen2.5:7b-instruct';
            guardrailModelEl.value = 'qwen2.5:3b-instruct';
        }
    } else {
        // No saved config, use defaults
        chatModelEl.value = 'qwen2.5:7b-instruct';
        guardrailModelEl.value = 'qwen2.5:3b-instruct';
    }
}

async function saveConfig(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const config = {
        llm_provider: 'ollama',
        guardrail_provider: 'ollama',
        ollama_model: formData.get('ollama_model'),
        ollama_guardrail_model: formData.get('ollama_guardrail_model')
    };
    
    // Save to localStorage
    localStorage.setItem('dentalChatbot_config', JSON.stringify(config));
    
    // Show immediate feedback
    showStatus('Saving configuration...', 'success');
    
    // Save to backend API
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            showStatus('✅ Configuration saved successfully!', 'success');
        } else {
            showStatus('⚠️ Failed to save configuration to server', 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showStatus('⚠️ Configuration saved locally. Server update failed.', 'error');
    }
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('statusMessage');
    if (!statusDiv) {
        console.error('statusMessage element not found');
        // Fallback: use alert if element not found
        alert(message);
        return;
    }
    
    console.log('Showing status:', message, type);
    
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'block';
    
    // Force visibility with inline style
    statusDiv.style.visibility = 'visible';
    statusDiv.style.opacity = '1';
    
    // Clear any existing timeout
    if (statusDiv._timeout) {
        clearTimeout(statusDiv._timeout);
    }
    
    // Hide after 5 seconds (increased from 3)
    statusDiv._timeout = setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}
