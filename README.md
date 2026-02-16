# 紫微八字 · 天機命譜 V20.0

![Logo](logo_v2.png)

## 🌟 專案簡介 (Introduction)
這是一個結合傳統東方命理（紫微斗數、子平八字）與現代 AI 技術（Google Gemini 2.0, Groq Llama 3, Ollama）的智慧命理系統。旨在透過大數據分析與深度學習模型，為用戶提供精準、有溫度的命盤解析與人生建議。

## 🚀 核心功能 (Features)
-   **雙盤合參**：同時排布《紫微斗數》與《子平八字》命盤，交叉驗證格局高低。
-   **混合 AI 引擎 (Hybrid-Engine)**：
    *   **本地運算**：支援 Ollama (Gemma 2:2b) 進行隱私優先的離線分析。
    *   **雲端極速**：自動切換至 Groq (Llama 3 8B) 實現毫秒級回應。
    *   **深度備援**：整合 Google Gemini 2.0 Flash 作為最強大的分析後盾。
-   **智能詳評**：自動生成結構化的命理報告（星曜坐守、飛星四化、終極總結）。
-   **生活化應用**：提供「今日錦囊」、「前世因果」、「轉運儀式」、「夢境解析」等多樣化功能。
-   **精美 UI**：現代化響應式介面，支援行動裝置與列印模式。

## 🛠️ 安裝與執行 (Installation)

### 1. 環境需求
-   Python 3.10+
-   Node.js (非必須，僅開發前端用)

### 2. 安裝依賴
```bash
pip install -r requirements.txt
```

### 3. 設定 API 金鑰
本專案支援多種 AI 服務，請依照需求設定：
1.  複製範本檔：
    ```bash
    cp config.example.json config.json
    ```
2.  編輯 `config.json`，填入您的 API Key：
    *   **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)
    *   **Groq API Key**: [Groq Console](https://console.groq.com/)

### 4. 啟動服務
```bash
python backend_ollama02016.py
```
啟動後請訪問：`http://localhost:5000`

## 📂 專案結構
-   `backend_ollama02016.py`: 核心後端伺服器 (Flask)。
-   `fate.html`: 前端單頁應用 (React/Tailwind)。
-   `ziwei_rules.json`: 紫微斗數全書規則庫。
-   `master_book.py`: AI 人設與系統提示詞 (System Prompt)。

## ⚠️ 注意事項
-   本專案僅供學術研究與趣味參考，命運掌握在自己手中。
-   **請勿將含有 API Key 的 `config.json` 直接上傳至公開儲存庫。**

## 📄 授權 (License)
MIT License
