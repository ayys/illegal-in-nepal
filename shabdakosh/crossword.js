(function (exports) {
    'use strict';

    // Keep SIZE / MIN_LEN / AKSHAR in sync with crossword_lib.py.
    const SIZE = 7;
    const MIN_LEN = 3;
    const MIN_WORDS = 6;
    const TARGET_WORDS = 10;
    const MAX_ATTEMPTS = 50;
    const AKSHAR = /(?:[\u0905-\u0914]|[\u0915-\u0939][\u093e-\u094c]?)[\u0901-\u0903]?/g;

    const akshars = (word) => {
        const text = (word || '').normalize('NFC');
        const cells = text.match(AKSHAR) || [];
        return cells.join('') === text && cells.length ? cells : null;
    };

    const push = (map, key, value) => {
        const list = map.get(key);
        if (list) list.push(value);
        else map.set(key, [value]);
    };

    const indexes = new WeakMap();
    const indexLexicon = (rows) => {
        if (indexes.has(rows)) return indexes.get(rows);
        const byKey = new Map();
        const starters = [];
        for (const [word, clue, hint = ''] of rows) {
            const cells = akshars(word);
            if (!cells || cells.length < MIN_LEN || cells.length > SIZE) continue;
            const entry = { word, clue, hint, cells };
            if (cells.length === 4 || cells.length === 5) starters.push(entry);
            cells.forEach((a, i) => push(byKey, `${cells.length}:${i}:${a}`, entry));
        }
        const index = { byKey, starters };
        indexes.set(rows, index);
        return index;
    };

    // sfc32, seeded from the first 16 bytes of a SHA-256 digest.
    const prng = (bytes) => {
        const view = new DataView(bytes.buffer, bytes.byteOffset, 16);
        let a = view.getUint32(0), b = view.getUint32(4), c = view.getUint32(8), d = view.getUint32(12);
        return () => {
            a |= 0; b |= 0; c |= 0; d |= 0;
            const t = (((a + b) | 0) + d) | 0;
            d = (d + 1) | 0;
            a = b ^ (b >>> 9);
            b = (c + (c << 3)) | 0;
            c = (c << 21) | (c >>> 11);
            c = (c + t) | 0;
            return (t >>> 0) / 4294967296;
        };
    };

    const shuffle = (list, rand) => {
        for (let i = list.length - 1; i > 0; i--) {
            const j = Math.floor(rand() * (i + 1));
            [list[i], list[j]] = [list[j], list[i]];
        }
        return list;
    };

    const step = (dir) => (dir === 'across' ? [0, 1] : [1, 0]);
    const inside = (r, c) => r >= 0 && c >= 0 && r < SIZE && c < SIZE;

    const build = (index, rand) => {
        const grid = Array.from({ length: SIZE }, () => Array(SIZE).fill(null));
        const taken = Array.from({ length: SIZE }, () =>
            Array.from({ length: SIZE }, () => ({ across: false, down: false })));
        const placed = [];
        const used = new Set();
        const at = (r, c) => (inside(r, c) ? grid[r][c] : null);

        const place = (entry, row, col, dir) => {
            const [dr, dc] = step(dir);
            entry.cells.forEach((a, i) => {
                grid[row + dr * i][col + dc * i] = a;
                taken[row + dr * i][col + dc * i][dir] = true;
            });
            placed.push({ ...entry, row, col, dir });
            used.add(entry.word);
        };

        const candidate = ({ row, col, dir, len }) => {
            const [dr, dc] = step(dir);
            const endR = row + dr * (len - 1);
            const endC = col + dc * (len - 1);
            if (!inside(row, col) || !inside(endR, endC)) return null;
            if (at(row - dr, col - dc) || at(endR + dr, endC + dc)) return null;

            const fixed = [];
            for (let i = 0; i < len; i++) {
                const r = row + dr * i;
                const c = col + dc * i;
                if (grid[r][c]) {
                    if (taken[r][c][dir]) return null;
                    fixed.push([i, grid[r][c]]);
                } else if (at(r + dc, c + dr) || at(r - dc, c - dr)) {
                    return null;
                }
            }
            if (!fixed.length || fixed.length === len) return null;

            let bucket = null;
            for (const [i, a] of fixed) {
                const list = index.byKey.get(`${len}:${i}:${a}`);
                if (!list) return null;
                if (!bucket || list.length < bucket.length) bucket = list;
            }
            const offset = Math.floor(rand() * bucket.length);
            for (let k = 0; k < bucket.length; k++) {
                const entry = bucket[(offset + k) % bucket.length];
                if (!used.has(entry.word) && fixed.every(([i, a]) => entry.cells[i] === a)) {
                    return entry;
                }
            }
            return null;
        };

        const first = index.starters[Math.floor(rand() * index.starters.length)];
        place(first, Math.floor(SIZE / 2), Math.floor((SIZE - first.cells.length) / 2), 'across');

        while (placed.length < TARGET_WORDS) {
            const seen = new Set();
            const options = [];
            for (const w of placed) {
                const [dr, dc] = step(w.dir);
                const dir = w.dir === 'across' ? 'down' : 'across';
                const [nr, nc] = step(dir);
                for (let i = 0; i < w.cells.length; i++) {
                    for (let len = MIN_LEN; len <= SIZE; len++) {
                        for (let k = 0; k < len; k++) {
                            const row = w.row + dr * i - nr * k;
                            const col = w.col + dc * i - nc * k;
                            const key = `${dir}:${row}:${col}:${len}`;
                            if (seen.has(key)) continue;
                            seen.add(key);
                            options.push({ row, col, dir, len });
                        }
                    }
                }
            }
            let grew = false;
            for (const opt of shuffle(options, rand)) {
                const entry = candidate(opt);
                if (entry) {
                    place(entry, opt.row, opt.col, opt.dir);
                    grew = true;
                    break;
                }
            }
            if (!grew) break;
        }

        const across = placed.filter((w) => w.dir === 'across').length;
        if (placed.length < MIN_WORDS || across < 2 || placed.length - across < 2) return null;

        const starts = [...new Set(placed.map((w) => w.row * SIZE + w.col))].sort((a, b) => a - b);
        const words = placed
            .map((w) => ({
                number: starts.indexOf(w.row * SIZE + w.col) + 1,
                dir: w.dir,
                row: w.row,
                col: w.col,
                word: w.word,
                clue: w.clue,
                hint: w.hint,
                cells: w.cells,
            }))
            .sort((a, b) => (a.dir === b.dir ? a.number - b.number : a.dir === 'across' ? -1 : 1));
        return { size: SIZE, grid, words };
    };

    const sha256 = async (text) =>
        new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)));

    const forDay = async (rows, day) => {
        const index = indexLexicon(rows);
        if (!index.starters.length) throw new Error('empty lexicon');
        for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            const seed = await sha256(attempt ? `${day}#${attempt}` : day);
            const puzzle = build(index, prng(seed));
            if (puzzle) return { day, ...puzzle };
        }
        throw new Error('no puzzle for ' + day);
    };

    exports.SIZE = SIZE;
    exports.akshars = akshars;
    exports.forDay = forDay;
})(typeof module !== 'undefined' && module.exports ? module.exports : (window.Crossword = {}));
