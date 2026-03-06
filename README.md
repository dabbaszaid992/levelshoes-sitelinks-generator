# Level Shoes — Sitelinks Generator Setup
==========================================

## First time setup (do this once)

### 1. Install Python
Download from https://python.org if you don't have it.

### 2. Open this folder in VS Code terminal
Right-click the folder → "Open in Terminal"

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Add your OpenAI API key
Open the `.env` file and replace the placeholder:
```
OPENAI_API_KEY=sk-paste-your-real-key-here
```
Get your key from: https://platform.openai.com/api-keys

---

## Every time you use the tool

### Step 1 — Start the server (in VS Code terminal)
```
python server.py
```
You'll see: ✅ Server starting — key loaded

### Step 2 — Open the HTML in your browser
Right-click `LevelShoes_Sitelinks_Generator.html` → Open with Live Server
OR just double-click the file to open in browser.

The green dot in the AI Studio panel confirms the server is connected.

---

## File structure
```
📁 Your folder
├── LevelShoes_Sitelinks_Generator.html  ← Open this in browser
├── server.py                            ← Run this in terminal
├── .env                                 ← Your API key goes here
├── requirements.txt                     ← Python dependencies
└── README.md                            ← This file
```

## Security
- Your API key is ONLY in `.env` on your computer
- It is never sent to the browser or exposed anywhere
- Never commit `.env` to Git or share it
