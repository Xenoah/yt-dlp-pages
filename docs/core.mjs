export const DEFAULTS = Object.freeze({mode:'video', quality:'1080', container:'mp4', audioFormat:'mp3', subtitles:'none', subLang:'ja,en', metadata:true, thumbnail:false, playlist:false, playlistLimit:20});

export function parseUrls(text) {
  const urls = [...new Set(text.split(/\r?\n/).map(s => s.trim()).filter(Boolean))];
  if (!urls.length) throw new Error('動画や音声のURLを入力してください。');
  if (urls.length > 20) throw new Error('一度に追加できるURLは20件までです。');
  for (const value of urls) {
    let u;
    try { u = new URL(value); } catch { throw new Error(`URLの形式を確認してください：${value.slice(0, 70)}`); }
    if (!['https:', 'http:'].includes(u.protocol) || u.username || u.password || /[\x00-\x1f]/.test(value) || value.length > 8192)
      throw new Error('http / https の動画URLを、1行に1件ずつ入力してください。');
  }
  return urls;
}

export function bridgeUrl(value) {
  const url = new URL(value.trim());
  if (url.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(url.hostname) || url.username || url.password || url.search || url.hash || !['', '/'].includes(url.pathname))
    throw new Error('接続先は http://127.0.0.1:9731 のような、このPCのアドレスを指定してください。');
  return url.origin;
}

export function commandArgs(options, urls) {
  const o = {...DEFAULTS, ...options};
  const args = ['--ignore-config', '--no-plugin-dirs', '--js-runtimes', 'node'];
  args.push(...(o.playlist ? ['--yes-playlist', '--playlist-end', String(o.playlistLimit)] : ['--no-playlist']));
  if (o.mode === 'audio') {
    args.push('-f', 'ba/b');
    if (o.audioFormat !== 'original') args.push('-x', '--audio-format', o.audioFormat, '--audio-quality', '0');
  } else {
    const h = o.quality === 'best' ? '' : `[height<=?${o.quality}]`;
    const ext = o.container === 'mkv' ? '' : `[ext=${o.container}]`;
    const a = {mp4:'[ext=m4a]', webm:'[ext=webm]', mkv:''}[o.container];
    args.push('-f', `bv*${h}${ext}+ba${a}/b${h}${ext}`, '--merge-output-format', o.container, '--remux-video', o.container);
  }
  if (o.metadata) args.push('--embed-metadata');
  if (o.thumbnail) args.push('--write-thumbnail');
  if (o.subtitles !== 'none') {
    args.push('--write-subs', '--sub-langs', o.subLang);
    if (o.subtitles === 'auto') args.push('--write-auto-subs');
  }
  return [...args, '--windows-filenames', '-o', '%(title).150B [%(id)s].%(ext)s', '--', ...urls];
}

export function shellQuote(value, shell = 'powershell') {
  if (/^[A-Za-z0-9_./:=+-]+$/.test(value)) return value;
  return "'" + value.replaceAll("'", shell === 'powershell' ? "''" : "'\"'\"'") + "'";
}

export function commandLine(options, urls, shell) {
  return 'yt-dlp ' + commandArgs(options, urls).map(v => shellQuote(v, shell)).join(' ');
}

export function bytes(value) {
  if (!Number.isFinite(value) || value < 0) return '—';
  const i = Math.min(3, Math.floor(Math.log(Math.max(1,value)) / Math.log(1024)));
  return `${(value / 1024 ** i).toFixed(i ? 1 : 0)} ${['B','KB','MB','GB'][i]}`;
}

export function duration(seconds) {
  if (!Number.isFinite(seconds)) return '—';
  const t = Math.max(0, Math.round(seconds));
  return [Math.floor(t/3600), Math.floor(t%3600/60), t%60].map((v,i) => i ? String(v).padStart(2,'0') : String(v)).join(':').replace(/^0:/,'');
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
