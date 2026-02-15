# 如何使用免費伺服器架設本系統 (Render + GitHub Pages)

若您不想花錢租用 VPS，可以使用現代化的 **雲端平台 (Cloud Platform)** 進行免費部署。

## ⚠️ 重要限制說明
1. **Ollama 無法在免費伺服器運行**：
   - 免費伺服器通常只有 512MB RAM，跑不動 Ollama AI 模型。
   - **解決方案**：必須使用 **Google Gemini API** (雲端 AI)。請至 [Google AI Studio](https://aistudio.google.com/) 申請免費 API Key。

## 架構總覽
- **後端 (Python)**: 使用 **Render** (免費 Web Service)。
- **前端 (HTML)**: 使用 **GitHub Pages** (免費靜態網頁託管)。
- **AI 核心**: 使用 **Google Gemini API** (免費額度足夠個人使用)。

---

## 第一步：準備 GitHub 儲存庫 (Repo)

1. 在 GitHub 上建立一個新的儲存庫 (Repository)，例如 `fate-purple-backend`。
2. 將以下檔案上傳到該儲存庫 (或使用 Git Push)：
   - `server_headless.py`
   - `requirements.txt`
   - `Procfile`
   - `master_book.py`
   - `rule_engine.py`
   - `ziwei_rules.json` (及其他 json 檔案)
   - `lunar_python` (若為自行修改版，否則 requirements.txt 會自動安裝)

## 第二步：部署後端 (Render)

1. 註冊 [Render.com](https://render.com/) 帳號。
2. 點擊 **New +** -> **Web Service**。
3. 連接您的 GitHub 帳號並選擇剛建立的 `fate-purple-backend`。
4. 設定參數：
   - **Name**: `fate-purple-api` (自取)
   - **Region**: `Singapore` (新加坡，連線台灣較快)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn server_headless:app` (系統應會自動偵測到 Procfile)
   - **Instance Type**: `Free`
5. **設定環境變數 (Environment Variables)**：
   -點擊 Advanced -> Add Environment Variable
   - Key: `GEMINI_API_KEY`
   - Value: `您的_Google_Gemini_API_Key` (請務必填寫，否則無法算命)
6. 點擊 **Create Web Service**。
7. 等待部署完成，您會獲得一個網址，例如：`https://fate-purple-api.onrender.com`。
   - **請複製這個網址**，這是您的後端 API 地址。

## 第三步：修改前端 (fate.html)

因前端與後端現在位於不同網域，需修改 `fate.html` 中的 API 連線地址。

1. 打開 `fate.html`。
2. 搜尋 `const apiUrl =`。
3. 將原本的判斷邏輯修改為您的 Render 網址：

```javascript
// 原本的代碼：
// const isLocal = window.location.protocol === 'file:';
// const apiUrl = isLocal ? 'http://localhost:5000/api/chat' : '/api/chat';

// ★★★ 修改為： ★★★
const BACKEND_URL = "https://fate-purple-api.onrender.com"; // 您的 Render 網址
const apiUrl = `${BACKEND_URL}/api/chat`;
```
*(同理，`save_record` 的 API 也要改)*

```javascript
// const apiUrl = isLocal ? 'http://localhost:5000/api/save_record' : '/api/save_record';
// ★★★ 修改為： ★★★
const RECORD_API_URL = `${BACKEND_URL}/api/save_record`;
```

## 第四步：部署前端 (GitHub Pages)

1. 在 GitHub 建立另一個儲存庫 (或同一個的 `/docs` 資料夾)，上傳修改後的 `fate.html` 及圖片 (`icon.png`, `logo_v2.png`)。
2. 進入 Repo 的 **Settings** -> **Pages**。
3. Source 選擇 `main` branch (或上傳的資料夾)。
4. 儲存後，GitHub 會生成一個網址，例如 `https://yourname.github.io/fate-purple/fate.html`。

## 完成！
現在您可以分享 GitHub Pages 的網址給朋友，他們就能在手機或電腦上使用您的紫微八字系統了！
