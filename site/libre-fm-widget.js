/**
 * Libre.fm "Now Playing" Widget
 * Version: 1.1.8-mod
 * Credit: https://source.tube/database/libre-fm-now
 * I've modified the original source code to add some missing features
 * and tweaks to suit my needs.
 */

(function (exports) {
  'use strict';

  const COPY = {
    justNow: 'भर्खर',
    listeningNow: 'सुन्दै',
    listen: 'सुन्नु →',
    loading: 'लोड हुँदै…',
    loadError: 'गीत लोड गर्न सकिएन।',
    unknownArtist: 'अज्ञात',
    unknownTrack: 'अज्ञात गीत',
    albumArt: 'एल्बम चित्र',
    listeningLabel: 'सुन्दै:',
    lastLabel: 'अन्तिम:',
    play: 'बजाउ',
    pause: 'रोक',
    minutesAgo: (n) => n + ' मिनेट अघि',
    hoursAgo: (n) => n + ' घण्टा अघि',
    daysAgo: (n) => n + ' दिन अघि'
  };

  function decodeEntities(value) {
    return String(value)
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;|&apos;/g, "'");
  }

  function fieldText(value) {
    if (typeof value === 'string') return decodeEntities(value);
    if (value && typeof value === 'object' && typeof value['#text'] === 'string') {
      return decodeEntities(value['#text']);
    }
    return '';
  }

  function timeAgo(unixTimestamp) {
    if (!unixTimestamp) return COPY.justNow;
    const s = Math.floor((Date.now() - unixTimestamp * 1000) / 1000);
    if (s < 60) return COPY.justNow;
    const m = Math.floor(s / 60);
    if (m < 60) return COPY.minutesAgo(m);
    const h = Math.floor(m / 60);
    if (h < 24) return COPY.hoursAgo(h);
    return COPY.daysAgo(Math.floor(h / 24));
  }

  function listenHref(resolvedUrl) {
    if (!resolvedUrl) return null;
    if (/[?&]search_query=/.test(resolvedUrl)) return null;
    return resolvedUrl;
  }

  function songlinkFromItunes(trackId) {
    return 'https://song.link/i/' + trackId;
  }

  function songlinkFromYoutube(videoId) {
    return 'https://song.link/y/' + videoId;
  }

  function normalizeText(value) {
    return String(value || '')
      .toLowerCase()
      .normalize('NFKC')
      .replace(/[^\p{L}\p{N}]+/gu, ' ')
      .trim();
  }

  function titleMatches(candidate, expected) {
    const a = normalizeText(candidate);
    const b = normalizeText(expected);
    if (!a || !b) return false;
    return a === b || a.includes(b) || b.includes(a);
  }

  const ARTIST_STOP = new Set(['the', 'and', 'of', 'ft', 'feat', 'featuring', 'official']);

  function significantTokens(value) {
    return normalizeText(value)
      .replace(/\s+topic$/, '')
      .split(' ')
      .filter((token) => token.length > 1 && !ARTIST_STOP.has(token));
  }

  function artistAppears(candidateArtist, candidateTitle, expectedArtist) {
    const needed = significantTokens(expectedArtist);
    const hay = normalizeText(
      String(candidateArtist || '').replace(/\s*-\s*topic$/i, '') + ' ' + (candidateTitle || '')
    );
    if (needed.length) return needed.every((token) => hay.includes(token));
    const expected = normalizeText(expectedArtist);
    return Boolean(expected && hay.includes(expected));
  }

  function catalogHit(title, artist, expectedTitle, expectedArtist) {
    return titleMatches(title, expectedTitle) && artistAppears(artist, title, expectedArtist);
  }

  function pickSonglink(results) {
    const rank = { ytmusic: 0, itunes: 1, youtube: 2 };
    return (results || [])
      .filter((item) => item && item.url)
      .sort((a, b) => (rank[a.source] ?? 9) - (rank[b.source] ?? 9))[0]?.url || null;
  }

  function youtubeWatchUrl(videoId, source) {
    if (!videoId) return null;
    if (source === 'ytmusic') return 'https://music.youtube.com/watch?v=' + videoId;
    return 'https://www.youtube.com/watch?v=' + videoId;
  }

  function youtubeEmbedUrl(videoId, origin) {
    if (typeof videoId !== 'string' || !/^[A-Za-z0-9_-]{11}$/.test(videoId)) return null;
    const params = new URLSearchParams({
      enablejsapi: '1',
      controls: '0',
      disablekb: '1',
      fs: '0',
      iv_load_policy: '3',
      modestbranding: '1',
      playsinline: '1',
      rel: '0'
    });
    if (origin) params.set('origin', origin);
    return 'https://www.youtube-nocookie.com/embed/' + videoId + '?' + params.toString();
  }

  function youtubeCommand(func, args) {
    return JSON.stringify({ event: 'command', func, args: args || [] });
  }

  function formatPlayerTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins + ':' + String(secs).padStart(2, '0');
  }

  function parseYoutubeMessage(data) {
    if (data && typeof data === 'object') return data;
    if (typeof data !== 'string' || data.charAt(0) !== '{') return null;
    try {
      return JSON.parse(data);
    } catch (e) {
      return null;
    }
  }

  function isYoutubePlayerOrigin(origin) {
    try {
      const host = new URL(origin).hostname;
      return host === 'www.youtube.com' || host === 'youtube.com' || host === 'www.youtube-nocookie.com';
    } catch (e) {
      return false;
    }
  }

  function listenLinks(results) {
    const list = results || [];
    const ytRank = { ytmusic: 0, youtube: 1 };
    const yt = list
      .filter((item) => item && item.videoId && (item.source === 'ytmusic' || item.source === 'youtube'))
      .sort((a, b) => (ytRank[a.source] ?? 9) - (ytRank[b.source] ?? 9))[0];
    if (yt) return { href: youtubeWatchUrl(yt.videoId, yt.source), videoId: yt.videoId };
    return { href: pickSonglink(list) };
  }

  function scaledItunesArtwork(url, size) {
    if (!url) return null;
    return url.replace(/\d+x\d+bb/, size + 'x' + size + 'bb');
  }

  function youtubeThumb(videoId) {
    if (!videoId) return null;
    return 'https://i.ytimg.com/vi/' + videoId + '/hqdefault.jpg';
  }

  function pickArtworkUrls(results, size, caaUrl) {
    const rank = { ytmusic: 0, youtube: 1, caa: 2, itunes: 3 };
    const items = [];
    (results || []).forEach((item) => {
      if (!item) return;
      if (item.source === 'itunes') {
        const url = scaledItunesArtwork(item.artwork, size);
        if (url) items.push({ source: 'itunes', url });
        return;
      }
      if (item.videoId && (item.source === 'ytmusic' || item.source === 'youtube')) {
        items.push({ source: item.source, url: youtubeThumb(item.videoId) });
      }
    });
    if (caaUrl) items.push({ source: 'caa', url: caaUrl });
    return items
      .sort((a, b) => (rank[a.source] ?? 9) - (rank[b.source] ?? 9))
      .map((item) => item.url);
  }

  function isFreshCache(cached, cacheTime, now) {
    if (!cached || !cached.data || !cached.timestamp) return false;
    const ttl = cached.nowPlaying ? Math.min(cacheTime, 60 * 1000) : cacheTime;
    return (now - cached.timestamp) < ttl;
  }

  function cachedTracks(cached) {
    const tracks = cached && cached.data && cached.data.tracks;
    return Array.isArray(tracks) && tracks.length ? cached.data : null;
  }

  function youtubeIdFromUrl(url) {
    const match = String(url || '').match(/(?:[?&]v=|youtu\.be\/)([A-Za-z0-9_-]{11})/);
    return match ? match[1] : null;
  }

  exports.fieldText = fieldText;
  exports.timeAgo = timeAgo;
  exports.COPY = COPY;
  exports.listenHref = listenHref;
  exports.songlinkFromItunes = songlinkFromItunes;
  exports.songlinkFromYoutube = songlinkFromYoutube;
  exports.titleMatches = titleMatches;
  exports.catalogHit = catalogHit;
  exports.pickSonglink = pickSonglink;
  exports.listenLinks = listenLinks;
  exports.pickArtworkUrls = pickArtworkUrls;
  exports.youtubeWatchUrl = youtubeWatchUrl;
  exports.youtubeEmbedUrl = youtubeEmbedUrl;
  exports.youtubeCommand = youtubeCommand;
  exports.formatPlayerTime = formatPlayerTime;
  exports.parseYoutubeMessage = parseYoutubeMessage;
  exports.isYoutubePlayerOrigin = isYoutubePlayerOrigin;
  exports.isFreshCache = isFreshCache;
  exports.cachedTracks = cachedTracks;

  if (typeof document === 'undefined') return;

  const VERSION = '1.1.8-mod';

  // --- 1. CONFIGURATION ---
  const script = document.currentScript;
  if (!script) {
    console.error('[Libre.fm] Widget must be loaded via synchronous script tag');
    return;
  }

  const dataset = script.dataset;
  const srcParams = new URLSearchParams(script.src.split('?')[1] || '');

  const requestedCache = parseInt(dataset.cache || srcParams.get('cache'));

  const config = {
    username: dataset.username || srcParams.get('username'),
    theme: dataset.theme || srcParams.get('theme') || 'standard',
    limit: parseInt(dataset.limit || srcParams.get('limit')) || 5,
    cacheDuration: requestedCache,
    userAvatar: dataset.avatar || srcParams.get('avatar') || null,
    brandUrl: dataset.brandUrl || srcParams.get('brandUrl') || 'https://libre.fm',
    cacheKey: `librefm_tracks_${dataset.username || srcParams.get('username')}_${dataset.theme || srcParams.get('theme') || 'standard'}`,
    cacheTime: requestedCache === 0 ? 0 : (requestedCache || 5) * 60 * 1000, 
    useSessionStorage: (dataset.sessionStorage || srcParams.get('sessionStorage')) === 'true'
  };

  // --- MBID CACHE CONSTANTS ---
  const MBID_CACHE_KEY = `librefm_mbids_v1`;
  const MBID_CACHE_MAX_SIZE = 200;
  const mbCache = new Map();
  let mbCacheSaveTimeout = null;
  let mbCacheDirty = false;

  const catalogCache = new Map();
  const PIPED_APIS = [
    'https://api.piped.private.coffee',
    'https://pipedapi.adminforge.de'
  ];
  const INVIDIOUS_APIS = [
    'https://invidious.flokinet.to',
    'https://invidious.protokolla.fi',
    'https://invidious.projectsegfau.lt'
  ];

  if (!config.username) {
    console.error('[Libre.fm] Username is required. Add data-username="YOUR_USERNAME" to the script tag.');
    return;
  }

  loadMbCache();

  // --- 2. HELPER FUNCTIONS ---
  const create = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  };

  const createLink = (href, className, text) => {
    const a = create('a', className, text);
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    return a;
  };

  const appendListenLink = (parent, track, opts = {}) => {
    const wrap = create('span', 'lib-listen-wrap');
    wrap.hidden = true;
    if (opts.bullet !== false) {
      wrap.appendChild(document.createTextNode(' \u2022 '));
    }
    const listen = createLink('#', 'lib-listen-link', COPY.listen);
    wrap.appendChild(listen);
    parent.appendChild(wrap);
    return wrap;
  };

  const postYoutube = (iframe, payload) => {
    if (!iframe.contentWindow) return;
    iframe.contentWindow.postMessage(payload, '*');
  };

  const bindBackgroundPlayer = (iframe, toggle, seek, timeEl) => {
    const playerId = 'lib-' + Math.random().toString(36).slice(2, 8);
    let duration = 0;
    let playing = false;
    let dragging = false;

    const renderTime = (current) => {
      timeEl.textContent = formatPlayerTime(current) + ' / ' + formatPlayerTime(duration);
    };

    const renderToggle = () => {
      toggle.textContent = playing ? COPY.pause : COPY.play;
      toggle.setAttribute('aria-pressed', playing ? 'true' : 'false');
    };

    const command = (func, args) => {
      postYoutube(iframe, youtubeCommand(func, args));
    };

    const onMessage = (event) => {
      if (!isYoutubePlayerOrigin(event.origin)) return;
      const data = parseYoutubeMessage(event.data);
      if (!data) return;

      if (data.event === 'onReady' || data.event === 'initialDelivery') {
        command('playVideo');
      }

      const info = data.info;
      if (!info || typeof info !== 'object') {
        if (data.event === 'onStateChange' && typeof data.info === 'number') {
          playing = data.info === 1;
          renderToggle();
        }
        return;
      }

      if (typeof info.duration === 'number' && info.duration > 0) {
        duration = info.duration;
        seek.max = String(duration);
        seek.disabled = false;
      }
      if (typeof info.currentTime === 'number' && !dragging) {
        seek.value = String(info.currentTime);
        renderTime(info.currentTime);
      }
      if (typeof info.playerState === 'number') {
        playing = info.playerState === 1;
        renderToggle();
      }
    };

    iframe.addEventListener('load', () => {
      postYoutube(iframe, JSON.stringify({ event: 'listening', id: playerId }));
      command('addEventListener', ['onReady']);
      command('addEventListener', ['onStateChange']);
    });

    window.addEventListener('message', onMessage);
    const poll = window.setInterval(() => {
      if (!iframe.isConnected) {
        window.clearInterval(poll);
        window.removeEventListener('message', onMessage);
        return;
      }
      if (playing) command('getCurrentTime');
    }, 500);

    toggle.addEventListener('click', () => {
      command(playing ? 'pauseVideo' : 'playVideo');
    });

    seek.addEventListener('input', () => {
      dragging = true;
      renderTime(Number(seek.value));
    });
    seek.addEventListener('change', () => {
      dragging = false;
      command('seekTo', [Number(seek.value), true]);
    });

    renderToggle();
    renderTime(0);
  };

  const mountResolvedMedia = (track, listenWrap, player) => {
    getListenLinks(track.artist, track.name).then((links) => {
      const href = listenHref(links && links.href);
      if (listenWrap && listenWrap.isConnected && href) {
        const listen = listenWrap.querySelector('.lib-listen-link');
        if (listen) listen.href = href;
        listenWrap.hidden = false;
      }

      const embed = youtubeEmbedUrl(links && links.videoId, window.location.origin);
      if (!player || !player.wrap || !player.wrap.isConnected || !embed) return;
      player.iframe.title = track.name + ' — ' + track.artist;
      bindBackgroundPlayer(player.iframe, player.toggle, player.seek, player.time);
      player.iframe.src = embed;
      player.wrap.hidden = false;
    });
  };

  const appendPlayer = (parent, track) => {
    const wrap = create('div', 'lib-player-wrap');
    wrap.hidden = true;

    const iframe = create('iframe', 'lib-player');
    iframe.allow = 'autoplay; encrypted-media';
    iframe.referrerPolicy = 'strict-origin-when-cross-origin';
    iframe.tabIndex = -1;
    iframe.setAttribute('aria-hidden', 'true');
    iframe.title = track.name;
    wrap.appendChild(iframe);

    const bar = create('div', 'lib-player-bar');
    const toggle = create('button', 'lib-player-toggle', COPY.play);
    toggle.type = 'button';
    toggle.setAttribute('aria-pressed', 'false');

    const seek = create('input', 'lib-player-seek');
    seek.type = 'range';
    seek.min = '0';
    seek.max = '1';
    seek.value = '0';
    seek.step = 'any';
    seek.disabled = true;
    seek.setAttribute('aria-label', track.name);

    const time = create('span', 'lib-player-time', '0:00 / 0:00');

    bar.appendChild(toggle);
    bar.appendChild(seek);
    bar.appendChild(time);
    wrap.appendChild(bar);
    parent.appendChild(wrap);
    return { wrap, iframe, toggle, seek, time };
  };

  const appendUserFooter = (parent, track) => {
    const footer = create('div', 'lib-footer');
    const userLink = createLink(`https://libre.fm/user/${config.username}`, 'lib-user-link');
    if (config.userAvatar) {
      const avatar = create('img', 'lib-avatar');
      avatar.src = config.userAvatar;
      avatar.alt = '';
      userLink.appendChild(avatar);
      userLink.appendChild(document.createTextNode(' '));
    }
    userLink.appendChild(document.createTextNode(config.username));
    footer.appendChild(userLink);
    footer.appendChild(document.createTextNode(' \u2022 '));
    const time = create('span', '', track.nowPlaying ? COPY.listeningNow : timeAgo(track.timestamp));
    footer.appendChild(time);
    const listenWrap = appendListenLink(footer, track);
    parent.appendChild(footer);
    return { footer, listenWrap };
  };

  async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  async function lookupItunes(artist, name) {
    const query = encodeURIComponent(artist + ' ' + name);
    const data = await fetchJson(
      'https://itunes.apple.com/search?term=' + query + '&entity=song&limit=5'
    );
    const results = data.results || [];
    const hit = results.find((item) =>
      catalogHit(item.trackName, item.artistName, name, artist)
    ) || null;
    return hit && hit.trackId
      ? {
          source: 'itunes',
          url: songlinkFromItunes(hit.trackId),
          artwork: hit.artworkUrl100 || hit.artworkUrl60 || null
        }
      : null;
  }

  async function lookupYoutubeMusic(artist, name) {
    const query = encodeURIComponent(artist + ' ' + name);
    for (const base of PIPED_APIS) {
      try {
        const data = await fetchJson(base + '/search?q=' + query + '&filter=music_songs');
        const items = data.items || [];
        const hit = items.find((item) =>
          catalogHit(item.title, item.uploaderName, name, artist)
        );
        const videoId = youtubeIdFromUrl(hit && hit.url);
        if (videoId) {
          return { source: 'ytmusic', videoId, url: songlinkFromYoutube(videoId) };
        }
      } catch (e) { /* try next instance */ }
    }
    return null;
  }

  async function lookupYoutube(artist, name) {
    const query = encodeURIComponent(artist + ' ' + name);
    for (const base of INVIDIOUS_APIS) {
      try {
        const items = await fetchJson(base + '/api/v1/search?q=' + query + '&type=video');
        if (!Array.isArray(items)) continue;
        const hit = items.find((item) =>
          catalogHit(item.title, item.author, name, artist)
        );
        if (hit && hit.videoId) {
          return { source: 'youtube', videoId: hit.videoId, url: songlinkFromYoutube(hit.videoId) };
        }
      } catch (e) { /* try next instance */ }
    }
    return null;
  }

  async function getCatalogHits(artist, trackName) {
    const cacheKey = (artist + '-' + trackName).toLowerCase();
    if (catalogCache.has(cacheKey)) return catalogCache.get(cacheKey);

    const pending = Promise.allSettled([
      lookupItunes(artist, trackName),
      lookupYoutubeMusic(artist, trackName),
      lookupYoutube(artist, trackName)
    ]).then((settled) =>
      settled
        .filter((result) => result.status === 'fulfilled' && result.value)
        .map((result) => result.value)
    );
    catalogCache.set(cacheKey, pending);
    try {
      return await pending;
    } catch (error) {
      catalogCache.delete(cacheKey);
      throw error;
    }
  }

  async function getListenLinks(artist, trackName) {
    return listenLinks(await getCatalogHits(artist, trackName));
  }

  // --- MBID RESOLVER & CACHE ---
  async function getMbid(artist, album) {
    const cacheKey = `${artist}-${album}`.toLowerCase();
    if (mbCache.has(cacheKey)) return mbCache.get(cacheKey);

    try {
      let query = encodeURIComponent(`release:"${album}" AND artist:"${artist}"`);
      let response = await fetch(`https://musicbrainz.org/ws/2/release/?query=${query}&fmt=json&limit=1`);
      let data = await response.json();

      let mbid = data.releases?.[0]?.id || null;

      if (!mbid) {
        query = encodeURIComponent(`${album} ${artist}`);
        response = await fetch(`https://musicbrainz.org/ws/2/release/?query=${query}&fmt=json&limit=5`);
        data = await response.json();
        mbid = data.releases?.[0]?.id || null;
      }

      if (mbCache.size >= MBID_CACHE_MAX_SIZE) {
        const firstKey = mbCache.keys().next().value;
        mbCache.delete(firstKey);
      }

      mbCache.set(cacheKey, mbid);
      scheduleMbCacheSave();
      return mbid;
    } catch (e) {
      console.warn('[Libre.fm] MusicBrainz lookup failed:', e);
      return null;
    }
  }

  function scheduleMbCacheSave() {
    mbCacheDirty = true;
    if (mbCacheSaveTimeout) return;
    mbCacheSaveTimeout = setTimeout(() => {
      saveMbCache();
      mbCacheSaveTimeout = null;
    }, 2000);
  }

  function saveMbCache() {
    if (!mbCacheDirty) return;
    try {
      const cacheObj = Object.fromEntries(mbCache);
      localStorage.setItem(MBID_CACHE_KEY, JSON.stringify(cacheObj));
      mbCacheDirty = false;
    } catch (e) {
      if (e.name === 'QuotaExceededError') {
        try {
          const entries = Array.from(mbCache.entries()).slice(-100);
          mbCache.clear();
          entries.forEach(([k, v]) => mbCache.set(k, v));
          localStorage.setItem(MBID_CACHE_KEY, JSON.stringify(Object.fromEntries(mbCache)));
          mbCacheDirty = false;
        } catch (e2) { }
      }
    }
  }

  function loadMbCache() {
    try {
      const cachedMbids = JSON.parse(localStorage.getItem(MBID_CACHE_KEY) || '{}');
      Object.entries(cachedMbids).forEach(([key, value]) => mbCache.set(key, value));
    } catch (e) {
      try { localStorage.removeItem(MBID_CACHE_KEY); } catch (e2) {}
    }
  }

  async function applyArtwork(imgElement, track, size = 250) {
    const uniqueId = Math.random().toString(36).slice(2);
    imgElement.dataset.artLoadId = uniqueId;

    const hits = await getCatalogHits(track.artist, track.name);
    if (!imgElement.isConnected || imgElement.dataset.artLoadId !== uniqueId) return;

    let caaUrl = null;
    if (track.album && track.artist) {
      const mbid = await getMbid(track.artist, track.album);
      if (mbid) caaUrl = 'https://coverartarchive.org/release/' + mbid + '/front-' + size;
    }
    const urls = pickArtworkUrls(hits, size, caaUrl);
    if (!imgElement.isConnected || imgElement.dataset.artLoadId !== uniqueId) return;

    let index = 0;
    const tryNext = () => {
      if (index >= urls.length) {
        imgElement.onerror = null;
        imgElement.src = '/assets/cat-curl.svg';
        imgElement.style.objectFit = 'contain';
        imgElement.style.padding = '8px';
        return;
      }
      imgElement.src = urls[index++];
    };
    imgElement.onerror = tryNext;
    tryNext();
  }

  // --- 3. CSS STYLES (Shadow DOM) ---
  const getStyles = () => `
    :host {
      display: block;
      margin: 1.6rem 0 1.4rem;
      font-family: "Tiro Devanagari Hindi", "Noto Serif Devanagari", Georgia, serif;
    }

    .librefm-widget {
      position: relative;
      border-radius: 1.4rem 0.4rem 1.6rem 0.8rem;
      width: 100%;
      max-width: 500px;
      overflow: visible;
      line-height: 1.45;
      background: var(--librefm-bg, #fff6ee);
      background-image: url("/assets/paws.svg");
      background-size: 140px 140px;
      border: 2px dashed var(--librefm-border, #edc8a8);
      box-shadow:
        0 0 0 3px #fff,
        0 0 0 6px var(--librefm-red, #e07a3a),
        8px 10px 0 rgba(44, 24, 16, 0.12);
      box-sizing: border-box;
    }

    .theme-minimal {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      font-size: 0.85rem;
      gap: 10px;
      background: transparent;
      border: none;
      box-shadow: none;
      max-width: none;
      color: inherit;
    }

    .theme-minimal .lib-status-indicator {
      width: 8px;
      height: 8px;
      background: #22c55e;
      border-radius: 50%;
      box-shadow: 0 0 8px #22c55e;
      animation: pulse 2s infinite;
      flex-shrink: 0;
    }

    .theme-minimal .lib-label { color: currentColor; font-weight: 500; opacity: 0.7; }
    .theme-minimal .lib-title { font-weight: 700; font-size: 1rem; color: currentColor; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .theme-minimal .lib-sep { color: currentColor; opacity: 0.5; }
    .theme-minimal .lib-artist { color: var(--librefm-red, #b03a22); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    
    .lib-pill-group {
      display: flex;
      gap: 6px;
      margin-left: auto;
      flex-shrink: 0;
    }

    .lib-brand-tag {
      text-decoration: none;
      font-family: "Kalam", serif;
      font-weight: 700;
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 4px;
      transition: all 0.2s ease;
      flex-shrink: 0;
      color: var(--librefm-red, #b03a22);
      border: 1px dashed var(--librefm-red, #b03a22);
    }
    .lib-brand-tag:hover { background: var(--librefm-red, #e07a3a); color: #fff6ee; }

    .lib-main-card { display: flex; padding: 16px; gap: 16px; }
    .lib-img-link { flex-shrink: 0; }
    .lib-img-standard {
      width: 90px;
      height: 90px;
      border-radius: 0.8rem;
      object-fit: cover;
      display: block;
      background: var(--librefm-bg-soft, #fff1dc);
      border: 3px solid var(--librefm-text-main, #2c1810);
    }
    .lib-content { flex-grow: 1; display: flex; flex-direction: column; min-width: 0; }
    
    .lib-header-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
    }

    .lib-header-row .lib-title {
      font-family: "Kalam", "Tiro Devanagari Hindi", serif;
      font-weight: 400;
      font-size: 1.15rem;
      color: var(--librefm-text-main, #2c1810);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .lib-brand-pill {
      font-family: "Kalam", serif;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      color: #fff6ee;
      background: var(--librefm-red, #e07a3a);
      padding: 2px 7px;
      border-radius: 4px;
      letter-spacing: 0.04em;
      text-decoration: none;
      transition: background 0.2s;
      flex-shrink: 0;
    }
    .lib-brand-pill:hover { background: var(--librefm-red-hover, #b03a22); }

    .lib-listen-wrap { white-space: nowrap; }
    .lib-listen-link {
      color: var(--librefm-red, #b03a22);
      text-decoration: underline;
      text-underline-offset: 0.18em;
      text-decoration-style: wavy;
      text-decoration-thickness: 1.2px;
      font-weight: 600;
    }
    .lib-listen-link:hover { color: var(--librefm-red-hover, #e07a3a); }

    .lib-player-wrap {
      position: relative;
      padding: 0 16px 14px;
    }
    .lib-player {
      position: absolute;
      width: 200px;
      height: 200px;
      opacity: 0;
      pointer-events: none;
      border: 0;
      overflow: hidden;
    }
    .lib-player-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      background: var(--librefm-bg-soft, #fff1dc);
      border: 2px dashed var(--librefm-border, #edc8a8);
      border-radius: 999px;
      padding: 6px 12px;
    }
    .lib-player-toggle {
      font-family: inherit;
      font-size: 0.8rem;
      font-weight: 700;
      color: #fff6ee;
      background: var(--librefm-red, #e07a3a);
      border: 0;
      border-radius: 999px;
      padding: 4px 12px;
      cursor: pointer;
    }
    .lib-player-toggle:hover { background: var(--librefm-red-hover, #b03a22); }
    .lib-player-seek {
      flex: 1;
      min-width: 0;
      accent-color: var(--librefm-red, #e07a3a);
    }
    .lib-player-time {
      font-size: 0.7rem;
      color: var(--librefm-text-muted, #8a6456);
      white-space: nowrap;
    }

    .lib-artist-link {
      color: var(--librefm-red, #b03a22);
      font-weight: 600;
      font-size: 0.95rem;
      text-decoration: underline;
      text-underline-offset: 0.18em;
      text-decoration-style: wavy;
      text-decoration-thickness: 1.2px;
    }
    .lib-artist-link:hover { color: var(--librefm-red-hover, #e07a3a); }
    .lib-meta { font-size: 0.75rem; color: var(--librefm-text-muted, #8a6456); margin-bottom: auto; padding-top: 2px; }
    
    .lib-footer { display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--librefm-text-muted, #8a6456); margin-top: 10px; }
    .lib-avatar { width: 18px; height: 18px; border-radius: 50%; background: var(--librefm-bg-soft, #fff1dc); vertical-align: middle; }
    .lib-user-link { color: var(--librefm-text-main, #2c1810); text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 6px; }
    .lib-user-link:hover { color: var(--librefm-red, #b03a22); }

    .lib-history-list { background: var(--librefm-bg-soft, #fff1dc); border-top: 2px dashed var(--librefm-border, #edc8a8); }
    .lib-history-item { display: flex; align-items: center; padding: 10px 16px; gap: 12px; border-bottom: 1px dashed var(--librefm-border, #edc8a8); }
    .lib-history-item:hover { background: #fde6d2; }
    .lib-history-item:last-child { border-bottom: none; }
    .lib-history-info { font-size: 0.8rem; flex-grow: 1; min-width: 0; color: var(--librefm-text-muted, #8a6456); }
    .lib-history-info strong { color: var(--librefm-text-main, #2c1810); font-size: 0.85rem; white-space: nowrap; }
    .lib-history-time { font-size: 0.7rem; color: var(--librefm-text-muted, #8a6456); white-space: nowrap; flex-shrink: 0; }

    .lib-error { padding: 16px; color: var(--librefm-red, #b03a22); font-size: 0.9rem; text-align: center; }
    .lib-loading { padding: 16px; color: var(--librefm-text-muted, #8a6456); font-size: 0.9rem; text-align: center; }

    .lib-cat-sit {
      position: absolute;
      top: -22px;
      right: 12px;
      width: 38px;
      height: auto;
      pointer-events: none;
      z-index: 2;
    }
    .lib-cat-loaf {
      position: absolute;
      left: -10px;
      bottom: -10px;
      width: 56px;
      height: auto;
      pointer-events: none;
      z-index: 2;
    }
    .lib-cat-stretch {
      position: absolute;
      right: 52px;
      bottom: -8px;
      width: 72px;
      height: auto;
      pointer-events: none;
      z-index: 1;
    }

    @keyframes pulse {
      0% { transform: scale(0.9); opacity: 1; }
      50% { transform: scale(1.2); opacity: 0.5; }
      100% { transform: scale(0.9); opacity: 1; }
    }

    :host {
      --librefm-red: #b03a22;
      --librefm-red-hover: #e07a3a;
      --librefm-bg: #fff6ee;
      --librefm-bg-soft: #fff1dc;
      --librefm-border: #edc8a8;
      --librefm-text-main: #2c1810;
      --librefm-text-muted: #8a6456;
    }
  `;

  function decorateCats(widget) {
    const sit = create('img', 'lib-cat-sit');
    sit.src = '/assets/cat-headphones.svg';
    sit.alt = '';
    sit.setAttribute('aria-hidden', 'true');
    widget.appendChild(sit);

    const loaf = create('img', 'lib-cat-loaf');
    loaf.src = '/assets/cat-curl.svg';
    loaf.alt = '';
    loaf.setAttribute('aria-hidden', 'true');
    widget.appendChild(loaf);

    const stretch = create('img', 'lib-cat-stretch');
    stretch.src = '/assets/cat-notes.svg';
    stretch.alt = '';
    stretch.setAttribute('aria-hidden', 'true');
    widget.appendChild(stretch);
  }

  // --- 4. RENDERERS ---
  function renderMinimal(data) {
    const track = data.tracks[0];
    const isPlaying = track.nowPlaying;

    const widget = create('div', 'librefm-widget theme-minimal');

    if (isPlaying) {
      const indicator = create('div', 'lib-status-indicator');
      widget.appendChild(indicator);
    }

    const label = create('span', 'lib-label', isPlaying ? COPY.listeningLabel : COPY.lastLabel);
    widget.appendChild(label);
    const title = create('span', 'lib-title', track.name);
    widget.appendChild(title);
    const sep = create('span', 'lib-sep', '\u2022');
    widget.appendChild(sep);
    const artist = create('span', 'lib-artist', track.artist);
    widget.appendChild(artist);

    const pillGroup = create('div', 'lib-pill-group');
    const brandTag = createLink(config.brandUrl, 'lib-brand-tag', 'libre.fm');
    pillGroup.appendChild(brandTag);
    widget.appendChild(pillGroup);
    const listenWrap = appendListenLink(pillGroup, track, { bullet: false });
    mountResolvedMedia(track, listenWrap);

    return widget;
  }

  function renderStandard(data) {
    const track = data.tracks[0];
    const widget = create('div', 'librefm-widget');
    const mainCard = create('div', 'lib-main-card');

    const artLink = createLink(track.url, 'lib-img-link');
    const img = create('img', 'lib-img-standard');
    img.alt = '';
    artLink.appendChild(img);
    mainCard.appendChild(artLink);

    applyArtwork(img, track, 500);

    const content = create('div', 'lib-content');
    const headerRow = create('div', 'lib-header-row');
    const title = create('span', 'lib-title', track.name);
    headerRow.appendChild(title);

    const pillGroup = create('div', 'lib-pill-group');
    const brandPill = createLink(config.brandUrl, 'lib-brand-pill', 'libre.fm');
    pillGroup.appendChild(brandPill);
    headerRow.appendChild(pillGroup);
    content.appendChild(headerRow);

    const artistLink = createLink(track.url, 'lib-artist-link', track.artist);
    content.appendChild(artistLink);

    if (typeof track.album === 'string' && track.album) {
      const meta = create('div', 'lib-meta', track.album);
      content.appendChild(meta);
    }

    const { listenWrap } = appendUserFooter(content, track);
    mainCard.appendChild(content);
    widget.appendChild(mainCard);
    const player = appendPlayer(widget, track);
    mountResolvedMedia(track, listenWrap, player);
    decorateCats(widget);

    return widget;
  }

  function renderExtended(data) {
    const track = data.tracks[0];
    const widget = create('div', 'librefm-widget');
    const mainCard = create('div', 'lib-main-card');

    const artLink = createLink(track.url, 'lib-img-link');
    const img = create('img', 'lib-img-standard');
    img.alt = '';
    artLink.appendChild(img);
    mainCard.appendChild(artLink);

    applyArtwork(img, track, 500);

    const content = create('div', 'lib-content');
    const headerRow = create('div', 'lib-header-row');
    const title = create('span', 'lib-title', track.name);
    headerRow.appendChild(title);

    const pillGroup = create('div', 'lib-pill-group');
    const brandPill = createLink(config.brandUrl, 'lib-brand-pill', 'libre.fm');
    pillGroup.appendChild(brandPill);
    headerRow.appendChild(pillGroup);
    content.appendChild(headerRow);

    const artistLink = createLink(track.url, 'lib-artist-link', track.artist);
    content.appendChild(artistLink);

    if (typeof track.album === 'string' && track.album) {
      const meta = create('div', 'lib-meta', track.album);
      content.appendChild(meta);
    }

    const { listenWrap } = appendUserFooter(content, track);
    mainCard.appendChild(content);
    widget.appendChild(mainCard);
    const player = appendPlayer(widget, track);
    mountResolvedMedia(track, listenWrap, player);

    if (data.tracks.length > 1) {
      const historyList = create('div', 'lib-history-list');
      const historyTracks = data.tracks.slice(1, 4);
      historyTracks.forEach((historyTrack) => {
        const historyItem = create('div', 'lib-history-item');
        const info = create('div', 'lib-history-info');
        const strong = create('strong', '', historyTrack.name);
        info.appendChild(strong);
        info.appendChild(document.createTextNode(' ' + historyTrack.artist));
        historyItem.appendChild(info);
        const historyTime = create('span', 'lib-history-time', timeAgo(historyTrack.timestamp));
        historyItem.appendChild(historyTime);
        historyList.appendChild(historyItem);
      });
      widget.appendChild(historyList);
    }

    decorateCats(widget);
    return widget;
  }

  function render(data) {
    const host = document.createElement('div');
    host.className = 'librefm-widget-host';
    const shadow = host.attachShadow({ mode: 'open' });

    const styleTag = document.createElement('style');
    styleTag.textContent = getStyles();
    shadow.appendChild(styleTag);

    let widget;
    switch (config.theme) {
      case 'minimal': widget = renderMinimal(data); break;
      case 'extended': widget = renderExtended(data); break;
      case 'standard':
      default: widget = renderStandard(data); break;
    }

    shadow.appendChild(widget);
    script.parentNode.insertBefore(host, script);
  }

  function renderLoading() {
    const host = document.createElement('div');
    host.className = 'librefm-widget-host';
    const shadow = host.attachShadow({ mode: 'open' });

    const styleTag = document.createElement('style');
    styleTag.textContent = getStyles();
    shadow.appendChild(styleTag);

    const widget = create('div', 'librefm-widget');
    const loading = create('div', 'lib-loading', COPY.loading);
    widget.appendChild(loading);
    shadow.appendChild(widget);

    script.parentNode.insertBefore(host, script);
    return host;
  }

  function renderError(message) {
    const host = document.createElement('div');
    host.className = 'librefm-widget-host';
    const shadow = host.attachShadow({ mode: 'open' });

    const styleTag = document.createElement('style');
    styleTag.textContent = getStyles();
    shadow.appendChild(styleTag);

    const widget = create('div', 'librefm-widget');
    const error = create('div', 'lib-error', message);
    widget.appendChild(error);
    shadow.appendChild(widget);

    script.parentNode.insertBefore(host, script);
  }

  // --- 5. DATA LOADING ---
  function parseTrackData(trackData) {
    const artist = fieldText(trackData.artist) || COPY.unknownArtist;
    const name = trackData.name || COPY.unknownTrack;
    const album = fieldText(trackData.album);
    const url = trackData.url || `https://libre.fm/user/${config.username}`;
    const timestamp = trackData.date?.uts || null;
    const nowPlaying = trackData['@attr']?.nowplaying === 'true';
    const mbid = trackData.album?.mbid || trackData.mbid || null;
    return { artist, name, album, url, timestamp, nowPlaying, mbid };
  }

  function loadData() {
    const apiUrl = `https://libre.fm/2.0/?method=user.getRecentTracks&user=${encodeURIComponent(config.username)}&limit=${config.limit}&format=json`;

    return fetch(apiUrl)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (data.error) throw new Error(data.message || 'API Error');
        if (!data.recenttracks?.track) throw new Error('No tracks found');

        const tracks = Array.isArray(data.recenttracks.track)
          ? data.recenttracks.track.map(parseTrackData)
          : [parseTrackData(data.recenttracks.track)];

        return { tracks };
      });
  }

  // --- 6. EXECUTION ---
  function load() {
    const getStorage = () => config.useSessionStorage ? sessionStorage : localStorage;
    let loadingHost = null;

    const finishLoading = () => {
      if (loadingHost && loadingHost.parentNode) {
        loadingHost.parentNode.removeChild(loadingHost);
      }
    };

    const finishRender = (data) => {
      finishLoading();
      if (config.cacheTime === 0) {
        render(data);
        return;
      }

      try {
        const isNowPlaying = data.tracks[0]?.nowPlaying || false;
        getStorage().setItem(
          config.cacheKey,
          JSON.stringify({
            timestamp: Date.now(),
            nowPlaying: isNowPlaying,
            data: data
          })
        );
      } catch (e) {
        console.warn('[Libre.fm] Could not save to cache:', e);
      }
      render(data);
    };

    const readCache = () => {
      if (config.cacheTime === 0) return null;
      try {
        return JSON.parse(getStorage().getItem(config.cacheKey));
      } catch (e) {
        return null;
      }
    };

    const handleError = (error, stale) => {
      finishLoading();
      if (stale) {
        console.warn('[Libre.fm] Using cached tracks after error:', error);
        render(stale);
        return;
      }
      console.error('[Libre.fm] Error:', error);
      renderError(COPY.loadError);
    };

    const cached = readCache();
    if (isFreshCache(cached, config.cacheTime, Date.now())) {
      finishRender(cached.data);
      return;
    }

    loadingHost = renderLoading();

    loadData()
      .then(data => finishRender(data))
      .catch(error => handleError(error, cachedTracks(cached)));
  }

  load();
})(typeof module !== 'undefined' && module.exports ? module.exports : {});
