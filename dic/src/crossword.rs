//! The daily crossword. Players' saved progress is keyed by day and cell, so
//! a day's puzzle must not change: keep every draw from the generator in the
//! same order.

use std::collections::{HashMap, HashSet};

use serde::Serialize;
use sha2::{Digest, Sha256};
use unicode_normalization::UnicodeNormalization;

// Keep SIZE / MIN_LEN / akshars in sync with crossword_lib.py.
pub const SIZE: usize = 7;
const MIN_LEN: usize = 3;
const MIN_WORDS: usize = 6;
const TARGET_WORDS: usize = 10;
const MAX_ATTEMPTS: usize = 50;

/// Split into cells: an independent vowel, or a consonant with an optional
/// vowel sign, then an optional chandrabindu / anusvara / visarga. None if
/// anything else (e.g. a conjunct) is in the word.
pub fn akshars(word: &str) -> Option<Vec<String>> {
    let chars: Vec<char> = word.nfc().collect();
    let within = |i: usize, lo: u32, hi: u32| chars.get(i).is_some_and(|&c| (lo..=hi).contains(&(c as u32)));
    let mut cells = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let start = i;
        if within(i, 0x0905, 0x0914) {
            i += 1;
        } else if within(i, 0x0915, 0x0939) {
            i += 1;
            if within(i, 0x093e, 0x094c) {
                i += 1;
            }
        } else {
            return None;
        }
        if within(i, 0x0901, 0x0903) {
            i += 1;
        }
        cells.push(chars[start..i].iter().collect());
    }
    (!cells.is_empty()).then_some(cells)
}

struct Entry {
    word: String,
    clue: String,
    cells: Vec<String>,
}

pub struct Lexicon {
    entries: Vec<Entry>,
    by_key: HashMap<String, Vec<usize>>,
    starters: Vec<usize>,
}

fn key(len: usize, i: usize, akshar: &str) -> String {
    format!("{len}:{i}:{akshar}")
}

impl Lexicon {
    /// Rows of crossword.json.gz: [word, clue].
    pub fn parse(json: &str) -> serde_json::Result<Self> {
        let rows: Vec<(String, String)> = serde_json::from_str(json)?;
        let mut lexicon = Lexicon { entries: Vec::new(), by_key: HashMap::new(), starters: Vec::new() };
        for (word, clue) in rows {
            let Some(cells) = akshars(&word) else { continue };
            if cells.len() < MIN_LEN || cells.len() > SIZE {
                continue;
            }
            let id = lexicon.entries.len();
            if cells.len() == 4 || cells.len() == 5 {
                lexicon.starters.push(id);
            }
            for (i, a) in cells.iter().enumerate() {
                lexicon.by_key.entry(key(cells.len(), i, a)).or_default().push(id);
            }
            lexicon.entries.push(Entry { word, clue, cells });
        }
        Ok(lexicon)
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }
}

/// sfc32, seeded from the first 16 bytes of a SHA-256 digest.
struct Rand([u32; 4]);

impl Rand {
    fn new(seed: &str) -> Self {
        let digest = Sha256::digest(seed.as_bytes());
        let word = |i: usize| u32::from_be_bytes(digest[i * 4..i * 4 + 4].try_into().unwrap());
        Rand([word(0), word(1), word(2), word(3)])
    }

    fn next(&mut self) -> f64 {
        let [a, b, c, d] = &mut self.0;
        let t = a.wrapping_add(*b).wrapping_add(*d);
        *d = d.wrapping_add(1);
        *a = *b ^ (*b >> 9);
        *b = c.wrapping_add(*c << 3);
        *c = c.rotate_left(21).wrapping_add(t);
        f64::from(t) / 4_294_967_296.0
    }

    /// Math.floor(rand() * n)
    fn below(&mut self, n: usize) -> usize {
        (self.next() * n as f64).floor() as usize
    }

    fn shuffle<T>(&mut self, list: &mut [T]) {
        for i in (1..list.len()).rev() {
            let j = self.below(i + 1);
            list.swap(i, j);
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
enum Dir {
    Across,
    Down,
}

impl Dir {
    fn step(self) -> (i32, i32) {
        match self {
            Dir::Across => (0, 1),
            Dir::Down => (1, 0),
        }
    }

    fn other(self) -> Dir {
        match self {
            Dir::Across => Dir::Down,
            Dir::Down => Dir::Across,
        }
    }

    fn name(self) -> &'static str {
        match self {
            Dir::Across => "across",
            Dir::Down => "down",
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
struct Slot {
    row: i32,
    col: i32,
    dir: Dir,
    len: usize,
}

struct Placed {
    entry: usize,
    row: i32,
    col: i32,
    dir: Dir,
}

#[derive(Serialize)]
pub struct Word<'a> {
    number: usize,
    dir: &'static str,
    row: i32,
    col: i32,
    word: &'a str,
    clue: &'a str,
    cells: &'a [String],
}

#[derive(Serialize)]
pub struct Puzzle<'a> {
    day: &'a str,
    size: usize,
    grid: Vec<Vec<Option<&'a str>>>,
    words: Vec<Word<'a>>,
}

fn inside(r: i32, c: i32) -> bool {
    r >= 0 && c >= 0 && (r as usize) < SIZE && (c as usize) < SIZE
}

struct Board<'a> {
    lexicon: &'a Lexicon,
    grid: [[Option<&'a str>; SIZE]; SIZE],
    taken: [[[bool; 2]; SIZE]; SIZE],
    placed: Vec<Placed>,
    used: HashSet<&'a str>,
}

impl<'a> Board<'a> {
    fn at(&self, r: i32, c: i32) -> Option<&'a str> {
        if inside(r, c) { self.grid[r as usize][c as usize] } else { None }
    }

    fn place(&mut self, id: usize, row: i32, col: i32, dir: Dir) {
        let entry = &self.lexicon.entries[id];
        let (dr, dc) = dir.step();
        for (i, a) in entry.cells.iter().enumerate() {
            let (r, c) = ((row + dr * i as i32) as usize, (col + dc * i as i32) as usize);
            self.grid[r][c] = Some(a);
            self.taken[r][c][dir as usize] = true;
        }
        self.placed.push(Placed { entry: id, row, col, dir });
        self.used.insert(&entry.word);
    }

    fn candidate(&self, slot: Slot, rand: &mut Rand) -> Option<usize> {
        let Slot { row, col, dir, len } = slot;
        let (dr, dc) = dir.step();
        let end_r = row + dr * (len as i32 - 1);
        let end_c = col + dc * (len as i32 - 1);
        if !inside(row, col) || !inside(end_r, end_c) {
            return None;
        }
        if self.at(row - dr, col - dc).is_some() || self.at(end_r + dr, end_c + dc).is_some() {
            return None;
        }

        let mut fixed = Vec::new();
        for i in 0..len {
            let (r, c) = (row + dr * i as i32, col + dc * i as i32);
            if let Some(a) = self.grid[r as usize][c as usize] {
                if self.taken[r as usize][c as usize][dir as usize] {
                    return None;
                }
                fixed.push((i, a));
            } else if self.at(r + dc, c + dr).is_some() || self.at(r - dc, c - dr).is_some() {
                return None;
            }
        }
        if fixed.is_empty() || fixed.len() == len {
            return None;
        }

        let mut bucket: Option<&Vec<usize>> = None;
        for &(i, a) in &fixed {
            let list = self.lexicon.by_key.get(&key(len, i, a))?;
            if bucket.is_none_or(|b| list.len() < b.len()) {
                bucket = Some(list);
            }
        }
        let bucket = bucket?;
        let offset = rand.below(bucket.len());
        (0..bucket.len()).map(|k| bucket[(offset + k) % bucket.len()]).find(|&id| {
            let entry = &self.lexicon.entries[id];
            !self.used.contains(entry.word.as_str()) && fixed.iter().all(|&(i, a)| entry.cells[i] == a)
        })
    }
}

fn build<'a>(lexicon: &'a Lexicon, day: &'a str, rand: &mut Rand) -> Option<Puzzle<'a>> {
    let mut board = Board {
        lexicon,
        grid: [[None; SIZE]; SIZE],
        taken: [[[false; 2]; SIZE]; SIZE],
        placed: Vec::new(),
        used: HashSet::new(),
    };

    let first = lexicon.starters[rand.below(lexicon.starters.len())];
    let len = lexicon.entries[first].cells.len();
    board.place(first, (SIZE / 2) as i32, ((SIZE - len) / 2) as i32, Dir::Across);

    while board.placed.len() < TARGET_WORDS {
        let mut seen = HashSet::new();
        let mut options = Vec::new();
        for w in &board.placed {
            let (dr, dc) = w.dir.step();
            let dir = w.dir.other();
            let (nr, nc) = dir.step();
            for i in 0..lexicon.entries[w.entry].cells.len() as i32 {
                for len in MIN_LEN..=SIZE {
                    for k in 0..len as i32 {
                        let slot = Slot { row: w.row + dr * i - nr * k, col: w.col + dc * i - nc * k, dir, len };
                        if seen.insert(slot) {
                            options.push(slot);
                        }
                    }
                }
            }
        }
        rand.shuffle(&mut options);
        let Some((slot, id)) = options.iter().find_map(|&slot| board.candidate(slot, rand).map(|id| (slot, id)))
        else {
            break;
        };
        board.place(id, slot.row, slot.col, slot.dir);
    }

    let across = board.placed.iter().filter(|w| w.dir == Dir::Across).count();
    if board.placed.len() < MIN_WORDS || across < 2 || board.placed.len() - across < 2 {
        return None;
    }

    let mut starts: Vec<i32> = board.placed.iter().map(|w| w.row * SIZE as i32 + w.col).collect();
    starts.sort_unstable();
    starts.dedup();
    let mut words: Vec<Word> = board
        .placed
        .iter()
        .map(|w| {
            let entry = &lexicon.entries[w.entry];
            Word {
                number: starts.binary_search(&(w.row * SIZE as i32 + w.col)).unwrap() + 1,
                dir: w.dir.name(),
                row: w.row,
                col: w.col,
                word: &entry.word,
                clue: &entry.clue,
                cells: &entry.cells,
            }
        })
        .collect();
    words.sort_by_key(|w| (w.dir != "across", w.number));
    Some(Puzzle { day, size: SIZE, grid: board.grid.iter().map(|row| row.to_vec()).collect(), words })
}

pub fn for_day<'a>(lexicon: &'a Lexicon, day: &'a str) -> Option<Puzzle<'a>> {
    if lexicon.starters.is_empty() {
        return None;
    }
    (0..MAX_ATTEMPTS).find_map(|attempt| {
        let seed = if attempt == 0 { day.to_owned() } else { format!("{day}#{attempt}") };
        build(lexicon, day, &mut Rand::new(&seed))
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Read;

    #[test]
    fn splits_akshars() {
        assert_eq!(akshars("आँगन").unwrap(), ["आँ", "ग", "न"]);
        assert_eq!(akshars("किताब").unwrap(), ["कि", "ता", "ब"]);
        assert_eq!(akshars("संसार").unwrap(), ["सं", "सा", "र"]);
        assert_eq!(akshars("क्षमा"), None);
        assert_eq!(akshars(""), None);
    }

    fn lexicon() -> Option<Lexicon> {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../shabdakosh/output/crossword.json.gz");
        let file = std::fs::File::open(path).ok()?;
        let mut json = String::new();
        flate2::read::GzDecoder::new(file).read_to_string(&mut json).unwrap();
        Some(Lexicon::parse(&json).unwrap())
    }

    /// Every run of two or more filled cells, as "dir:row,col:word".
    fn runs(grid: &[Vec<Option<&str>>]) -> Vec<String> {
        let at = |r: i32, c: i32| if inside(r, c) { grid[r as usize][c as usize] } else { None };
        let mut found = Vec::new();
        for r in 0..SIZE as i32 {
            for c in 0..SIZE as i32 {
                for (dr, dc, dir) in [(0, 1, "across"), (1, 0, "down")] {
                    if at(r, c).is_none() || at(r - dr, c - dc).is_some() {
                        continue;
                    }
                    let mut word = String::new();
                    let mut len = 0;
                    while let Some(a) = at(r + dr * len, c + dc * len) {
                        word += a;
                        len += 1;
                    }
                    if len > 1 {
                        found.push(format!("{dir}:{r},{c}:{word}"));
                    }
                }
            }
        }
        found.sort();
        found
    }

    #[test]
    fn puzzles_are_valid() {
        let Some(lexicon) = lexicon() else {
            eprintln!("skipped: build shabdakosh/output/crossword.json.gz first");
            return;
        };
        let clues: HashMap<&str, &str> =
            lexicon.entries.iter().map(|e| (e.word.as_str(), e.clue.as_str())).collect();
        let days: Vec<String> = (1..=12)
            .flat_map(|m| (1..=10).map(move |d| format!("2026-{m:02}-{d:02}")))
            .collect();
        for day in &days {
            let puzzle = for_day(&lexicon, day).unwrap();
            let across = puzzle.words.iter().filter(|w| w.dir == "across").count();
            assert!(across >= 2 && puzzle.words.len() - across >= 2, "{day}: two of each direction");
            assert!(puzzle.words.len() >= MIN_WORDS, "{day}: at least six words");

            let mut seen = HashSet::new();
            for w in &puzzle.words {
                assert_eq!(clues[w.word], w.clue, "{day}: {} must come from the lexicon", w.word);
                assert!(seen.insert(w.word), "{day}: {} repeated", w.word);
                assert!(w.number > 0);
            }
            let mut expected: Vec<String> =
                puzzle.words.iter().map(|w| format!("{}:{},{}:{}", w.dir, w.row, w.col, w.word)).collect();
            expected.sort();
            assert_eq!(runs(&puzzle.grid), expected, "{day}: grid has an accidental word");
        }
        let a = serde_json::to_string(&for_day(&lexicon, "2026-10-14")).unwrap();
        assert_eq!(a, serde_json::to_string(&for_day(&lexicon, "2026-10-14")).unwrap());
        assert_ne!(a, serde_json::to_string(&for_day(&lexicon, "2026-10-15")).unwrap());
    }
}
