# Fate Purple - 紫微天機命譜系統

這是基於 Python (Flask) 與 Ollama/Gemini API 的紫微斗數命理系統。

## 功能
- 紫微斗數排盤
- 八字論命
- AI 詳批 (支援 Gemini 與 Ollama)
- 前端視覺化介面 (React)

## 部署至雲端 (免費方案)
本專案支援部署於 **Render.com** (後端) 與 **GitHub Pages** (前端)。

1. **後端 (API)**:
   - 請將此儲存庫部署至 Render Web Service。
   - 環境變數 `GEMINI_API_KEY` 需設定為您的 Google API Key。
   - 啟動指令: `gunicorn server_headless:app`

2. **前端 (網頁)**:
   - 修改 `fate.html` 中的 `BACKEND_URL` 指向 Render 網址。
   - 使用 GitHub Pages 部署 `fate.html`。

詳細步驟請參閱 `FREE_HOSTING_GUIDE.md`。

## 本地開發
1. 安裝依賴: `pip install -r requirements.txt`
2. 啟動伺服器: `python server_headless.py`
3. 開啟網頁: 瀏覽器打開 `fate.html`
