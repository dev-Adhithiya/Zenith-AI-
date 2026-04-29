// Zenith AI API Client
// Connects to FastAPI backend

// Auto-detect API URL: use environment variable, or determine from current location
const getApiBaseUrl = () => {
  // Use explicit environment variable if set
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // For localhost development, use port 8000
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  
  // For production (Cloud Run), use same origin (the root domain)
  // API endpoints are served from the same backend
  return `${window.location.protocol}//${window.location.host}`;
};

const API_BASE_URL = getApiBaseUrl();

// Types
export interface User {
  user_id: string;
  email: string;
  name?: string;
  picture?: string;
  settings?: Record<string, any>;
  created_at?: string;
  last_login?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  metadata?: Record<string, any>;
  images?: Array<{
    id: string;
    src: string;
    filename?: string;
  }>;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  suggestions?: string[];
  intent?: Record<string, any>;
  execution_success?: boolean;
  error?: string;
  requires_confirmation?: boolean;
  pending_plan?: Record<string, any>;
}

export interface CalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  location?: string;
  description?: string;
  meet_link?: string;
  attendees?: string[];
}

export interface Task {
  id: string;
  title: string;
  notes?: string;
  due?: string;
  is_completed: boolean;
  created_at?: string;
}

export interface Note {
  note_id: string;
  title: string;
  content: string;
  tags: string[];
  source?: string;
  created_at: string;
  updated_at?: string;
}

export interface Email {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  body_text?: string;
  body_html?: string;
  is_unread: boolean;
  date: string;
}

export interface Briefing {
  status: string;
  title: string;
  content: string;
  error?: string;
  metadata?: {
    task_count: number;
    event_count: number;
    unread_count: number;
    last_updated: string;
  };
}

export interface WorkingHours {
  start: string;
  end: string;
  days: string[];
}

export interface NotificationPreferences {
  daily_briefing: boolean;
  email_alerts: boolean;
  task_reminders: boolean;
}

export interface UserPreferences {
  preferred_meeting_times: string[];
  frequent_contacts: string[];
  email_tone: string;
  custom_rules: string[];
  working_hours: WorkingHours;
  timezone: string;
  notification_preferences: NotificationPreferences;
  updated_at?: string;
}

export interface TaskPayload {
  title: string;
  description?: string | null;
  due?: string | null;
}

export interface MeetingPayload {
  title: string;
  description?: string | null;
  attendees: string[];
  start_time?: string | null;
  end_time?: string | null;
}

export interface EmailActionItem {
  id: string;
  type: 'email_action';
  action_type: 'reply' | 'task' | 'meeting' | 'ignore';
  ui_actions: string[];
  title: string;
  from: string;
  summary: string;
  reason: string;
  draft_reply?: string;
  task_payload?: TaskPayload;
  meeting_payload?: MeetingPayload;
}

export interface MeetingPrepItem {
  id: string;
  type: 'meeting_prep';
  status: 'ready' | 'needs_clarification';
  title: string;
  summary: string;
  reason: string;
  prep: {
    risks: string[];
    talking_points: string[];
  };
}

export type PriorityFeedItem = EmailActionItem | MeetingPrepItem;

// Helpers
function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

function normalizeClientErrorMessage(status: number, raw: unknown): string {
  if (typeof raw === 'string') {
    const t = raw.trim();
    if (t.length > 200) {
      return status >= 500 ? 'Server error. Please try again.' : 'Request could not be completed.';
    }
    return t;
  }
  if (Array.isArray(raw)) {
    return 'Invalid request. Please check your input.';
  }
  if (raw && typeof raw === 'object') {
    return 'Request could not be completed.';
  }
  return status >= 500 ? 'Server error. Please try again.' : 'Request failed.';
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let rawDetail: unknown;
    try {
      const error = await response.json();
      rawDetail = error.detail ?? error.error ?? error.message;
    } catch {
      rawDetail = response.statusText;
    }
    const safe = normalizeClientErrorMessage(response.status, rawDetail);
    if (import.meta.env.DEV) {
      console.error(`API Error ${response.status}`, { url: response.url, safe });
    }
    throw new Error(safe);
  }
  return response.json().catch(() => {
    if (import.meta.env.DEV) {
      console.error('Failed to parse response as JSON');
    }
    throw new Error('Invalid server response');
  });
}

// Auth API
export const authAPI = {
  async login(): Promise<{ authorization_url: string; state: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/login`);
    return handleResponse(response);
  },

  async getCurrentUser(): Promise<User> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },
};

// Chat API
export const chatAPI = {
  async sendMessage(message: string, sessionId?: string, images?: File[], emailDraft?: Record<string, any>, signal?: AbortSignal): Promise<ChatResponse> {
    // Always use FormData for consistency (supports both text-only and with-images)
    const formData = new FormData();
    formData.append('message', message);
    if (sessionId) {
      formData.append('session_id', sessionId);
    }
    if (emailDraft) {
      formData.append('email_draft', JSON.stringify(emailDraft));
    }
    
    // Append images if provided
    if (images && images.length > 0) {
      images.forEach((file) => {
        formData.append('images', file);
      });
    }

    const token = localStorage.getItem('access_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers,
        // DO NOT set Content-Type - let browser set it to multipart/form-data
        body: formData,
        signal,
      });
      return handleResponse(response);
    } catch (error) {
      console.error('[Chat] Request failed:', error);
      throw error;
    }
  },

  async createSession(): Promise<{ session_id: string }> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getSessions(limit = 10): Promise<{ sessions: any[]; count: number }> {
    try {
      const response = await fetch(`${API_BASE_URL}/sessions?limit=${limit}`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) {
        // Return empty sessions on error (e.g., index not ready)
        return { sessions: [], count: 0 };
      }
      return response.json();
    } catch (err) {
      return { sessions: [], count: 0 };
    }
  },

  async deleteSession(sessionId: string): Promise<{ result: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getSessionMessages(sessionId: string): Promise<{ session_id: string; messages: ChatMessage[]; count: number }> {
    const response = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// Calendar API
export const calendarAPI = {
  async listEvents(maxResults = 10, query?: string): Promise<{ events: CalendarEvent[]; count: number }> {
    const params = new URLSearchParams({
      max_results: maxResults.toString(),
      ...(query && { query }),
    });
    const response = await fetch(`${API_BASE_URL}/calendar/events?${params}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async createEvent(event: {
    summary: string;
    start_time: string;
    end_time: string;
    description?: string;
    location?: string;
    attendees?: string[];
    add_google_meet?: boolean;
  }): Promise<CalendarEvent> {
    const response = await fetch(`${API_BASE_URL}/calendar/events`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(event),
    });
    return handleResponse(response);
  },

  async quickAdd(text: string): Promise<CalendarEvent> {
    const response = await fetch(`${API_BASE_URL}/calendar/quick-add`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ text }),
    });
    return handleResponse(response);
  },

  async createEventWithMeet(event: {
    summary: string;
    start_time: string;
    end_time: string;
    description?: string;
    location?: string;
    attendees?: string[];
  }): Promise<CalendarEvent> {
    return calendarAPI.createEvent({ ...event, add_google_meet: true });
  },
};

// Tasks API
export const tasksAPI = {
  async listTasks(showCompleted = false): Promise<{ tasks: Task[]; count: number }> {
    const params = new URLSearchParams({ show_completed: showCompleted.toString() });
    const response = await fetch(`${API_BASE_URL}/tasks?${params}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async addTask(task: { title: string; notes?: string; due_date?: string }): Promise<Task> {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(task),
    });
    return handleResponse(response);
  },

  async completeTask(taskId: string): Promise<Task> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/complete`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async uncompleteTask(taskId: string): Promise<Task> {
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/uncomplete`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async setReminder(reminder: { title: string; remind_at: string; notes?: string }): Promise<Task> {
    const response = await fetch(`${API_BASE_URL}/tasks/reminder`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(reminder),
    });
    return handleResponse(response);
  },

  async editTaskPreview(task: { title: string; description?: string; due?: string }): Promise<{ status: string; task_payload: TaskPayload }> {
    const response = await fetch(`${API_BASE_URL}/tasks/edit`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(task),
    });
    return handleResponse(response);
  },
};

// Notes API
export const notesAPI = {
  async listNotes(limit = 20, source?: string): Promise<{ notes: Note[]; count: number }> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      ...(source && { source }),
    });
    const response = await fetch(`${API_BASE_URL}/notes?${params}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async saveNote(note: { title: string; content: string; tags?: string[]; source?: string }): Promise<Note> {
    const response = await fetch(`${API_BASE_URL}/notes`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(note),
    });
    return handleResponse(response);
  },

  async searchNotes(query: string, limit = 5): Promise<{ notes: Note[]; count: number }> {
    const response = await fetch(`${API_BASE_URL}/notes/search`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ query, limit }),
    });
    return handleResponse(response);
  },
};

// Gmail API
export const gmailAPI = {
  async searchMessages(query?: string, maxResults = 10): Promise<{ emails: Email[]; count: number }> {
    const params = new URLSearchParams({
      max_results: maxResults.toString(),
      ...(query && { query }),
    });
    const response = await fetch(`${API_BASE_URL}/gmail/messages?${params}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getMessage(id: string): Promise<Email> {
    const response = await fetch(`${API_BASE_URL}/gmail/messages/${id}`, {      
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async sendEmail(email: {
    to: string[];
    subject: string;
    body: string;
    cc?: string[];
    bcc?: string[];
    html_body?: string;
    reply_to_thread_id?: string;
  }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/gmail/send`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(email),
    });
    return handleResponse(response);
  },
};

// Health check
export const healthAPI = {
  async check(): Promise<{ status: string; version: string; timestamp: string }> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return handleResponse(response);
  },
};

// Briefing API
export const briefingAPI = {
  async getBriefing(): Promise<Briefing> {
    const response = await fetch(`${API_BASE_URL}/agent/briefing`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

export const preferencesAPI = {
  async getPreferences(): Promise<{ preferences: UserPreferences; updated_at?: string }> {
    const response = await fetch(`${API_BASE_URL}/preferences`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async updatePreferences(preferences: Partial<UserPreferences>): Promise<{ preferences: UserPreferences; updated_at?: string }> {
    const response = await fetch(`${API_BASE_URL}/preferences`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(preferences),
    });
    return handleResponse(response);
  },
};

export const priorityAPI = {
  async getFeed(): Promise<{ status: string; items: PriorityFeedItem[]; metadata?: Record<string, unknown> }> {
    const response = await fetch(`${API_BASE_URL}/insights/priority-feed`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};
