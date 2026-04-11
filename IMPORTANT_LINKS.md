# 🔗 Important Links - Priyanshu AI Chat Assistant

## 📱 Live Deployments

### Frontend (Vercel)
- **URL:** https://priyanshu-ai-chat-assistant.vercel.app/
- **Dashboard:** https://vercel.com/dashboard
- **Project:** Priyanshu-AI---Chat-Assistant

### Backend (Render)
- **URL:** https://priyanshu-ai-chat-assistant.onrender.com/
- **Dashboard:** https://dashboard.render.com
- **Service Name:** priyanshu-ai-chat-assistant
- **Health Check:** https://priyanshu-ai-chat-assistant.onrender.com/health
- **Chat API:** https://priyanshu-ai-chat-assistant.onrender.com/chat

### Avatar Asset (from Backend)
- **URL:** https://priyanshu-ai-chat-assistant.onrender.com/public/avatar_GIF.mp4

---

## 💻 Development

### GitHub Repository
- **URL:** https://github.com/PriyanshuS27/Priyanshu-AI---Chat-Assistant
- **Owner:** PriyanshuS27
- **Repository:** Priyanshu-AI---Chat-Assistant
- **Branch:** main

### Local Development
- **Frontend:** http://localhost:3000 (if running React dev server)
- **Backend:** http://localhost:8000
- **Chat Endpoint:** http://localhost:8000/chat

---

## 🔑 API & Services

### Google Gemini AI
- **API Studio:** https://aistudio.google.com/app/apikey
- **Model Used:** gemini-2.5-flash
- **Environment Variable:** `GEMINI_API_KEY`

### Telegram Notifications
- **Bot Token:** Stored in `.env` as `TELEGRAM_BOT_TOKEN`
- **Chat ID:** Stored in `.env` as `TELEGRAM_CHAT_ID`

### Pushover Notifications (Fallback)
- **Token:** Stored in `.env` as `PUSHOVER_TOKEN`
- **User ID:** Stored in `.env` as `PUSHOVER_USER`

---

## 📁 Project Structure

```
Priyanshu-AI---Chat-Assistant/
├── 1_foundations/           # Backend (FastAPI + Google Gemini)
│   ├── app.py              # Main FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── .env                # Environment variables (NOT in git)
│   └── me/                 # Personal data (resume, LinkedIn)
│
├── frontend/               # Frontend (React + Vite)
│   ├── index.html         # Main HTML with embedded React
│   ├── package.json       # Node dependencies
│   ├── vite.config.js     # Vite configuration
│   └── public/            # Static assets (avatar, etc)
│
├── render.yaml            # Render.com deployment config
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
└── IMPORTANT_LINKS.md     # This file
```

---

## 🚀 Deployment Checklist

### Before Pushing to GitHub
- [ ] `.env` file is in `.gitignore`
- [ ] No sensitive keys in code
- [ ] All changes committed locally
- [ ] Code tested on localhost

### Render Deployment
- [ ] Environment variables set in Render dashboard
- [ ] `GEMINI_API_KEY` updated to valid key
- [ ] Service auto-redeployed after `git push`

### Vercel Deployment
- [ ] Frontend code updated
- [ ] Avatar URL points to Render backend
- [ ] Build succeeds without errors

---

## 📋 Common Tasks

### Update Avatar
1. Replace file in `frontend/public/avatar_GIF.mp4`
2. Both deployments pick it up automatically

### Update API Key
1. Generate new key at: https://aistudio.google.com/app/apikey
2. Update `.env` locally
3. Update Render environment variables
4. Restart Render service

### Test Locally
```bash
cd 1_foundations
python app.py
# Visit http://localhost:8000
```

### Push Changes
```bash
git add .
git commit -m "Your message"
git push origin main
```

---

## 🔐 Security Notes

- ✅ `.env` file is gitignored (never commit)
- ✅ API keys stored only in environment variables
- ✅ Resume PDF in private `me/` folder
- ⚠️ Keep Telegram bot token safe
- ⚠️ Keep Pushover token safe

---

**Last Updated:** April 11, 2026
**Created by:** GitHub Copilot
