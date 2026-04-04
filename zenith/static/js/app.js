// Zenith AI - Frontend Application
// Gemini-inspired glassmorphism UI with chat interface

// ==================== Configuration ====================
const API_BASE_URL = window.location.origin;
let authToken = localStorage.getItem('zenith_token');
let currentUser = null;
let currentSessionId = localStorage.getItem('zenith_session_id');

// ==================== Theme Management ====================
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('zenith_theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme();
        document.getElementById('themeToggle').addEventListener('click', () => this.toggle());
    }

    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
        localStorage.setItem('zenith_theme', this.theme);
    }

    toggle() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme();
    }
}

// ==================== API Client ====================
class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }

    get token() {
        return authToken;
    }

    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${this.baseURL}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            this.handleUnauthorized();
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || error.detail || 'Request failed');
        }

        return response.json();
    }

    handleUnauthorized() {
        localStorage.removeItem('zenith_token');
        localStorage.removeItem('zenith_user');
        authToken = null;
        currentUser = null;
        showLoginModal();
    }

    async chat(message, sessionId) {
        return this.request('/chat', {
            method: 'POST',
            body: JSON.stringify({ message, session_id: sessionId })
        });
    }

    async getAuthUrl() {
        return this.request('/auth/login');
    }

    async getCurrentUser() {
        return this.request('/auth/me');
    }

    async listEvents(maxResults = 10) {
        return this.request(`/calendar/events?max_results=${maxResults}`);
    }

    async listTasks() {
        return this.request('/tasks');
    }

    async listNotes(limit = 20) {
        return this.request(`/notes?limit=${limit}`);
    }
}

const api = new APIClient(API_BASE_URL);

// ==================== Chat Interface ====================
class ChatInterface {
    constructor() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.suggestionsBar = document.getElementById('suggestionsBar');
        this.isTyping = false;

        this.init();
    }

    init() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });

        // Suggestion cards
        document.querySelectorAll('.suggestion-card').forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.getAttribute('data-prompt');
                this.messageInput.value = prompt;
                this.sendMessage();
            });
        });

        // Enter to send (Shift+Enter for new line)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        if (!authToken) {
            showLoginModal();
            return;
        }

        // Hide welcome screen
        if (this.welcomeScreen && !this.welcomeScreen.classList.contains('hidden')) {
            this.welcomeScreen.classList.add('hidden');
        }

        // Add user message
        this.addMessage('user', message);
        
        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';

        // Show typing indicator
        this.showTypingIndicator();
        this.isTyping = true;

        try {
            // Create session if needed
            if (!currentSessionId) {
                currentSessionId = this.generateSessionId();
                localStorage.setItem('zenith_session_id', currentSessionId);
            }

            // Send to API
            const response = await api.chat(message, currentSessionId);

            // Remove typing indicator
            this.hideTypingIndicator();
            
            // Add assistant response
            this.addMessage('assistant', response.response);

            // Show suggestions
            if (response.suggestions && response.suggestions.length > 0) {
                this.showSuggestions(response.suggestions);
            }

        } catch (error) {
            console.error('Chat error:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', `I encountered an error: ${error.message}. Please try again.`);
        } finally {
            this.isTyping = false;
        }
    }

    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = role === 'user' 
            ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
            : '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/></svg>';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing-message';
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/></svg>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const typingMessage = this.messagesContainer.querySelector('.typing-message');
        if (typingMessage) {
            typingMessage.remove();
        }
    }

    showSuggestions(suggestions) {
        this.suggestionsBar.innerHTML = '';
        this.suggestionsBar.style.display = 'flex';

        suggestions.forEach(suggestion => {
            const chip = document.createElement('button');
            chip.className = 'suggestion-chip';
            chip.textContent = suggestion;
            chip.addEventListener('click', () => {
                this.messageInput.value = suggestion;
                this.sendMessage();
                this.suggestionsBar.style.display = 'none';
            });
            this.suggestionsBar.appendChild(chip);
        });
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// ==================== Navigation ====================
class Navigation {
    constructor() {
        this.navItems = document.querySelectorAll('.nav-item[data-view]');
        this.views = document.querySelectorAll('.view');
        
        this.init();
    }

    init() {
        this.navItems.forEach(item => {
            item.addEventListener('click', () => {
                const viewId = item.getAttribute('data-view') + 'View';
                this.switchView(viewId);
                
                // Update active state
                this.navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');
            });
        });
    }

    switchView(viewId) {
        this.views.forEach(view => {
            view.classList.remove('active');
            if (view.id === viewId) {
                view.classList.add('active');
                this.loadViewData(viewId);
            }
        });
    }

    async loadViewData(viewId) {
        if (!authToken) return;

        try {
            switch(viewId) {
                case 'calendarView':
                    await this.loadCalendar();
                    break;
                case 'tasksView':
                    await this.loadTasks();
                    break;
                case 'notesView':
                    await this.loadNotes();
                    break;
            }
        } catch (error) {
            console.error('Error loading view data:', error);
        }
    }

    async loadCalendar() {
        const content = document.getElementById('calendarContent');
        content.innerHTML = '<p class="loading-text">Loading calendar...</p>';
        
        try {
            const data = await api.listEvents();
            
            if (data.events.length === 0) {
                content.innerHTML = '<p class="loading-text">No upcoming events</p>';
                return;
            }

            const html = data.events.map(event => `
                <div class="glass" style="padding: 16px; margin-bottom: 12px; border-radius: 12px;">
                    <h3 style="margin-bottom: 8px;">${event.summary}</h3>
                    <p style="color: var(--text-secondary); font-size: 0.875rem;">
                        📅 ${new Date(event.start).toLocaleString()}
                    </p>
                    ${event.location ? `<p style="color: var(--text-secondary); font-size: 0.875rem;">📍 ${event.location}</p>` : ''}
                    ${event.meet_link ? `<a href="${event.meet_link}" target="_blank" style="color: var(--accent-primary);">Join Meeting</a>` : ''}
                </div>
            `).join('');

            content.innerHTML = html;
        } catch (error) {
            content.innerHTML = `<p class="loading-text">Error loading calendar: ${error.message}</p>`;
        }
    }

    async loadTasks() {
        const content = document.getElementById('tasksContent');
        content.innerHTML = '<p class="loading-text">Loading tasks...</p>';
        
        try {
            const data = await api.listTasks();
            
            if (data.tasks.length === 0) {
                content.innerHTML = '<p class="loading-text">No tasks found</p>';
                return;
            }

            const html = data.tasks.map(task => `
                <div class="glass" style="padding: 16px; margin-bottom: 12px; border-radius: 12px; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 1.25rem;">${task.is_completed ? '✅' : '⬜'}</span>
                    <div style="flex: 1;">
                        <h3 style="margin-bottom: 4px; ${task.is_completed ? 'text-decoration: line-through; opacity: 0.6;' : ''}">${task.title}</h3>
                        ${task.due ? `<p style="color: var(--text-secondary); font-size: 0.875rem;">Due: ${new Date(task.due).toLocaleDateString()}</p>` : ''}
                    </div>
                </div>
            `).join('');

            content.innerHTML = html;
        } catch (error) {
            content.innerHTML = `<p class="loading-text">Error loading tasks: ${error.message}</p>`;
        }
    }

    async loadNotes() {
        const content = document.getElementById('notesContent');
        content.innerHTML = '<p class="loading-text">Loading notes...</p>';
        
        try {
            const data = await api.listNotes();
            
            if (data.notes.length === 0) {
                content.innerHTML = '<p class="loading-text">No notes found</p>';
                return;
            }

            const html = data.notes.map(note => `
                <div class="glass" style="padding: 16px; margin-bottom: 12px; border-radius: 12px;">
                    <h3 style="margin-bottom: 8px;">${note.title}</h3>
                    <p style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 8px;">
                        ${note.content.substring(0, 150)}${note.content.length > 150 ? '...' : ''}
                    </p>
                    ${note.tags && note.tags.length > 0 ? `
                        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                            ${note.tags.map(tag => `<span style="background: var(--accent-light); color: var(--accent-primary); padding: 4px 8px; border-radius: 12px; font-size: 0.75rem;">#${tag}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            `).join('');

            content.innerHTML = html;
        } catch (error) {
            content.innerHTML = `<p class="loading-text">Error loading notes: ${error.message}</p>`;
        }
    }
}

// ==================== Authentication ====================
function showLoginModal() {
    const modal = document.getElementById('loginModal');
    modal.classList.add('active');
}

function hideLoginModal() {
    const modal = document.getElementById('loginModal');
    modal.classList.remove('active');
}

async function handleLogin() {
    try {
        const { authorization_url } = await api.getAuthUrl();
        window.location.href = authorization_url;
    } catch (error) {
        console.error('Login error:', error);
        alert('Failed to initiate login. Please try again.');
    }
}

async function loadUser() {
    if (!authToken) {
        showLoginModal();
        return;
    }

    try {
        const user = await api.getCurrentUser();
        currentUser = user;
        localStorage.setItem('zenith_user', JSON.stringify(user));
        
        // Update UI
        document.getElementById('userName').textContent = user.name || user.email;
        hideLoginModal();
    } catch (error) {
        console.error('Failed to load user:', error);
        showLoginModal();
    }
}

// Check for OAuth callback (handles auth data from URL fragment after redirect)
async function checkOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check for auth error
    const authError = urlParams.get('auth_error');
    if (authError) {
        console.error('OAuth error:', authError);
        document.body.innerHTML = `<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-size: 1.25rem; color: red; text-align: center; padding: 20px;">
            Authentication failed: ${decodeURIComponent(authError)}<br><br>
            <a href="/" style="color: #1a73e8;">Return to home</a>
        </div>`;
        // Clear URL params
        window.history.replaceState({}, document.title, '/');
        return true;
    }
    
    // Check for successful auth (data in URL fragment)
    const authSuccess = urlParams.get('auth_success');
    if (authSuccess && window.location.hash) {
        try {
            // Parse auth data from URL fragment
            const hashParams = new URLSearchParams(window.location.hash.substring(1));
            const accessToken = hashParams.get('access_token');
            const userData = hashParams.get('user');
            
            if (accessToken && userData) {
                // Save token and user data
                authToken = accessToken;
                localStorage.setItem('zenith_token', authToken);
                localStorage.setItem('zenith_user', userData);
                
                console.log('Authentication successful');
                
                // Clear URL (remove auth data from URL for security)
                window.history.replaceState({}, document.title, '/');
                
                // Reload to show authenticated UI
                window.location.reload();
                return true;
            }
        } catch (error) {
            console.error('Error processing auth callback:', error);
        }
    }
    
    // Legacy support: Check for OAuth code in URL (direct API call flow)
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    
    if (code) {
        // OAuth callback - show loading
        document.body.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100vh; font-size: 1.25rem;">Signing in...</div>';
        
        try {
            // Exchange code for token by calling backend
            const response = await fetch(`${API_BASE_URL}/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`);
            
            // If we get a redirect, follow it (this shouldn't happen with new backend)
            if (response.redirected) {
                window.location.href = response.url;
                return true;
            }
            
            if (!response.ok) {
                throw new Error(`Authentication failed: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Save token and user data
            authToken = data.access_token;
            localStorage.setItem('zenith_token', authToken);
            localStorage.setItem('zenith_user', JSON.stringify(data.user));
            
            // Redirect to home (remove code from URL)
            window.location.href = '/';
        } catch (error) {
            console.error('OAuth callback error:', error);
            document.body.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100vh; font-size: 1.25rem; color: red;">
                Authentication failed: ${error.message}<br><br>
                <a href="/" style="color: #1a73e8;">Return to home</a>
            </div>`;
        }
        
        return true;
    }
    
    return false;
}

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', async () => {
    // Check for OAuth callback
    if (await checkOAuthCallback()) return;

    // Initialize theme
    new ThemeManager();

    // Load user if authenticated
    if (authToken) {
        loadUser();
    } else {
        showLoginModal();
    }

    // Initialize chat interface
    new ChatInterface();

    // Initialize navigation
    new Navigation();

    // Login button
    document.getElementById('loginBtn').addEventListener('click', handleLogin);

    // User profile click
    document.getElementById('userProfile').addEventListener('click', () => {
        if (!authToken) {
            showLoginModal();
        }
    });

    console.log('%c🛡️ Zenith AI', 'font-size: 24px; font-weight: bold; color: #1a73e8;');
    console.log('%cYour elite personal assistant is ready.', 'font-size: 14px; color: #5f6368;');
});

// ==================== Service Worker (Optional) ====================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment to enable service worker for PWA
        // navigator.serviceWorker.register('/sw.js');
    });
}
