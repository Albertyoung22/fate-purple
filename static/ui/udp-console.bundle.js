
// All UI is encapsulated in a Web Component to avoid leaking styles to other pages.
class UDPConsole extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.state = {
      volume: 80, rate: "-20%", lang: "zh-TW", gender: "female",
      muted: false, playing: "idle", progress: 0, ngrok_url: null,
      timetable: { enabled: true, count: 0 }, relay: {}, auto_unmute_on_play: true
    };
  }

  connectedCallback() {
    this.render();
    this.bind();
    this.refreshState();
    this.timer = setInterval(()=>this.refreshState(), 2000);
  }

  disconnectedCallback() {
    if (this.timer) clearInterval(this.timer);
  }

  css() {
    return /*css*/`
      :host { display:block; }
      * { box-sizing: border-box; }
      .app { --card-bg:#ffffff; --card-br:#e7f0fb; --accent:#1e7bd8; --text:#0b2239; }
      .status {
        display:flex; flex-wrap:wrap; gap:10px; align-items:center; justify-content:space-between;
        background: #eaf3ff; border:1px solid #cfe5ff; border-radius:14px; padding:10px 12px; margin-bottom:12px;
      }
      .status .left { display:flex; align-items:center; flex-wrap:wrap; gap:10px; }
      .badge { padding:4px 8px; background:#fff; border:1px solid #d8e7fb; border-radius:12px; font-size:12px; color:#1f3b57; }
      .progress-wrap { display:flex; align-items:center; gap:8px; min-width:260px; }
      progress { width: 220px; height: 14px; }
      .grid {
        display:grid; gap:12px;
        grid-template-columns: 1fr 1fr;
      }
      @media (max-width: 900px) {
        .grid { grid-template-columns: 1fr; }
      }
      .card {
        background: var(--card-bg); border:1px solid var(--card-br); border-radius:16px; padding:14px;
        box-shadow: 0 1px 0 rgba(16,24,40,0.03);
      }
      .card h3 { margin:0 0 12px; font-size:16px; color:var(--text); display:flex; align-items:center; gap:8px; }
      .row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin: 8px 0; }
      .row > * { flex: 0 1 auto; }
      .row.stretch > * { flex: 1 1 auto; }
      label.small { font-size:12px; color:#445b78; }
      input[type="text"], textarea, select {
        width:100%; font-size:14px; padding:8px 10px; border:1px solid #d6e3f7; border-radius:10px; background:#fff;
      }
      textarea { min-height: 96px; resize: vertical; }
      button {
        appearance:none; border:1px solid #cfe1fb; background:#f6faff; color:#0a2b5a; padding:8px 10px; border-radius:10px;
        font-size:14px; cursor:pointer;
      }
      button.primary { background:#1e7bd8; border-color:#1e7bd8; color:#fff; }
      button.warn { background:#ffe9e9; border-color:#ffd0d0; color:#8b1a1a; }
      button.ghost { background:#fff; }
      .btns { display:flex; flex-wrap:wrap; gap:8px; }
      .two-col { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
      @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
      .hint { color:#5c738f; font-size:12px; }
      .tight * { font-size: 12px; }
      .select-inline { display:flex; gap:6px; align-items:center; }
      .file-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
      .file-row .grow { flex: 1 1 260px; }
      .right-col .card { min-height: 0; }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    `;
  }

  html() {
    const s = this.state;
    return /*html*/`
      <div class="app">
        <div class="status">
          <div class="left">
            <span class="badge">狀態：${this.escape(s.playing || "—")}</span>
            <div class="progress-wrap">
              <progress value="${Number(s.progress||0)}" max="100"></progress>
              <span class="mono">${Number(s.progress||0)}%</span>
            </div>
            <span class="badge">音量：${Number(s.volume||0)}%</span>
            <span class="badge">語速：${this.escape(s.rate||"-")}</span>
            <span class="badge">語言：${this.escape(s.lang||"-")}</span>
            <span class="badge">聲別：${this.escape(s.gender||"-")}</span>
            ${s.muted ? '<span class="badge" style="background:#ffecec;border-color:#ffcece;color:#8b1a1a">靜音</span>' : ""}
          </div>
          <div class="right tight">
            <span class="hint">ngrok：</span>
            <span class="mono">${s.ngrok_url ? this.escape(s.ngrok_url) : '（未啟動）'}</span>
          </div>
        </div>

        <div class="grid">
          <!-- Left Column -->
          <div class="left-col">
            <div class="card">
              <h3>📝 傳送文字訊息</h3>
              <div class="row">
                <textarea id="msg" placeholder="要播報／顯示的內容…"></textarea>
              </div>
              <div class="btns">
                <button id="btn-say" class="primary">🔊 直接播報</button>
                <button id="btn-show" class="">📢 全螢幕顯示（有聲）</button>
                <button id="btn-show-silent" class="ghost">🖥️ 全螢幕顯示（無聲）</button>
              </div>

              <div class="card" style="margin-top:12px;">
                <h3>🌐 翻譯助手</h3>
                <div class="two-col">
                  <div>
                    <div class="row">
                      <label class="small">來源語言</label>
                      <select id="srcLang">
                        <option value="auto">自動偵測</option>
                        <option value="zh">中文</option>
                        <option value="en">英文</option>
                        <option value="ja">日文</option>
                        <option value="ko">韓文</option>
                        <option value="vi">越南語</option>
                        <option value="id">印尼語</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <div class="row">
                      <label class="small">目標語言</label>
                      <select id="tgtLang">
                        <option value="zh">中文</option>
                        <option value="en">英文</option>
                        <option value="ja">日文</option>
                        <option value="ko">韓文</option>
                        <option value="vi">越南語</option>
                        <option value="id">印尼語</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div class="btns" style="margin:8px 0 6px">
                  <button id="btn-translate">↔️ 翻譯</button>
                  <span class="hint">優先使用 LibreTranslate；若失敗會開啟 Google 翻譯。</span>
                </div>
                <div class="row">
                  <textarea id="translated" placeholder="翻譯結果…" rows="4"></textarea>
                </div>
                <div class="btns">
                  <button id="btn-apply" class="">⬆️ 套用翻譯 → 上方欄位</button>
                </div>
              </div>
            </div>

            <div class="card" style="margin-top:12px;">
              <h3>🎵 MP3 / YouTube</h3>
              <div class="two-col">
                <div>
                  <div class="row">
                    <input id="mp3url" type="text" placeholder="貼上 MP3 或 YouTube 連結…" />
                  </div>
                  <div class="btns">
                    <button id="btn-mp3url" class="primary">▶️ 播放音訊</button>
                    <button id="btn-ytfs">🎬 全螢幕播放（YouTube）</button>
                    <button id="btn-ytclose" class="ghost">⏹ 關閉全螢幕</button>
                  </div>
                </div>
                <div>
                  <div class="file-row">
                    <input id="file" type="file" accept=".mp3" />
                    <button id="btn-upload">⬆️ 上傳 MP3</button>
                  </div>
                  <div class="row stretch" style="margin-top:8px;">
                    <select id="fileList"></select>
                    <select id="fileAction">
                      <option value="play">播放</option>
                      <option value="download">下載</option>
                      <option value="delete">刪除</option>
                    </select>
                    <button id="btn-file-go">執行</button>
                  </div>
                  <div class="btns" style="margin-top:8px;">
                    <button id="btn-mp3pause">⏸ 暫停</button>
                    <button id="btn-mp3resume">▶️ 繼續</button>
                    <button id="btn-mp3stop" class="ghost">⏹ 停止</button>
                  </div>
                </div>
              </div>
            </div>

            <div class="card" style="margin-top:12px;">
              <h3>⚡ 快速指令</h3>
              <div class="btns">
                <button data-cmd="Bell:ClassStart">🔔 上課鈴</button>
                <button data-cmd="Bell:ClassEnd">🔔 下課鈴</button>
                <button data-cmd="Bell:EarthquakeAlarm">🚨 地震警報</button>
                <button data-cmd="CancelALL" class="warn">⏹ 強制取消</button>
              </div>
            </div>
          </div>

          <!-- Right Column -->
          <div class="right-col">
            <div class="card">
              <h3>🗣️ 語音設定</h3>
              <div class="row">
                <div class="select-inline">
                  <label class="small">語言</label>
                  <select id="lang">
                    <option value="zh-TW">中文（台灣）</option>
                    <option value="en-US">英文（美國）</option>
                    <option value="ja-JP">日文（日本）</option>
                    <option value="ko-KR">韓文（韓國）</option>
                    <option value="vi-VN">越南語</option>
                    <option value="id-ID">印尼語</option>
                    <option value="nan-TW">台語</option>
                  </select>
                  <button id="btn-lang">套用</button>
                </div>
              </div>
              <div class="row">
                <div class="select-inline">
                  <label class="small">聲別</label>
                  <select id="gender">
                    <option value="female">女聲</option>
                    <option value="male">男聲</option>
                  </select>
                  <button id="btn-gender">套用</button>
                </div>
              </div>
              <div class="row">
                <label class="small" for="rate">語速（-50%..0%）</label>
                <input id="rate" type="range" min="-50" max="0" step="5" value="-20" />
                <span id="rateVal" class="mono">-20%</span>
              </div>
              <div class="row">
                <label class="small">播放前自動解除靜音</label>
                <input id="autoUnmute" type="checkbox" />
              </div>
            </div>

            <div class="card" style="margin-top:12px;">
              <h3>🔊 音量 / 靜音</h3>
              <div class="row">
                <input id="volume" type="range" min="0" max="100" value="80" />
                <span id="volVal" class="mono">80%</span>
              </div>
              <div class="btns">
                <button id="btn-volup">＋5</button>
                <button id="btn-voldown">－5</button>
                <button id="btn-mute">🔇 靜音</button>
                <button id="btn-unmute" class="ghost">🔊 解除靜音</button>
              </div>
            </div>

            <div class="card" style="margin-top:12px;">
              <h3>ℹ️ 系統資訊</h3>
              <div class="row tight"><span class="hint">課表：</span> <span id="ttInfo" class="mono">—</span></div>
              <div class="row tight"><span class="hint">Relay：</span> <span id="relayInfo" class="mono">—</span></div>
              <div class="row">
                <a class="hint" href="sched.html">📚 開啟課表（進階）</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>${this.css()}</style>
      ${this.html()}
    `;
  }

  bind() {
    const $ = (sel) => this.shadowRoot.querySelector(sel);
    // Text actions
    $("#btn-say").addEventListener("click", ()=> this.postForm("/send", { msg: $("#msg").value.trim() }));
    $("#btn-show").addEventListener("click", ()=> this.postForm("/special", { msg: "ShowMsg: " + $("#msg").value.trim() }));
    $("#btn-show-silent").addEventListener("click", ()=> this.postForm("/special", { msg: "SilentMsg: " + $("#msg").value.trim() }));

    // Translate
    $("#btn-translate").addEventListener("click", ()=> this.translate());
    $("#btn-apply").addEventListener("click", ()=> { $("#msg").value = $("#translated").value; });

    // MP3 / YT
    $("#btn-mp3url").addEventListener("click", ()=> {
      const url = $("#mp3url").value.trim();
      if (!url) return;
      this.postForm("/sendmp3", { mp3url: url });
    });
    $("#btn-ytfs").addEventListener("click", ()=> {
      const url = $("#mp3url").value.trim();
      if (!url) return;
      this.postForm("/cmd", { cmd: "YTFull:" + url });
    });
    $("#btn-ytclose").addEventListener("click", ()=> this.postForm("/cmd", { cmd: "YTClose" }));

    $("#btn-upload").addEventListener("click", ()=> this.upload());
    $("#btn-file-go").addEventListener("click", ()=> this.fileAction());

    $("#btn-mp3pause").addEventListener("click", ()=> this.postForm("/cmd", { cmd:"MP3Pause" }));
    $("#btn-mp3resume").addEventListener("click", ()=> this.postForm("/cmd", { cmd:"MP3Resume" }));
    $("#btn-mp3stop").addEventListener("click", ()=> this.postForm("/cmd", { cmd:"MP3Stop" }));

    // Quick commands
    this.shadowRoot.querySelectorAll('[data-cmd]').forEach(btn=>{
      btn.addEventListener("click", ()=> this.postForm("/cmd", { cmd: btn.getAttribute("data-cmd") }));
    });

    // Voice
    $("#btn-lang").addEventListener("click", ()=> this.postForm("/setlang", { lang: $("#lang").value }));
    $("#btn-gender").addEventListener("click", ()=> {
      const g = $("#gender").value === "male" ? "Boy" : "Girl";
      this.postForm("/cmd", { cmd: g });
    });
    $("#rate").addEventListener("input", (e)=> {
      const val = Number(e.target.value);
      $("#rateVal").textContent = val + "%";
    });
    $("#rate").addEventListener("change", (e)=> {
      const val = Number(e.target.value);
      this.postForm("/setrate", { rate: val + "%" });
    });
    $("#autoUnmute").addEventListener("change", (e)=> {
      this.postForm("/autounmute", { on: e.target.checked ? "1":"0" });
    });

    // Volume / mute
    $("#volume").addEventListener("input", (e)=> $("#volVal").textContent = `${Number(e.target.value)}%`);
    $("#volume").addEventListener("change", (e)=> this.postForm("/setvol", { vol: String(Number(e.target.value)) }));
    $("#btn-volup").addEventListener("click", ()=> this.postForm("/volup", {}));
    $("#btn-voldown").addEventListener("click", ()=> this.postForm("/voldown", {}));
    $("#btn-mute").addEventListener("click", ()=> this.postForm("/cmd", { cmd:"Mute" }));
    $("#btn-unmute").addEventListener("click", ()=> this.postForm("/cmd", { cmd:"Unmute" }));

    // Populate file list
    this.refreshFiles();
  }

  async refreshState() {
    try {
      const r = await fetch("/state"); const s = await r.json();
      // Merge state defensively
      const next = Object.assign({}, this.state, s || {});
      this.state = next;
      // Update some UI bits without full re-render
      const $ = (sel)=> this.shadowRoot.querySelector(sel);
      if ($("#rateVal") && s.rate) $("#rateVal").textContent = s.rate;
      if ($("#rate") && s.rate) $("#rate").value = parseInt(String(s.rate).replace("%",""), 10);
      if ($("#lang") && s.lang) $("#lang").value = s.lang;
      if ($("#gender") && s.gender) $("#gender").value = s.gender === "male" ? "male" : "female";
      if ($("#volume") && (typeof s.volume === "number")) {
        $("#volume").value = s.volume; $("#volVal").textContent = `${s.volume}%`;
      }
      if ($("#autoUnmute")) $("#autoUnmute").checked = !!s.auto_unmute_on_play;
      // Update status area
      // Cheap way: re-render the header only (avoid flicker elsewhere)
      const header = this.shadowRoot.querySelector(".status");
      if (header) {
        header.outerHTML = this.html().match(/<div class="status">[\s\S]*?<\/div>/)[0];
      }
      // TT & relay small labels
      if (s.timetable && this.shadowRoot.getElementById("ttInfo")) {
        const inf = s.timetable;
        this.shadowRoot.getElementById("ttInfo").textContent = `啟用=${inf.enabled ? "是":"否"}，筆數=${inf.count}`;
      }
      if (s.relay && this.shadowRoot.getElementById("relayInfo")) {
        const rly = s.relay;
        this.shadowRoot.getElementById("relayInfo").textContent =
          `port=${rly.port || "-"}, last=${rly.last_cmd || "-"}:${rly.last_result || "-"}`;
      }
    } catch (e) {
      // ignore
    }
  }

  async refreshFiles() {
    const sel = this.shadowRoot.querySelector("#fileList");
    try {
      const r = await fetch("/files"); const j = await r.json();
      sel.innerHTML = "";
      if (!j || !j.ok || !Array.isArray(j.files)) {
        const op = document.createElement("option"); op.textContent = "（無檔案）"; op.value = ""; sel.appendChild(op); return;
        }
      j.files.forEach(f=>{
        const op = document.createElement("option");
        op.value = f.name; op.textContent = `${f.name}  (${(f.size/1024).toFixed(0)} KB)`;
        sel.appendChild(op);
      });
      if (!sel.value && sel.options.length) sel.selectedIndex = 0;
    } catch (e) {
      const op = document.createElement("option"); op.textContent = "（清單失敗）"; op.value = ""; sel.appendChild(op);
    }
  }

  async upload() {
    const file = this.shadowRoot.querySelector("#file").files[0];
    if (!file) return alert("請先選取 .mp3 檔案");
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await fetch("/upload", { method:"POST", body: fd });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "upload fail");
      await this.refreshFiles();
      alert("上傳完成：" + (j.filename || file.name));
    } catch (e) {
      alert("上傳失敗：" + e.message);
    }
  }

  async fileAction() {
    const name = this.shadowRoot.querySelector("#fileList").value;
    const act = this.shadowRoot.querySelector("#fileAction").value;
    if (!name) return;
    if (act === "play") {
      await this.postForm("/cmd", { cmd: "PlayMP3:" + name });
    } else if (act === "download") {
      // open direct
      const base = name.split("/").pop();
      window.open("/download/" + encodeURIComponent(base), "_blank");
    } else if (act === "delete") {
      if (!confirm("確定要刪除？\n" + name)) return;
      const fd = new URLSearchParams(); fd.append("name", name.split("/").pop());
      await fetch("/delete", { method:"POST", headers: {"Content-Type":"application/x-www-form-urlencoded"}, body: fd });
      await this.refreshFiles();
    }
  }

  async translate() {
  const srcSel = this.shadowRoot.querySelector("#srcLang").value;  // auto | zh | en | ...
  const tgtSel = this.shadowRoot.querySelector("#tgtLang").value;  // zh | en | ...
  const text = this.shadowRoot.querySelector("#msg").value.trim();
  const outBox = this.shadowRoot.querySelector("#translated");
  if (!text) return;

  // 同語言保險：src 不是 auto 且與 tgt 同族，就直接回原文，不要丟到上游也不要 alert
  const base = s => String(s || "").split("-")[0].toLowerCase(); // zh-TW -> zh
  if (srcSel && srcSel !== "auto" && base(srcSel) === base(tgtSel)) {
    outBox.value = text;   // no-op：套用原文即可
    return;
  }

  try {
    // ✅ 使用你自己的後端 /translate（有備援與 CORS 設定）
    const r = await fetch("/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        q: text,
        source: srcSel || "auto",   // 後端支援 auto
        target: tgtSel,
        format: "text"
      })
    });
    const j = await r.json();

    // 後端成功
    if (j && (j.translatedText || j.text)) {
      outBox.value = j.translatedText || j.text;
      return;
    }

    // 某些情況後端可能告知「同語言不翻」；做個保底
    if (j && j.ok === true && j.via === "noop_same_lang") {
      outBox.value = text;
      return;
    }

    // 其他錯誤 → 開 Google 翻譯備援
    throw new Error(j && j.error ? j.error : "translate failed");
  } catch (e) {
    const url = "https://translate.google.com/?sl=auto&tl="
      + encodeURIComponent(tgtSel)
      + "&text=" + encodeURIComponent(text)
      + "&op=translate";
    window.open(url, "_blank");
  }
}


  async postForm(path, kv) {
    const body = new URLSearchParams();
    Object.entries(kv).forEach(([k,v])=> body.append(k, String(v)));
    try {
      await fetch(path, { method:"POST", headers: { "Content-Type":"application/x-www-form-urlencoded" }, body });
      // minor optimistic refresh
      setTimeout(()=>this.refreshState(), 400);
    } catch (e) {
      alert("請求失敗：" + e.message);
    }
  }

  // utils
  escape(s) { return String(s).replace(/[&<>"']/g, m=>({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[m])); }
}

customElements.define("udp-console", UDPConsole);
