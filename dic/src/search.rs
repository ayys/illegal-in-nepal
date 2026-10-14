//! Typo-tolerant word search over the site's search-data.json.gz.

use serde::{Deserialize, Serialize};
use unicode_normalization::UnicodeNormalization;

const LIMIT: usize = 20;

#[derive(Deserialize, Serialize)]
struct Entry {
    word: String,
    slug: String,
    grammar: String,
    preview: String,
}

pub struct Index {
    entries: Vec<Entry>,
    words: Vec<String>,
    loose: Vec<Vec<char>>,
    previews: Vec<String>,
}

pub fn normalize(s: &str) -> String {
    s.trim().nfc().collect::<String>().to_lowercase()
}

/// Fold spellings that are commonly confused when typing Nepali, including
/// conjuncts typed without the halant.
fn loosen(s: &str) -> Vec<char> {
    s.chars()
        .filter(|c| !matches!(c, '\u{093c}' | '\u{094d}' | '\u{200c}' | '\u{200d}'))
        .map(|c| match c {
            'ी' => 'ि',
            'ू' => 'ु',
            'ई' => 'इ',
            'ऊ' => 'उ',
            'ँ' => 'ं',
            'श' | 'ष' => 'स',
            'व' => 'ब',
            'ण' => 'न',
            c => c,
        })
        .collect()
}

/// Edits allowed between a query of `len` characters and a word.
fn max_edits(len: usize) -> usize {
    match len {
        0..=2 => 0,
        3..=4 => 1,
        5..=8 => 2,
        _ => 3,
    }
}

/// Levenshtein distance from `q` to all of `w` and to its closest prefix,
/// or None if both exceed `k`.
fn distances(q: &[char], w: &[char], k: usize) -> Option<(usize, usize)> {
    if w.len() + k < q.len() {
        return None;
    }
    let mut row: Vec<usize> = (0..=w.len()).collect();
    for (i, &qc) in q.iter().enumerate() {
        let mut diagonal = row[0];
        row[0] = i + 1;
        for (j, &wc) in w.iter().enumerate() {
            let above = row[j + 1];
            row[j + 1] = (diagonal + usize::from(qc != wc)).min(above + 1).min(row[j] + 1);
            diagonal = above;
        }
        if row.iter().min().is_some_and(|&m| m > k) {
            return None;
        }
    }
    let full = row[w.len()];
    let prefix = *row.iter().min().unwrap();
    (prefix <= k).then_some((full, prefix))
}

impl Index {
    pub fn parse(json: &str) -> serde_json::Result<Self> {
        let entries: Vec<Entry> = serde_json::from_str(json)?;
        let words: Vec<String> = entries.iter().map(|e| normalize(&e.word)).collect();
        let loose = words.iter().map(|w| loosen(w)).collect();
        let previews = entries.iter().map(|e| normalize(&e.preview)).collect();
        Ok(Index { entries, words, loose, previews })
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Ranks, best first: the exact word; the word up to folded spelling;
    /// words starting with the query, exactly then up to folding; words a few
    /// edits away; words containing the query; words whose beginning is a few
    /// edits away; definitions containing the query. Shorter words first.
    /// `query` must already be normalized.
    pub fn search(&self, query: &str) -> String {
        let loose_query = loosen(query);
        let k = max_edits(loose_query.len());
        let mut hits: Vec<(u8, usize, usize, usize)> = Vec::new();
        for (i, word) in self.words.iter().enumerate() {
            let fuzzy = distances(&loose_query, &self.loose[i], k);
            let (tier, edits) = match fuzzy {
                _ if word == query => (0, 0),
                Some((0, _)) => (1, 0),
                _ if word.starts_with(query) => (2, 0),
                Some((_, 0)) => (3, 0),
                Some((full, _)) if full <= k => (4, full),
                _ if word.contains(query) => (5, 0),
                Some((_, prefix)) => (6, prefix),
                _ if self.previews[i].contains(query) => (7, 0),
                None => continue,
            };
            hits.push((tier, edits, self.loose[i].len(), i));
        }
        hits.sort_unstable();
        let top: Vec<&Entry> = hits.iter().take(LIMIT).map(|&(.., i)| &self.entries[i]).collect();
        serde_json::to_string(&top).expect("entries serialize")
    }
}
