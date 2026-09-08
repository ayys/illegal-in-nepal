'use strict';

const assert = require('assert');
const {
  fieldText,
  listenLinks,
  youtubeEmbedUrl,
  youtubeCommand,
  formatPlayerTime,
  parseYoutubeMessage,
  COPY
} = require('./libre-fm-widget.js');

assert.strictEqual(
  fieldText({ '#text': 'Tatiana Eva-Marie &amp; Duved Dunayevsky', mbid: '' }),
  'Tatiana Eva-Marie & Duved Dunayevsky',
  'Libre.fm artist #text must decode HTML entities'
);

const embed = youtubeEmbedUrl('LvAC0coG-gk');
assert.ok(embed.startsWith('https://www.youtube-nocookie.com/embed/LvAC0coG-gk?'));
assert.ok(embed.includes('enablejsapi=1'));
assert.ok(embed.includes('controls=0'));
assert.strictEqual(youtubeEmbedUrl('not_a_valid_id'), null);
assert.strictEqual(youtubeEmbedUrl(''), null);
assert.strictEqual(youtubeEmbedUrl(null), null);

assert.strictEqual(formatPlayerTime(65), '1:05');
assert.strictEqual(formatPlayerTime(0), '0:00');
assert.strictEqual(formatPlayerTime(NaN), '0:00');

assert.strictEqual(
  youtubeCommand('playVideo'),
  JSON.stringify({ event: 'command', func: 'playVideo', args: [] })
);
assert.deepStrictEqual(parseYoutubeMessage('{"event":"onReady"}'), { event: 'onReady' });
assert.strictEqual(parseYoutubeMessage('ok'), null);

assert.strictEqual(COPY.play, 'बजाउ');
assert.strictEqual(COPY.pause, 'रोक');

const youtubeHit = listenLinks([
  { source: 'youtube', videoId: 'LvAC0coG-gk', url: 'https://song.link/y/LvAC0coG-gk' }
]);
assert.strictEqual(youtubeHit.videoId, 'LvAC0coG-gk');
assert.ok(youtubeEmbedUrl(youtubeHit.videoId));

const itunesOnly = listenLinks([
  { source: 'itunes', url: 'https://song.link/i/123' }
]);
assert.strictEqual(itunesOnly.videoId, undefined);
assert.strictEqual(youtubeEmbedUrl(itunesOnly.videoId), null);

console.log('ok');
