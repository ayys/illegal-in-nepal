'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { akshars, forDay, SIZE } = require('./crossword.js');

assert.deepStrictEqual(akshars('आँगन'), ['आँ', 'ग', 'न']);
assert.deepStrictEqual(akshars('किताब'), ['कि', 'ता', 'ब']);
assert.deepStrictEqual(akshars('संसार'), ['सं', 'सा', 'र']);
assert.strictEqual(akshars('क्षमा'), null);

const lexiconPath = path.join(__dirname, 'output', 'crossword.json.gz');
const rows = JSON.parse(zlib.gunzipSync(fs.readFileSync(lexiconPath)).toString('utf8'));
const known = new Map(rows.map(([word, clue]) => [word, clue]));
const hints = new Map(rows.map(([word, , hint]) => [word, hint || '']));

const runs = (grid) => {
  const found = [];
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      for (const [dr, dc, dir] of [[0, 1, 'across'], [1, 0, 'down']]) {
        const before = grid[r - dr] && grid[r - dr][c - dc];
        if (!grid[r][c] || before) continue;
        let word = '';
        let len = 0;
        while (grid[r + dr * len] && grid[r + dr * len][c + dc * len]) {
          word += grid[r + dr * len][c + dc * len];
          len++;
        }
        if (len > 1) found.push(`${dir}:${r},${c}:${word}`);
      }
    }
  }
  return found.sort();
};

const checkPuzzle = (puzzle, day) => {
  const across = puzzle.words.filter((w) => w.dir === 'across');
  const down = puzzle.words.filter((w) => w.dir === 'down');
  assert.ok(across.length >= 2, `${day}: needs two across`);
  assert.ok(down.length >= 2, `${day}: needs two down`);
  assert.ok(puzzle.words.length >= 6, `${day}: needs at least six words`);

  const words = new Set();
  for (const w of puzzle.words) {
    assert.strictEqual(known.get(w.word), w.clue, `${day}: ${w.word} must come from the lexicon`);
    assert.strictEqual(hints.get(w.word), w.hint, `${day}: ${w.word} must carry its hint`);
    assert.ok(!words.has(w.word), `${day}: ${w.word} repeated`);
    words.add(w.word);
  }

  const expected = puzzle.words.map((w) => `${w.dir}:${w.row},${w.col}:${w.word}`).sort();
  assert.deepStrictEqual(runs(puzzle.grid), expected, `${day}: grid has an accidental word`);

  const cellsOf = (w) => w.cells.map((_, i) =>
    w.dir === 'across' ? `${w.row},${w.col + i}` : `${w.row + i},${w.col}`);
  const reached = new Set([0]);
  let grew = true;
  while (grew) {
    grew = false;
    puzzle.words.forEach((w, i) => {
      if (reached.has(i)) return;
      const mine = new Set(cellsOf(w));
      for (const j of reached) {
        if (cellsOf(puzzle.words[j]).some((cell) => mine.has(cell))) {
          reached.add(i);
          grew = true;
          return;
        }
      }
    });
  }
  assert.strictEqual(reached.size, puzzle.words.length, `${day}: words must all connect`);

  const numbers = puzzle.words.map((w) => w.number);
  assert.ok(numbers.every((n) => Number.isInteger(n) && n > 0), `${day}: every clue numbered`);
};

(async () => {
  const day = '2026-10-14';
  const a = await forDay(rows, day);
  const b = await forDay(rows, day);
  assert.deepStrictEqual(a, b, 'same day must give the same puzzle');

  const other = await forDay(rows, '2026-10-15');
  assert.notDeepStrictEqual(a.grid, other.grid, 'next day must give a new grid');

  const start = Date.UTC(2026, 0, 1);
  const sizes = [];
  for (let i = 0; i < 120; i++) {
    const d = new Date(start + i * 86400000).toISOString().slice(0, 10);
    const puzzle = await forDay(rows, d);
    checkPuzzle(puzzle, d);
    sizes.push(puzzle.words.length);
  }
  console.log(`crossword ok: 120 days, ${Math.min(...sizes)}–${Math.max(...sizes)} words each`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
