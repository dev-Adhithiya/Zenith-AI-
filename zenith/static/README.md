# Zenith AI - Gemini-Inspired Liquid Glass UI

## UI Features

### Design System
- **Liquid Glass Glassmorphism** - Blur effects with translucent backgrounds
- **Dark Mode** - Gray tones (#131314 base)
- **Light Mode** - White tones (#ffffff base)
- **Gemini-inspired** - Google Sans font, similar layout and interactions

### Color Palette

**Light Mode:**
- Background: `#ffffff` (white)
- Glass: `rgba(255, 255, 255, 0.7)` with blur
- Text: `#202124` (near-black)
- Accent: `#1a73e8` (Google Blue)

**Dark Mode:**
- Background: `#131314` (dark gray)
- Glass: `rgba(30, 31, 32, 0.7)` with blur
- Text: `#e8eaed` (light gray)
- Accent: `#8ab4f8` (light blue)

### Components

1. **Chat Interface**
   - Welcome screen with suggestion cards
   - Message bubbles (user & assistant)
   - Typing indicator animation
   - Suggestions chips
   - Auto-resizing input

2. **Sidebar Navigation**
   - Chat, Calendar, Tasks, Notes views
   - User profile section
   - Glass morphism effect

3. **Theme Toggle**
   - Floating button (top-right)
   - Smooth transitions
   - Persists preference

### Interactions

- **Suggestion Cards** - Quick-start prompts
- **Message Streaming** - Real-time responses
- **Auto-scroll** - Smooth scroll to latest message
- **Keyboard Shortcuts** - Enter to send, Shift+Enter for new line

### Responsive Design

- **Desktop** - Full sidebar + main content
- **Mobile** - Collapsible sidebar, optimized layouts

## File Structure

```
static/
├── index.html          # Main UI structure
├── css/
│   └── styles.css      # Glassmorphism styles
└── js/
    └── app.js          # Chat & API logic
```

## Usage

The UI is served at the root (`/`) of the FastAPI application.

1. **Start server:** `uvicorn main:app --reload`
2. **Open:** http://localhost:8000
3. **Authenticate:** Click "Sign in with Google"
4. **Chat:** Ask Zenith anything!

## API Integration

The frontend connects to these endpoints:
- `POST /chat` - Send messages
- `GET /auth/login` - Get OAuth URL
- `GET /auth/me` - Get current user
- `GET /calendar/events` - List events
- `GET /tasks` - List tasks
- `GET /notes` - List notes

## Customization

### Change Colors
Edit CSS variables in `static/css/styles.css`:
```css
:root {
    --accent-primary: #1a73e8;  /* Your brand color */
    --glass-bg: rgba(255, 255, 255, 0.7);
}
```

### Add Features
- Edit `static/js/app.js` for new functionality
- All API calls go through the `APIClient` class
- Use `ChatInterface` class for chat-related features

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires:
- CSS `backdrop-filter` support
- ES6+ JavaScript
- Fetch API
