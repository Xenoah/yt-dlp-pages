import {DEFAULTS, parseUrls, bridgeUrl, commandLine, bytes, duration, escapeHtml as esc} from './core.mjs';

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const state = {options:{...DEFAULTS}, bridge:'http://127.0.0.1:9731', token:'', connected:false, jobs:[], filter:'all', logId:null, timer:null, toastTimer:null, epoch:0};
const labels = {queued:'待機中', running:'ダウンロード中', processing:'変換・結合中', completed:'完了', failed:'エラー', cancelled:'中止'};
const active = job => ['queued','running','processing'].includes(job.status);
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const optionFields = {quality:'quality', container:'container', audioFormat:'audio-format', subtitles:'subtitles', subLang:'sub-lang', metadata:'metadata', thumbnail:'thumbnail', playlist:'playlist', playlistLimit:'playlist-limit'};

try {state.bridge = bridgeUrl(location.origin);} catch { /* Manual connection when opened outside the local server. */ }

try {
  const stored = JSON.parse(localStorage.getItem('yt-dlp-pages-options') || '{}');
  for (const key of Object.keys(DEFAULTS)) {
    if (typeof stored[key] === typeof DEFAULTS[key]) state.options[key] = stored[key];
  }
} catch { /* Storage can be unavailable in private sessions. */ }
if (!['video','audio'].includes(state.options.mode)) state.options.mode = 'video';
state.options.playlistLimit = Math.max(1, Math.min(100, Number(state.options.playlistLimit) || 20));
for (const [key,id] of Object.entries(optionFields)) {
  const field = $(`#${id}`);
  if (field.type === 'checkbox') field.checked = state.options[key];
  else {
    field.value = state.options[key];
    if (!field.value) field.value = DEFAULTS[key];
    state.options[key] = key === 'playlistLimit' ? Number(field.value) : field.value;
  }
}

function toast(text) {
  clearTimeout(state.toastTimer);
  $('#toast').textContent = text;
  $('#toast').hidden = false;
  state.toastTimer = setTimeout(() => $('#toast').hidden = true, 4500);
}

function errorAt(selector, message='') {
  $(selector).textContent = message;
  $(selector).hidden = !message;
}

function setView(view) {
  if (!['download','command','guide'].includes(view)) return;
  $$('.view').forEach(el => el.hidden = el.id !== `view-${view}`);
  $$('.nav-item').forEach(el => {
    const selected = el.dataset.view === view;
    el.classList.toggle('active', selected);
    if (selected) el.setAttribute('aria-current','page'); else el.removeAttribute('aria-current');
  });
  $('#view-label').textContent = {download:'ダウンローダー', command:'コマンド生成', guide:'使い方ガイド'}[view];
  if (view === 'command') updateCommand();
  window.scrollTo({top:0, behavior:'instant'});
}

function settingsChanged() {
  for (const [key,id] of Object.entries(optionFields)) {
    const field = $(`#${id}`);
    state.options[key] = field.type === 'checkbox' ? field.checked : key === 'playlistLimit' ? Number(field.value) : field.value;
  }
  const o = state.options;
  $$('#download-form [data-mode]').forEach(button => {
    const selected = button.dataset.mode === o.mode;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  $$('.quality-chips button').forEach(button => {
    const selected = button.dataset.quality === o.quality;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  $('#video-options').hidden = o.mode !== 'video';
  $('#audio-options').hidden = o.mode !== 'audio';
  $('#playlist-limit').disabled = !o.playlist;
  $('#sub-lang').disabled = o.subtitles === 'none';
  $('#summary-icon use').setAttribute('href', o.mode === 'video' ? '#i-video' : '#i-music');
  $('#summary-format').textContent = o.mode === 'video' ? `${o.container.toUpperCase()} / ${o.quality === 'best' ? '最高画質' : o.quality + 'p'}` : `${o.audioFormat === 'original' ? '元の音声形式' : o.audioFormat.toUpperCase()} / 最高品質`;
  $('#summary-details').textContent = [o.mode === 'video' ? '動画 + 音声' : '音声のみ', o.metadata ? 'メタデータ付き' : '', o.playlist ? `最大${o.playlistLimit}件` : ''].filter(Boolean).join(' · ');
  try {localStorage.setItem('yt-dlp-pages-options', JSON.stringify(o));} catch { /* Optional persistence. */ }
  updateCommand();
}

function validOptions() {
  const n = state.options.playlistLimit;
  if (!Number.isInteger(n) || n < 1 || n > 100) throw new Error('プレイリストの取得上限は1〜100件で指定してください。');
  return {...state.options};
}

function updateCommand() {
  let urls;
  try { urls = parseUrls($('#urls').value); }
  catch { urls = ['https://example.com/video']; }
  $('#command-preview').textContent = commandLine(state.options, urls, $('#shell').value);
}

async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly','');
    document.body.append(area);
    area.select();
    const success = document.execCommand('copy');
    area.remove();
    if (!success) throw new Error('コピーできませんでした。コマンド画面のテキストを選択してコピーしてください。');
  }
}

async function copyCommand() {
  try {
    const text = commandLine(validOptions(), parseUrls($('#urls').value), $('#shell').value);
    await copy(text);
    toast(`${$('#shell').value === 'powershell' ? 'PowerShell' : 'Bash'}用コマンドをコピーしました`);
  } catch(error) {toast(error.message);}
}

async function api(path, body, timeout=18000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(state.bridge + path, {
      method:body === undefined ? 'GET' : 'POST',
      headers:{Authorization:`Bearer ${state.token}`, ...(body === undefined ? {} : {'Content-Type':'application/json'})},
      body:body === undefined ? undefined : JSON.stringify(body),
      signal:controller.signal, credentials:'omit', cache:'no-store', referrerPolicy:'no-referrer',
    });
    let data;
    try { data = await response.json(); } catch { throw new Error('接続先がyt-dlp Localではないようです。起動ウィンドウのアドレスを確認してください。'); }
    if (!response.ok) throw new Error(data.error || `接続エラー (${response.status})`);
    return data;
  } catch(error) {
    if (error.name === 'AbortError') throw new Error('応答がありません。起動ウィンドウが開いているか確認し、もう一度接続してください。');
    if (error instanceof TypeError) throw new Error('接続できません。起動ファイルを実行し、ウィンドウに表示された Open のURLを開いてください。');
    throw error;
  } finally {clearTimeout(timer);}
}

function openConnection() {
  $('#bridge-address').value = state.bridge;
  if (!$('#connect-dialog').open) $('#connect-dialog').showModal();
}

async function connect(event) {
  event?.preventDefault();
  errorAt('#connect-error');
  $('#connect-submit').disabled = true;
  clearTimeout(state.timer);
  state.epoch += 1;
  state.connected = false;
  try {
    state.bridge = bridgeUrl($('#bridge-address').value);
    state.token = $('#bridge-token').value.trim();
    if (!state.token) throw new Error('起動ウィンドウに表示された接続キーを入力してください。');
    const health = await api('/api/health');
    if (!health.version || !('engine' in health)) throw new Error('ブリッジの応答形式が正しくありません。');
    if (!health.engine) throw new Error('yt-dlpが見つかりません。起動セットの手順でインストールしてから再接続してください。');
    state.connected = true;
    state.jobs = [];
    document.body.classList.add('connected');
    $('#side-status').textContent = `yt-dlp ${health.engine}`;
    $('#connection-label').textContent = '接続済み';
    $('#connection-banner').classList.add('connected');
    $('#connection-banner b').textContent = 'このPCに接続しています';
    $('#connection-banner p').textContent = health.ffmpeg && health.runtime ? `保存先：${health.output}` : `未導入：${[!health.ffmpeg && 'FFmpeg', !health.runtime && 'Deno / Node.js'].filter(Boolean).join('、')}。使い方ガイドから導入してください。`;
    $('#connection-banner button').innerHTML = `接続設定 ${icon('settings')}`;
    $('#capabilities').hidden = false;
    $('#capabilities').innerHTML = `<div class="caps-grid"><span class="cap">yt-dlp ${esc(health.engine)}</span><span class="cap ${health.ffmpeg ? '' : 'missing'}">FFmpeg ${health.ffmpeg ? 'OK' : '未導入'}</span><span class="cap ${health.runtime ? '' : 'missing'}">${esc(health.runtime || 'Deno / Node.js 未導入')}</span></div><div class="output-path">保存先：${esc(health.output)}</div>`;
    $('#connect-dialog').close();
    toast(health.ffmpeg ? 'このPCに接続しました' : '接続しました。動画・音声変換にはFFmpegを導入してください。');
    await poll();
  } catch(error) {
    state.connected = false;
    document.body.classList.remove('connected');
    $('#connection-label').textContent = '未接続';
    $('#side-status').textContent = 'ローカル接続待ち';
    $('#connection-banner').classList.remove('connected');
    $('#connection-banner b').textContent = '接続を確認してください';
    $('#connection-banner p').textContent = '起動ウィンドウの Open のURLを開くか、接続キーを入力してください。';
    $('#capabilities').hidden = true;
    errorAt('#connect-error', error.message);
    openConnection();
  } finally {$('#connect-submit').disabled = false;}
}

async function poll() {
  clearTimeout(state.timer);
  if (!state.connected) return;
  const epoch = state.epoch;
  try {
    const data = await api('/api/jobs', undefined, 8000);
    if (epoch !== state.epoch) return;
    if (!Array.isArray(data.jobs)) throw new Error('ジョブ一覧を取得できませんでした。');
    state.jobs = data.jobs;
    $('#connection-label').textContent = '接続済み';
    renderJobs();
  } catch {
    if (epoch === state.epoch) $('#connection-label').textContent = '応答なし · 接続確認';
  } finally {
    if (state.connected && epoch === state.epoch) state.timer = setTimeout(poll, 1800);
  }
}

function renderJobs() {
  $('#queue-count').textContent = state.jobs.length;
  $('#active-count').textContent = state.jobs.filter(active).length;
  $('#done-count').textContent = state.jobs.filter(j => j.status === 'completed').length;
  const jobs = state.jobs.filter(j => state.filter === 'all' || (state.filter === 'active' ? active(j) : j.status === 'completed'));
  if (!jobs.length) {
    $('#jobs').innerHTML = `<div class="queue-empty"><span class="empty-icon">${icon('download')}</span><b>${state.jobs.length ? '該当するダウンロードはありません。' : '準備ができたら、ダウンロード。'}</b><p>追加したメディアの進捗と保存ファイルをここに表示します。</p></div>`;
  } else {
    $('#jobs').innerHTML = [...jobs].reverse().map(job => {
      const busy = active(job);
      const status = Object.hasOwn(labels, job.status) ? job.status : 'failed';
      const percent = Math.max(0, Math.min(100, Number(job.percent) || 0));
      const format = job.options?.mode === 'audio' ? job.options.audioFormat : job.options?.container;
      return `<article class="job ${status}"><span class="job-icon">${icon(status === 'completed' ? 'check' : job.options?.mode === 'audio' ? 'music' : 'video')}</span><div><h3 title="${esc(job.title)}">${esc(job.title)}</h3><div class="job-meta"><span class="job-status">${labels[status]}</span><span>${esc(format?.toUpperCase() || '')}</span>${busy ? `<span>${percent}%</span>${job.speed ? `<span>${bytes(job.speed)}/s</span>` : ''}${Number.isFinite(job.eta) ? `<span>残り ${duration(job.eta)}</span>` : ''}` : ''}</div>${busy ? `<div class="progress"><progress max="100" value="${percent}" aria-label="${esc(job.title)} のダウンロード進捗"></progress></div>` : ''}${job.error && status === 'failed' ? `<p class="error-message">${esc(job.error)}</p>` : ''}${job.files?.length ? `<div class="file-list">${job.files.map((file,index) => `<button class="file-button" data-action="save" data-id="${esc(job.id)}" data-index="${index}">${icon('download')}<span>${esc(file.name)}</span><small>${bytes(file.size)}</small></button>`).join('')}</div>` : ''}</div><div class="job-actions"><button class="button ghost" data-action="log" data-id="${esc(job.id)}">ログ</button>${busy ? `<button class="button ghost" data-action="cancel" data-id="${esc(job.id)}">中止</button>` : ['failed','cancelled'].includes(status) ? `<button class="button ghost" data-action="retry" data-id="${esc(job.id)}">再試行</button>` : ''}</div></article>`;
    }).join('');
  }
  if ($('#log-dialog').open && state.logId) showLog(state.logId);
}

function showLog(id) {
  const job = state.jobs.find(j => j.id === id);
  if (!job) return;
  state.logId = id;
  $('#job-log').textContent = (job.logs || []).join('\n') || 'まだログはありません。';
  if (!$('#log-dialog').open) $('#log-dialog').showModal();
}

async function inspect() {
  errorAt('#form-error');
  let urls;
  try { urls = parseUrls($('#urls').value); } catch(error) {errorAt('#form-error',error.message);return;}
  if (!state.connected) {openConnection();return;}
  const requested = urls[0];
  const button = $('#inspect');
  button.disabled = true;
  button.textContent = '情報を取得中…';
  try {
    const info = await api('/api/probe', {url:requested}, 70000);
    if ($('#urls').value.trim().split(/\r?\n/)[0].trim() !== requested) return;
    $('#preview-title').textContent = info.title || 'タイトルなし';
    $('#preview-description').textContent = info.uploader || '投稿者情報なし';
    $('#preview-type').textContent = info.extractor_key || 'MEDIA INFO';
    const image = $('#preview-image');
    let thumbnail = '';
    try {const url = new URL(info.thumbnail); if (['http:', 'https:'].includes(url.protocol)) thumbnail = url.href;} catch { /* No thumbnail. */ }
    image.hidden = !thumbnail;
    $('#preview-art').hidden = !!thumbnail;
    image.onerror = () => {image.hidden = true;$('#preview-art').hidden = false;};
    if (thumbnail) image.src = thumbnail; else image.removeAttribute('src');
    $('#preview-meta').hidden = false;
    $('#preview-meta').textContent = `${duration(info.duration)} · ${info.formats || 0}形式`;
    if (window.innerWidth <= 740) toast(`${info.title || '動画情報を取得しました'} · ${duration(info.duration)}`);
    if (urls.length > 1) toast('先頭のURLの情報を取得しました');
  } catch(error) {errorAt('#form-error',error.message);}
  finally {button.disabled = false;button.innerHTML = `動画情報を取得 ${icon('arrow')}`;}
}

async function startDownload(event) {
  event.preventDefault();
  errorAt('#form-error');
  try {
    const urls = parseUrls($('#urls').value);
    const options = validOptions();
    if (!state.connected) {openConnection();return;}
    $('#download').disabled = true;
    const result = await api('/api/jobs', {urls,options});
    toast(`${result.ids.length}件をキューに追加しました`);
    state.filter = 'all';
    $$('.queue-tabs button').forEach(b => b.classList.toggle('active', b.dataset.filter === 'all'));
    await poll();
  } catch(error) {errorAt('#form-error',error.message);}
  finally {$('#download').disabled = false;}
}

async function jobAction(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const job = state.jobs.find(j => j.id === button.dataset.id);
  if (!job) return;
  const action = button.dataset.action;
  if (action === 'log') {showLog(job.id);return;}
  button.disabled = true;
  try {
    if (action === 'cancel') await api('/api/cancel', {id:job.id});
    if (action === 'retry') {await api('/api/jobs', {urls:[job.url], options:job.options});toast('再試行をキューに追加しました');}
    if (action === 'save') {
      const file = job.files[Number(button.dataset.index)];
      if (!file) return;
      const ticket = await api('/api/ticket', {id:job.id,name:file.name});
      if (!/^\/download\/[A-Za-z0-9_-]+$/.test(ticket.path)) throw new Error('保存リンクの形式が正しくありません。');
      const anchor = document.createElement('a');
      anchor.href = state.bridge + ticket.path;
      anchor.download = file.name;
      anchor.referrerPolicy = 'no-referrer';
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      toast('ブラウザに保存を要求しました。ファイルはPCの保存先にもあります。');
    }
    if (action !== 'save') await poll();
  } catch(error) {toast(error.message);}
  finally {button.disabled = false;}
}

$$('[data-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
$$('[data-connect]').forEach(button => button.addEventListener('click', openConnection));
$$('[data-mode]').forEach(button => button.addEventListener('click', () => {state.options.mode = button.dataset.mode;settingsChanged();}));
$$('[data-quality]').forEach(button => button.addEventListener('click', () => {$('#quality').value = button.dataset.quality;settingsChanged();}));
for (const id of Object.values(optionFields)) $(`#${id}`).addEventListener('change', settingsChanged);
$('#urls').addEventListener('input', () => {errorAt('#form-error');updateCommand();});
$('#clear-urls').addEventListener('click', () => {$('#urls').value = '';updateCommand();$('#urls').focus();});
$('#shell').addEventListener('change', updateCommand);
$('#copy-command').addEventListener('click', copyCommand);
$('#copy-command-large').addEventListener('click', copyCommand);
$('#paste').addEventListener('click', async () => {
  try {$('#urls').value = await navigator.clipboard.readText();updateCommand();}
  catch {$('#urls').focus();toast('URL入力欄で Ctrl+V / ⌘V を押して貼り付けてください。');}
});
$('#inspect').addEventListener('click', inspect);
$('#download-form').addEventListener('submit', startDownload);
$('#connect-form').addEventListener('submit', connect);
$('#close-connect').addEventListener('click', () => $('#connect-dialog').close());
$('#setup-help').addEventListener('click', () => {$('#connect-dialog').close();setView('guide');});
$('#close-log').addEventListener('click', () => $('#log-dialog').close());
$('#jobs').addEventListener('click', jobAction);
$$('.queue-tabs button').forEach(button => button.addEventListener('click', () => {
  state.filter = button.dataset.filter;
  $$('.queue-tabs button').forEach(b => b.classList.toggle('active', b === button));
  renderJobs();
}));
$('#clear-jobs').addEventListener('click', async () => {
  if (!state.connected || !state.jobs.length) return;
  try {await api('/api/clear', {});await poll();toast('終了したジョブの履歴をクリアしました');}
  catch(error) {toast(error.message);}
});

settingsChanged();
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has('token')) {
  const token = fragment.get('token');
  const address = fragment.get('bridge') || location.origin;
  history.replaceState(null, '', location.pathname + location.search);
  try {
    state.bridge = bridgeUrl(address);
    $('#bridge-address').value = state.bridge;
    $('#bridge-token').value = token;
    if (state.bridge === location.origin) connect();
    else openConnection();
  } catch(error) {toast(error.message);}
}
