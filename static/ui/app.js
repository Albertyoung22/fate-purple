const $ = (s, r=document)=>r.querySelector(s);
const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
const toastEl = document.getElementById('toast');

function toast(msg='已送出'){
  if(!toastEl) return;
  toastEl.textContent = msg;
  toastEl.style.display = 'block';
  setTimeout(()=>toastEl.style.display='none', 1400);
}
function getToken(){ return localStorage.getItem('X_TOKEN') || ''; }
function setToken(tok){ localStorage.setItem('X_TOKEN', tok||''); }

async function http(path, {method='GET', json=null, form=null}={}){
  const opt = { method, headers: {} };
  const tok = getToken();
  if (tok) opt.headers['X-Token'] = tok;
  if (json){ opt.headers['Content-Type']='application/json'; opt.body = JSON.stringify(json); }
  if (form){ opt.headers['Content-Type']='application/x-www-form-urlencoded'; opt.body = new URLSearchParams(form).toString(); }
  const r = await fetch(path, opt);
  if (!r.ok && r.status !== 204){
    const t = await r.text().catch(()=>'');
    throw new Error(t || ('HTTP '+r.status));
  }
  try{ return await r.json(); }catch{ return null; }
}

function bindHeader(active){
  const tokenInput = $('#tokenInput');
  const saveToken = $('#saveToken');
  const viewMode = $('#viewMode');
  if (tokenInput){ tokenInput.value = getToken(); }
  if (saveToken){ saveToken.onclick = ()=>{ setToken(tokenInput.value.trim()); toast('已儲存 Token'); }; }
  if (viewMode){
    const s = localStorage.getItem('VIEW') || 'auto';
    viewMode.value = s;
    viewMode.onchange = ()=>{ localStorage.setItem('VIEW', viewMode.value); location.reload(); };
    document.documentElement.classList.toggle('mobile', (s==='mobile'));
    document.documentElement.classList.toggle('desktop', (s==='desktop'));
  }
  $$('.nav a').forEach(a=>a.classList.toggle('active', a.dataset.active===active));
}

async function refreshState(){
  try{
    const s = await http('/state');
    if (!s) return;
    $('#srvMode')?.replaceChildren(document.createTextNode('OK'));
    $('#srvTime')?.replaceChildren(document.createTextNode(new Date().toLocaleTimeString()));
    $('#stPlaying')?.replaceChildren(document.createTextNode(s.playing));
    $('#stProgress')?.replaceChildren(document.createTextNode(s.progress));
    $('#stMuted')?.replaceChildren(document.createTextNode(String(s.muted)));
    $('#stVox')?.replaceChildren(document.createTextNode(`${s.lang}/${s.gender}/${s.rate}`));
    $('#stRPort')?.replaceChildren(document.createTextNode(s.relay?.port||'-'));
    $('#stRCmd')?.replaceChildren(document.createTextNode(s.relay?.last_cmd||'-'));
    $('#stRRes')?.replaceChildren(document.createTextNode(s.relay?.last_result||'-'));
    $('#stRErr')?.replaceChildren(document.createTextNode(s.relay?.last_error||''));
    $('#stNgrok')?.replaceChildren(document.createTextNode(s.ngrok_url||'-'));
    $('#stMpv')?.replaceChildren(document.createTextNode(s.mpv_ipc_path||'-'));
    $('#stTT')?.replaceChildren(document.createTextNode(`${s.timetable?.enabled?'On':'Off'} / ${s.timetable?.count||0}`));
  }catch(e){ console.warn(e); }
}
function every(ms, fn){ fn(); return setInterval(fn, ms); }
async function reloadFileList(selectEl){
  const data = await http('/files');
  if(!data?.ok) return;
  selectEl.innerHTML = '';
  data.files.forEach(f=>{
    const o = document.createElement('option');
    o.value = f.name;
    o.textContent = `${f.name} (${(f.size/1024).toFixed(0)} KB)`;
    selectEl.appendChild(o);
  });
}

async function loadTimetableUI(){
  const t = await http('/timetable');
  if(!t?.ok) return;
  $('#ttStatus')?.replaceChildren(document.createTextNode(t.enabled?'啟用':'停用'));
  $('#ttCount')?.replaceChildren(document.createTextNode(`共 ${t.count} 筆`));
  $('#ttPath')?.replaceChildren(document.createTextNode(t.data?.path||''));
  if($('#ttSkipHoliday')) $('#ttSkipHoliday').checked = !!t.data?.skip_holidays;
  if($('#ttSatSchool')) $('#ttSatSchool').checked = !!t.data?.treat_saturday_as_school;
  if($('#ttHolidays')) $('#ttHolidays').value = (t.data?.holidays||[]).join('\n');
  if($('#ttJson')) $('#ttJson').value = JSON.stringify(t.data || {}, null, 2);
  const tbody = $('#ttTable tbody'); if(!tbody) return;
  tbody.innerHTML = '';
  (t.data?.items||[]).forEach((it, i)=>{
    const tr = document.createElement('tr');
    const wd = it.date ? it.date : `週${it.dow}`;
    tr.innerHTML = `<td>${i}</td><td>${it.time||''}</td><td>${wd}</td><td>${it.label||''}</td><td><code>${it.action||''}</code></td>
    <td><button class="btn" data-idx="${i}">試播</button></td>`;
    tbody.appendChild(tr);
  });
  tbody.addEventListener('click', async e=>{
    const btn = e.target.closest('button[data-idx]'); if(!btn) return;
    const i = btn.dataset.idx;
    try{ await http('/timetable/play?i='+i, {method:'POST'}); toast('已試播'); }catch(e){ alert('失敗: '+e.message); }
  }, {once:true});
}

export { $, $$, toast, http, bindHeader, refreshState, every, reloadFileList, loadTimetableUI };
