# 紫微天機命譜系統 - 伺服器部署指南

本指南說明如何將「紫微天機命譜系統」部署至 Linux/Windows 伺服器（代理伺服器環境）。

## 1. 準備工作

### 核心檔案清單
請確保將以下檔案上傳至您的伺服器目錄（例如 `/opt/fate_purple/`）：

- **主程式**: `server_headless.py` (已為您建立的無介面版本)
- **網頁前端**: `fate.html`, `intro.html`
- **靜態資源**: `icon.png`, `logo_v2.png`, `ziwei_rules.json`, `ziwei_constants.json`, `config.json`
- **邏輯模組**: `master_book.py`, `rule_engine.py`, `lunar_python` (若有修改源碼)
- **資料檔案**: `user_records.json`, `chat_history.json` (若無則會自動產生)

## 2. 環境安裝 (Server Environment)

確保伺服器已安裝 Python 3.10+。

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 Python 與 pip
sudo apt install python3 python3-pip -y

# 安裝專案依賴
pip3 install flask flask-cors requests lunar-python
```

### 安裝 Ollama (AI 模型核心)
本系統依賴 Ollama 進行 AI 推論。請在伺服器上安裝 Ollama：

```bash
# Linux 安裝 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 啟動 Ollama 服務
sudo systemctl start ollama

# 下載模型 (這裡使用 gemma2:2b，可依配置調整)
ollama pull gemma2:2b
```

## 3. 啟動伺服器

### 測試運行
使用 Python 直接執行，確認無誤：

```bash
python3 server_headless.py
```
*看到 `Starting Headless FatePurple Server on port 5000...` 即表示成功。*

### 正式運行 (使用 Gunicorn)
建議在生產環境使用 Gunicorn (Linux 適用)：

```bash
# 安裝 Gunicorn
pip3 install gunicorn

# 背景執行 (4 workder process, 綁定 5000 port)
gunicorn -w 4 -b 0.0.0.0:5000 server_headless:app --daemon
```

## 4. 設定 Nginx 反向代理 (Reverse Proxy)

若您希望透過正規網域 (如 `fate.example.com`) 訪問，請設定 Nginx。

1. 安裝 Nginx: `sudo apt install nginx`
2. 編輯設定檔: `sudo nano /etc/nginx/sites-available/fate_purple`

```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

3. 啟用並重啟 Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/fate_purple /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 5. 常見問題

- **Ollama 連線失敗**: 請確認 `config.json` 中的 `ollama_url` 指向正確位置。若 Ollama 與 Flask 在同一台機器，通常是 `http://localhost:11434`。
- **防火牆問題**: 若無法從外部連線，請確認伺服器防火牆 (UFW/AWS Security Group) 已開放 5000 或 80 port。
