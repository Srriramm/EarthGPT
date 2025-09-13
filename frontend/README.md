# EarthGPT Frontend

A beautiful, modern React frontend for the EarthGPT sustainability AI assistant.

## Features

### 🎨 **Modern UI/UX**
- Clean, responsive design with Tailwind CSS
- Dark/Light mode toggle
- Smooth animations with Framer Motion
- Mobile-first responsive design

### 💬 **Chat Interface**
- Multiple chat sessions with sidebar navigation
- Real-time messaging with typing indicators
- Message history and persistence
- Copy message functionality

### 🌱 **Sustainability Focus**
- Built-in sustainability topic suggestions
- Guardrail warnings for off-topic queries
- Environmental-themed color scheme
- Sustainability tips and badges

### 🔧 **Advanced Features**
- Progressive summarization support
- Session management (create, delete, switch)
- Online/offline status indicators
- Toast notifications
- Local storage persistence

## Getting Started

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Installation

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start development server:**
```bash
npm start
```

The app will open at `http://localhost:3000`

### Building for Production

```bash
npm run build
```

## Project Structure

```
frontend/
├── public/
│   ├── index.html
│   └── manifest.json
├── src/
│   ├── components/
│   │   ├── Sidebar.tsx
│   │   ├── ChatArea.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   └── Header.tsx
│   ├── hooks/
│   │   ├── useChat.ts
│   │   └── useTheme.ts
│   ├── services/
│   │   └── api.ts
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   ├── index.tsx
│   └── index.css
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000/api/v1` by default.

### Environment Variables

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
```

## Key Components

### **Sidebar**
- Chat session management
- New chat creation
- Session switching and deletion
- Dark mode toggle

### **ChatArea**
- Message display with animations
- Loading indicators
- Guardrail warnings
- Welcome screen

### **ChatInput**
- Message composition
- Sustainability suggestions
- Guardrail detection
- Auto-resize textarea

### **ChatMessage**
- Message rendering
- Copy functionality
- Summary/detailed response handling
- Sustainability tips

## Styling

The app uses Tailwind CSS with custom sustainability-themed colors:

- **Earth Green**: Primary brand color
- **Forest Green**: Secondary accent color
- **Custom animations**: Fade-in, slide-up, pulse effects

## State Management

- **useChat**: Manages chat sessions, messages, and API calls
- **useTheme**: Handles dark/light mode switching
- **Local Storage**: Persists sessions and theme preferences

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.



