// Configuration page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    setupEventListeners();
});

function setupEventListeners() {
    const form = document.getElementById('configForm');
    form.addEventListener('submit', saveConfig);
    
    // Show/hide provider-specific options
    document.getElementById('llmProvider').addEventListener('change', toggleProviderOptions);
    document.getElementById('guardrailProvider').addEventListener('change', toggleGuardrailOptions);
}

function toggleProviderOptions() {
    const provider = document.getElementById('llmProvider').value;
    document.getElementById('ollamaChatGroup').style.display = provider === 'ollama' ? 'block' : 'none';
    document.getElementById('geminiChatGroup').style.display = provider === 'gemini' ? 'block' : 'none';
}

function toggleGuardrailOptions() {
    const provider = document.getElementById('guardrailProvider').value;
    const ollamaGroup = document.getElementById('ollamaGuardrailGroup');
    const geminiGroup = document.getElementById('geminiGuardrailGroup');
    
    if (!ollamaGroup || !geminiGroup) {
        console.error('Guardrail groups not found!');
        return;
    }
    
    if (provider === 'ollama') {
        ollamaGroup.style.display = 'block';
        geminiGroup.style.display = 'none';
    } else if (provider === 'gemini') {
        ollamaGroup.style.display = 'none';
        geminiGroup.style.display = 'block';
    } else {
        // Default: hide both
        ollamaGroup.style.display = 'none';
        geminiGroup.style.display = 'none';
    }
    
    console.log(`Guardrail provider changed to: ${provider}, showing ${provider === 'ollama' ? 'Ollama' : 'Gemini'} options`);
}

function loadConfig() {
    // Load from localStorage or API
    const saved = localStorage.getItem('dentalChatbot_config');
    if (saved) {
        const config = JSON.parse(saved);
        document.getElementById('llmProvider').value = config.llm_provider || 'ollama';
        document.getElementById('guardrailProvider').value = config.guardrail_provider || 'ollama';
        document.getElementById('ollamaChatModel').value = config.ollama_model || 'qwen2.5:7b';
        document.getElementById('ollamaGuardrailModel').value = config.ollama_guardrail_model || 'phi-3';
        document.getElementById('geminiChatModel').value = config.gemini_model || 'gemini-1.5-flash';
        document.getElementById('geminiGuardrailModel').value = config.gemini_guardrail_model || 'gemini-1.5-flash';
        document.getElementById('searchTool').value = config.search_tool || 'duckduckgo';
    }
    
    // Toggle options AFTER setting values (important!)
    toggleProviderOptions();
    toggleGuardrailOptions();
    
    // Debug logging
    const guardrailProvider = document.getElementById('guardrailProvider')?.value;
    const geminiGroup = document.getElementById('geminiGuardrailGroup');
    console.log('Config loaded - Guardrail provider:', guardrailProvider);
    console.log('Gemini guardrail group found:', !!geminiGroup);
    console.log('Gemini guardrail group display:', geminiGroup?.style.display);
}

async function saveConfig(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const config = {
        llm_provider: formData.get('llm_provider'),
        guardrail_provider: formData.get('guardrail_provider'),
        ollama_model: formData.get('ollama_model'),
        ollama_guardrail_model: formData.get('ollama_guardrail_model'),
        gemini_model: formData.get('gemini_model'),
        gemini_guardrail_model: formData.get('gemini_guardrail_model'),
        search_tool: formData.get('search_tool')
    };
    
    // Save to localStorage
    localStorage.setItem('dentalChatbot_config', JSON.stringify(config));
    
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
            showStatus('Configuration saved successfully!', 'success');
        } else {
            showStatus('Failed to save configuration to server', 'error');
        }
    } catch (error) {
        console.error('Error saving config:', error);
        showStatus('Configuration saved locally. Server update failed.', 'error');
    }
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'block';
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 3000);
}
