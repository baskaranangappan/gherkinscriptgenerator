/**
 * BDD Test Generator - Frontend Application (FastAPI + WebSocket)
 * Handles UI interactions and real-time WebSocket communication
 */

class BDDTestGenerator {
    constructor() {
        this.currentTaskId = null;
        this.websocket = null;
        this.config = null;
        
        this.init();
    }

    init() {
        this.loadConfig();
        this.loadTaskHistory();
        this.attachEventListeners();
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.config = data;
                this.populateModelDropdown('groq');
            }
        } catch (error) {
            this.showToast('Failed to load configuration', 'error');
        }
    }

    attachEventListeners() {
        // Generate button
        document.getElementById('generate-btn').addEventListener('click', () => {
            this.generateTests();
        });

        // Clear button
        document.getElementById('clear-btn').addEventListener('click', () => {
            this.clearForm();
        });

        // Refresh history
        document.getElementById('refresh-history').addEventListener('click', () => {
            this.loadTaskHistory();
        });

        // LLM provider change
        document.getElementById('llm-provider').addEventListener('change', (e) => {
            this.populateModelDropdown(e.target.value);
        });

        // Download buttons
        document.getElementById('download-hover').addEventListener('click', () => {
            this.downloadFeature('hover');
        });

        document.getElementById('download-popup').addEventListener('click', () => {
            this.downloadFeature('popup');
        });
    }

    populateModelDropdown(provider) {
        if (!this.config || !this.config.models[provider]) return;

        const modelSelect = document.getElementById('llm-model');
        modelSelect.innerHTML = '';

        this.config.models[provider].forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });
    }

    connectWebSocket(taskId) {
        // Close existing connection
        if (this.websocket) {
            this.websocket.close();
        }

        // WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${taskId}`;
        
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected');
            // Request initial status
            this.websocket.send('get_status');
        };

        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.showToast('Connection error, falling back to polling', 'warning');
            // Fallback to polling if WebSocket fails
            this.startPolling();
        };

        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
        };
    }

    handleWebSocketMessage(message) {
        console.log('WebSocket message:', message);

        switch (message.type) {
            case 'status':
                this.updateProgress({
                    progress: message.progress,
                    status: message.status,
                    current_step: message.current_step
                });
                break;

            case 'complete':
                this.handleCompletion(message);
                break;

            case 'error':
                this.handleFailure(message);
                break;
        }
    }

    async generateTests() {
        const url = document.getElementById('url').value.trim();
        
        if (!url) {
            this.showToast('Please enter a URL', 'error');
            return;
        }

        const llmProvider = document.getElementById('llm-provider').value;
        const llmModel = document.getElementById('llm-model').value;
        const headless = document.getElementById('headless').checked;

        const payload = {
            url: url,
            llm_provider: llmProvider,
            llm_model: llmModel,
            headless: headless,
            temperature: 0.3,
            max_tokens: 4096
        };

        try {
            // Disable generate button
            const generateBtn = document.getElementById('generate-btn');
            generateBtn.disabled = true;
            generateBtn.textContent = '⏳ Generating...';

            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (data.status === 'success') {
                this.currentTaskId = data.task_id;
                this.showToast('Test generation started!', 'success');
                
                // Show progress panel
                document.getElementById('progress-panel').style.display = 'block';
                document.getElementById('results-panel').style.display = 'none';
                
                // Connect WebSocket for real-time updates
                this.connectWebSocket(data.task_id);
            } else {
                this.showToast(data.message || 'Failed to start generation', 'error');
                generateBtn.disabled = false;
                generateBtn.textContent = '🚀 Generate Tests';
            }
        } catch (error) {
            this.showToast('Error: ' + error.message, 'error');
            const generateBtn = document.getElementById('generate-btn');
            generateBtn.disabled = false;
            generateBtn.textContent = '🚀 Generate Tests';
        }
    }

    // Fallback polling method if WebSocket fails
    startPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        this.pollingInterval = setInterval(() => {
            this.checkTaskStatus();
        }, 2000);

        // Initial check
        this.checkTaskStatus();
    }

    async checkTaskStatus() {
        if (!this.currentTaskId) return;

        try {
            const response = await fetch(`/api/task/${this.currentTaskId}`);
            const data = await response.json();

            if (data.status === 'success') {
                const task = data.task;
                
                // Update progress
                this.updateProgress(task);

                // Check if completed
                if (task.status === 'completed') {
                    if (this.pollingInterval) {
                        clearInterval(this.pollingInterval);
                    }
                    this.handleCompletion({result: data});
                } else if (task.status === 'failed') {
                    if (this.pollingInterval) {
                        clearInterval(this.pollingInterval);
                    }
                    this.handleFailure(task);
                }
            }
        } catch (error) {
            console.error('Error checking task status:', error);
        }
    }

    updateProgress(task) {
        const progressFill = document.getElementById('progress-fill');
        const progressPercent = document.getElementById('progress-percent');
        const progressStatus = document.getElementById('progress-status');
        const currentStep = document.getElementById('current-step');

        progressFill.style.width = `${task.progress}%`;
        progressPercent.textContent = `${task.progress}%`;
        progressStatus.textContent = task.status;
        currentStep.textContent = task.current_step || 'Processing...';
    }

    async handleCompletion(message) {
        this.showToast('Test generation completed!', 'success');
        
        // Close WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        // Reset generate button
        const generateBtn = document.getElementById('generate-btn');
        generateBtn.disabled = false;
        generateBtn.textContent = '🚀 Generate Tests';

        // Fetch complete task data
        const response = await fetch(`/api/task/${this.currentTaskId}`);
        const data = await response.json();

        if (data.status === 'success') {
            // Show results
            document.getElementById('results-panel').style.display = 'block';

            // Display features
            data.features.forEach(feature => {
                if (feature.feature_type === 'hover') {
                    document.getElementById('hover-preview').textContent = feature.feature_content;
                    document.getElementById('download-hover').disabled = false;
                } else if (feature.feature_type === 'popup') {
                    document.getElementById('popup-preview').textContent = feature.feature_content;
                    document.getElementById('download-popup').disabled = false;
                }
            });

            // Load logs
            this.loadTaskLogs(this.currentTaskId);

            // Refresh history
            this.loadTaskHistory();
        }
    }

    handleFailure(task) {
        const errorMsg = task.error_message || task.error || 'Unknown error';
        this.showToast('Test generation failed: ' + errorMsg, 'error');
        
        // Close WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        // Reset generate button
        const generateBtn = document.getElementById('generate-btn');
        generateBtn.disabled = false;
        generateBtn.textContent = '🚀 Generate Tests';

        // Load logs to show error details
        this.loadTaskLogs(this.currentTaskId || task.task_id);
        
        // Refresh history
        this.loadTaskHistory();
    }

    async loadTaskLogs(taskId) {
        try {
            const response = await fetch(`/api/task/${taskId}/logs`);
            const data = await response.json();

            if (data.status === 'success') {
                const logsPanel = document.getElementById('logs-panel');
                const logsContent = document.getElementById('logs-content');
                
                logsContent.innerHTML = '';
                
                data.logs.forEach(log => {
                    const logEntry = document.createElement('div');
                    logEntry.className = 'log-entry';
                    logEntry.innerHTML = `
                        <span class="log-level ${log.log_level}">[${log.log_level}]</span>
                        <span>${log.created_at}</span> - ${log.message}
                    `;
                    logsContent.appendChild(logEntry);
                });

                logsPanel.style.display = 'block';
            }
        } catch (error) {
            console.error('Error loading logs:', error);
        }
    }

    async loadTaskHistory() {
        try {
            const response = await fetch('/api/tasks?limit=20');
            const data = await response.json();

            if (data.status === 'success') {
                const historyContainer = document.getElementById('task-history');
                historyContainer.innerHTML = '';

                if (data.tasks.length === 0) {
                    historyContainer.innerHTML = '<p class="text-muted">No tasks yet. Generate your first test!</p>';
                    return;
                }

                data.tasks.forEach(task => {
                    const taskItem = this.createTaskItem(task);
                    historyContainer.appendChild(taskItem);
                });
            }
        } catch (error) {
            console.error('Error loading task history:', error);
        }
    }

    createTaskItem(task) {
        const div = document.createElement('div');
        div.className = 'task-item';
        div.onclick = () => this.viewTask(task.id);

        const statusClass = `status-${task.status}`;

        div.innerHTML = `
            <div class="task-header">
                <div class="task-url">${task.url}</div>
                <span class="task-status ${statusClass}">${task.status.toUpperCase()}</span>
            </div>
            <div class="task-meta">
                <span>🤖 ${task.llm_provider} - ${task.llm_model}</span>
                <span>📅 ${new Date(task.created_at).toLocaleString()}</span>
                ${task.progress !== null ? `<span>📊 ${task.progress}%</span>` : ''}
            </div>
        `;

        return div;
    }

    async viewTask(taskId) {
        try {
            const response = await fetch(`/api/task/${taskId}`);
            const data = await response.json();

            if (data.status === 'success') {
                const task = data.task;
                
                // Populate URL field
                document.getElementById('url').value = task.url;

                // If task is completed, show features
                if (task.status === 'completed' && data.features.length > 0) {
                    document.getElementById('results-panel').style.display = 'block';
                    
                    data.features.forEach(feature => {
                        if (feature.feature_type === 'hover') {
                            document.getElementById('hover-preview').textContent = feature.feature_content;
                            document.getElementById('download-hover').disabled = false;
                        } else if (feature.feature_type === 'popup') {
                            document.getElementById('popup-preview').textContent = feature.feature_content;
                            document.getElementById('download-popup').disabled = false;
                        }
                    });

                    this.currentTaskId = taskId;
                    this.loadTaskLogs(taskId);
                }

                this.showToast('Task loaded', 'info');
            }
        } catch (error) {
            this.showToast('Error loading task: ' + error.message, 'error');
        }
    }

    async downloadFeature(featureType) {
        if (!this.currentTaskId) {
            this.showToast('No task selected', 'error');
            return;
        }

        try {
            window.location.href = `/api/download/${this.currentTaskId}/${featureType}`;
            this.showToast('Downloading feature file...', 'success');
        } catch (error) {
            this.showToast('Download failed: ' + error.message, 'error');
        }
    }

    clearForm() {
        document.getElementById('url').value = '';
        document.getElementById('progress-panel').style.display = 'none';
        document.getElementById('results-panel').style.display = 'none';
        document.getElementById('logs-panel').style.display = 'none';
        
        document.getElementById('hover-preview').textContent = '';
        document.getElementById('popup-preview').textContent = '';
        
        document.getElementById('download-hover').disabled = true;
        document.getElementById('download-popup').disabled = true;

        this.currentTaskId = null;

        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }

        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        this.showToast('Form cleared', 'info');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                container.removeChild(toast);
            }, 300);
        }, 4000);
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new BDDTestGenerator();
});
