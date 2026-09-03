/**
 * Libre.fm "Now Playing" Widget
 * Version: 1.1.6-mod
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
    minutesAgo: (n) => n + ' मिनेट अघि',
    hoursAgo: (n) => n + ' घण्टा अघि',
    daysAgo: (n) => n + ' दिन अघि'
  };

  function fieldText(value) {
    if (typeof value === 'string') return value;
    if (value && typeof value === 'object' && typeof value['#text'] === 'string') {
      return value['#text'];
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

  function listenHref(track, songlinkUrl) {
    if (songlinkUrl) return songlinkUrl;
    return 'https://www.youtube.com/results?search_query=' +
      encodeURIComponent(track.artist + ' ' + track.name);
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

  function pickSonglink(results) {
    const rank = { itunes: 0, ytmusic: 1, youtube: 2 };
    return (results || [])
      .filter((item) => item && item.url)
      .sort((a, b) => (rank[a.source] ?? 9) - (rank[b.source] ?? 9))[0]?.url || null;
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
  exports.pickSonglink = pickSonglink;
  exports.isFreshCache = isFreshCache;
  exports.cachedTracks = cachedTracks;

  if (typeof document === 'undefined') return;

  const VERSION = '1.1.6-mod';

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

  const songlinkCache = new Map();
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
    if (opts.bullet !== false) {
      wrap.appendChild(document.createTextNode(' \u2022 '));
    }
    const listen = createLink(listenHref(track), 'lib-listen-link', COPY.listen);
    wrap.appendChild(listen);
    parent.appendChild(wrap);

    getSonglinkUrl(track.artist, track.name).then((url) => {
      if (!url || !wrap.isConnected) return;
      listen.href = listenHref(track, url);
    });
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
    appendListenLink(footer, track);
    parent.appendChild(footer);
    return footer;
  };

  const getPlaceholder = (seed, size) => {
    return `https://picsum.photos/seed/${encodeURIComponent(seed)}/${size}`;
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
      titleMatches(item.trackName, name) && titleMatches(item.artistName, artist)
    ) || results.find((item) => titleMatches(item.trackName, name)) || null;
    return hit && hit.trackId
      ? { source: 'itunes', url: songlinkFromItunes(hit.trackId) }
      : null;
  }

  async function lookupYoutubeMusic(artist, name) {
    const query = encodeURIComponent(artist + ' ' + name);
    for (const base of PIPED_APIS) {
      try {
        const data = await fetchJson(base + '/search?q=' + query + '&filter=music_songs');
        const items = data.items || [];
        const hit = items.find((item) => titleMatches(item.title, name));
        const videoId = youtubeIdFromUrl(hit && hit.url);
        if (videoId) return { source: 'ytmusic', url: songlinkFromYoutube(videoId) };
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
        const hit = items.find((item) => titleMatches(item.title, name));
        if (hit && hit.videoId) {
          return { source: 'youtube', url: songlinkFromYoutube(hit.videoId) };
        }
      } catch (e) { /* try next instance */ }
    }
    return null;
  }

  async function getSonglinkUrl(artist, trackName) {
    const cacheKey = (artist + '-' + trackName).toLowerCase();
    if (songlinkCache.has(cacheKey)) return songlinkCache.get(cacheKey);

    const settled = await Promise.allSettled([
      lookupItunes(artist, trackName),
      lookupYoutubeMusic(artist, trackName),
      lookupYoutube(artist, trackName)
    ]);
    const found = settled
      .filter((result) => result.status === 'fulfilled' && result.value)
      .map((result) => result.value);
    const url = pickSonglink(found);
    songlinkCache.set(cacheKey, url);
    return url;
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
    imgElement.dataset.mbidLoadId = uniqueId;

    let mbid = track.mbid;
    if (!mbid && track.album && track.artist) {
      mbid = await getMbid(track.artist, track.album);
    }

    if (!imgElement.isConnected || imgElement.dataset.mbidLoadId !== uniqueId) return;

    if (mbid) {
      imgElement.src = `https://coverartarchive.org/release/${mbid}/front-${size}`;
    } else {
      imgElement.src = getPlaceholder(track.artist + (track.album || ''), size);
    }

    imgElement.onerror = () => {
      if (imgElement.dataset.retried === 'true') {
        imgElement.onerror = null;
        imgElement.src = getPlaceholder(track.artist, size);
        return;
      }
      imgElement.dataset.retried = 'true';
      imgElement.src = getPlaceholder(track.artist, size);
    };
  }

  // --- 3. CSS STYLES (Shadow DOM) ---
  const getStyles = () => `
    :host {
      display: block;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .librefm-widget {
      border-radius: 12px;
      width: 100%;
      max-width: 500px;
      overflow: hidden;
      line-height: 1.4;
      background: var(--librefm-bg, #1a1a1a);
      border: 1px solid var(--librefm-border, #333);
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
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
    .theme-minimal .lib-artist { color: #d32f2f; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    
    .lib-pill-group {
      display: flex;
      gap: 6px;
      margin-left: auto;
      flex-shrink: 0;
    }

    .lib-brand-tag {
      text-decoration: none;
      font-weight: 800;
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 4px;
      transition: all 0.2s ease;
      flex-shrink: 0;
      color: #d32f2f;
      border: 1px solid #d32f2f;
    }
    .lib-brand-tag:hover { background: #d32f2f; color: white; }

    .lib-main-card { display: flex; padding: 16px; gap: 16px; }
    .lib-img-link { flex-shrink: 0; }
    .lib-img-standard { width: 90px; height: 90px; border-radius: 8px; object-fit: cover; display: block; background: #333; }
    .lib-content { flex-grow: 1; display: flex; flex-direction: column; min-width: 0; }
    
    .lib-header-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
    }

    .lib-header-row .lib-title { font-weight: 700; font-size: 1.1rem; color: var(--librefm-text-main, #eeeeee); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .lib-brand-pill {
      font-size: 0.6rem;
      font-weight: 900;
      text-transform: uppercase;
      color: #fff;
      background: var(--librefm-red, #d32f2f);
      padding: 2px 6px;
      border-radius: 4px;
      letter-spacing: 0.05em;
      text-decoration: none;
      transition: background 0.2s;
      flex-shrink: 0;
    }
    .lib-brand-pill:hover { background: var(--librefm-red-hover, #ff3d3d); }

    .lib-listen-wrap { white-space: nowrap; }
    .lib-listen-link {
      color: var(--librefm-text-muted, #9ca3af);
      text-decoration: none;
      font-weight: 600;
    }
    .lib-listen-link:hover { color: var(--librefm-red, #d32f2f); }

    .lib-artist-link { color: var(--librefm-red, #d32f2f); font-weight: 600; font-size: 0.95rem; text-decoration: none; }
    .lib-artist-link:hover { text-decoration: underline; }
    .lib-meta { font-size: 0.75rem; color: var(--librefm-text-muted, #9ca3af); margin-bottom: auto; padding-top: 2px; }
    
    .lib-footer { display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--librefm-text-muted, #9ca3af); margin-top: 10px; }
    .lib-avatar { width: 18px; height: 18px; border-radius: 50%; background: #444; vertical-align: middle; }
    .lib-user-link { color: var(--librefm-text-main, #eeeeee); text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 6px; }
    .lib-user-link:hover { color: var(--librefm-red, #d32f2f); }

    .lib-history-list { background: var(--librefm-bg-soft, #242424); border-top: 1px solid var(--librefm-border, #333); }
    .lib-history-item { display: flex; align-items: center; padding: 10px 16px; gap: 12px; border-bottom: 1px solid var(--librefm-border, #333); transition: background 0.2s; }
    .lib-history-item:hover { background: #2a2a2a; }
    .lib-history-item:last-child { border-bottom: none; }
    .lib-history-info { font-size: 0.8rem; flex-grow: 1; min-width: 0; color: var(--librefm-text-muted, #9ca3af); }
    .lib-history-info strong { color: var(--librefm-text-main, #eeeeee); font-size: 0.85rem; white-space: nowrap; }
    .lib-history-time { font-size: 0.7rem; color: var(--librefm-text-muted, #9ca3af); white-space: nowrap; flex-shrink: 0; }

    .lib-error { padding: 16px; color: #ef4444; font-size: 0.9rem; text-align: center; }
    .lib-loading { padding: 16px; color: var(--librefm-text-muted, #9ca3af); font-size: 0.9rem; text-align: center; }

    @keyframes pulse {
      0% { transform: scale(0.9); opacity: 1; }
      50% { transform: scale(1.2); opacity: 0.5; }
      100% { transform: scale(0.9); opacity: 1; }
    }

    :host {
      --librefm-red: #d32f2f;
      --librefm-red-hover: #ff3d3d;
      --librefm-bg: #1a1a1a;
      --librefm-bg-soft: #242424;
      --librefm-border: #333;
      --librefm-text-main: #eeeeee;
      --librefm-text-muted: #9ca3af;
    }
  `;

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
    appendListenLink(pillGroup, track, { bullet: false });

    return widget;
  }

  function renderStandard(data) {
    const track = data.tracks[0];
    const widget = create('div', 'librefm-widget');
    const mainCard = create('div', 'lib-main-card');

    const artLink = createLink(track.url, 'lib-img-link');
    const img = create('img', 'lib-img-standard');
    img.alt = track.album ? track.album + ' चित्र' : COPY.albumArt;
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

    appendUserFooter(content, track);
    mainCard.appendChild(content);
    widget.appendChild(mainCard);

    return widget;
  }

  function renderExtended(data) {
    const track = data.tracks[0];
    const widget = create('div', 'librefm-widget');
    const mainCard = create('div', 'lib-main-card');

    const artLink = createLink(track.url, 'lib-img-link');
    const img = create('img', 'lib-img-standard');
    img.alt = track.album ? track.album + ' चित्र' : COPY.albumArt;
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

    appendUserFooter(content, track);
    mainCard.appendChild(content);
    widget.appendChild(mainCard);

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
