import test from 'node:test';
import assert from 'node:assert/strict';
import {DEFAULTS, parseUrls, bridgeUrl, commandArgs, commandLine, shellQuote, escapeHtml, bytes, duration} from '../docs/core.mjs';

test('URLs: preserve query, deduplicate and reject invalid protocols or credentials', () => {
  assert.deepEqual(parseUrls(' https://example.org/watch?v=1&list=2\nhttps://example.org/watch?v=1&list=2\n'), ['https://example.org/watch?v=1&list=2']);
  for (const url of ['', '--exec whoami', 'file:///etc/passwd', 'javascript:alert(1)', 'https://user:pass@example.org/video', 'https://example.org/\u0001']) assert.throws(() => parseUrls(url));
  assert.throws(() => parseUrls(Array.from({length:21},(_,i) => `https://example.org/${i}`).join('\n')));
});
test('Connection credentials can only be sent to explicit loopback addresses', () => {
  assert.equal(bridgeUrl('http://127.0.0.1:9731/'), 'http://127.0.0.1:9731');
  assert.equal(bridgeUrl('http://localhost:9732'), 'http://localhost:9732');
  for (const url of ['https://example.org','http://127.0.0.1.evil.example:9731','http://127.0.0.1:9731/other','http://localhost:9731?token=x','http://u:p@localhost:9731']) assert.throws(() => bridgeUrl(url));
});
test('Video resolution, container and playlist cap reach command arguments', () => {
  const args = commandArgs({...DEFAULTS,quality:'720',container:'mp4',playlist:true,playlistLimit:7},['https://example.org']);
  assert.equal(args[args.indexOf('-f')+1], 'bv*[height<=?720][ext=mp4]+ba[ext=m4a]/b[height<=?720][ext=mp4]');
  assert.equal(args[args.indexOf('--playlist-end')+1], '7');
  assert.equal(args[args.indexOf('--remux-video')+1], 'mp4');
  assert.deepEqual(args.slice(-2), ['--','https://example.org']);
});
test('Original audio avoids conversion; subtitle and thumbnail switches are accurate', () => {
  const args = commandArgs({...DEFAULTS,mode:'audio',audioFormat:'original',metadata:false,thumbnail:true,subtitles:'auto'},['https://example.org']);
  assert.ok(!args.includes('-x'));
  assert.ok(!args.includes('--embed-metadata'));
  assert.ok(args.includes('--write-auto-subs'));
  assert.ok(args.includes('--write-subs'));
  assert.ok(args.includes('--write-thumbnail'));
  assert.ok(args.includes('--no-playlist'));
});
test('Shell quoting keeps quotes and command substitution literal', () => {
  const input = "https://example.org/?v=it's&x=$(whoami)`id`";
  assert.equal(shellQuote(input,'powershell'), "'https://example.org/?v=it''s&x=$(whoami)`id`'");
  assert.equal(shellQuote(input,'bash'), "'https://example.org/?v=it'\"'\"'s&x=$(whoami)`id`'");
  assert.ok(commandLine(DEFAULTS,[input],'bash').endsWith(shellQuote(input,'bash')));
});
test('Untrusted titles are escaped and display helpers handle missing metadata', () => {
  assert.equal(escapeHtml('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
  assert.equal(bytes(1048576),'1.0 MB');
  assert.equal(bytes(null),'—');
  assert.equal(duration(3661),'1:01:01');
  assert.equal(duration(null),'—');
});
