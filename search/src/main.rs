//! Dictionary search for illegal-in-nepal.org.
//!
//! GET /search?q=<query> returns up to LIMIT entries from the site's
//! search-data.json.gz as JSON. The data is re-fetched every REFRESH and
//! results are cached in memory until it changes.

use std::collections::HashMap;
use std::io::Read;
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::Duration;

use flate2::read::GzDecoder;
use serde::{Deserialize, Serialize};
use tiny_http::{Header, Response, Server};
use unicode_normalization::UnicodeNormalization;

const LIMIT: usize = 20;
const CACHE_CAP: usize = 10_000;
const REFRESH: Duration = Duration::from_secs(3600);
const THREADS: usize = 4;

#[derive(Deserialize, Serialize)]
struct Entry {
    word: String,
    slug: String,
    grammar: String,
    preview: String,
}

struct Index {
    entries: Vec<Entry>,
    words: Vec<String>,
    previews: Vec<String>,
    etag: Option<String>,
}

fn normalize(s: &str) -> String {
    s.trim().nfc().collect::<String>().to_lowercase()
}

impl Index {
    fn new(entries: Vec<Entry>, etag: Option<String>) -> Self {
        let words = entries.iter().map(|e| normalize(&e.word)).collect();
        let previews = entries.iter().map(|e| normalize(&e.preview)).collect();
        Index { entries, words, previews, etag }
    }

    /// Exact word, then words starting with the query, then words containing
    /// it, then definitions containing it; shorter words first within a tier.
    fn search(&self, query: &str) -> String {
        let mut hits: Vec<(u8, usize, usize)> = Vec::new();
        for (i, word) in self.words.iter().enumerate() {
            let tier = if word == query {
                0
            } else if word.starts_with(query) {
                1
            } else if word.contains(query) {
                2
            } else if self.previews[i].contains(query) {
                3
            } else {
                continue;
            };
            hits.push((tier, word.chars().count(), i));
        }
        hits.sort_unstable();
        let top: Vec<&Entry> = hits.iter().take(LIMIT).map(|&(_, _, i)| &self.entries[i]).collect();
        serde_json::to_string(&top).expect("entries serialize")
    }
}

/// Fetch the search data; Ok(None) means it hasn't changed since `etag`.
fn fetch(url: &str, etag: Option<&str>) -> Result<Option<Index>, Box<dyn std::error::Error>> {
    let mut request = ureq::get(url).timeout(Duration::from_secs(120));
    if let Some(etag) = etag {
        request = request.set("If-None-Match", etag);
    }
    let response = request.call()?;
    if response.status() == 304 {
        return Ok(None);
    }
    let etag = response.header("ETag").map(str::to_owned);
    let mut compressed = Vec::new();
    response.into_reader().read_to_end(&mut compressed)?;
    let mut json = String::new();
    GzDecoder::new(&compressed[..]).read_to_string(&mut json)?;
    Ok(Some(Index::new(serde_json::from_str(&json)?, etag)))
}

fn main() {
    let url = std::env::var("SEARCH_DATA")
        .unwrap_or_else(|_| "https://illegal-in-nepal.org/shabdakosh/search-data.json.gz".into());
    let addr = std::env::var("SEARCH_ADDR").unwrap_or_else(|_| "127.0.0.1:8091".into());

    let index = match fetch(&url, None) {
        Ok(Some(index)) => Arc::new(RwLock::new(index)),
        Ok(None) => unreachable!("unconditional fetch returned 304"),
        Err(e) => panic!("loading {url}: {e}"),
    };
    let cache: Arc<Mutex<HashMap<String, Arc<String>>>> = Arc::default();
    eprintln!("loaded {} entries", index.read().unwrap().entries.len());

    {
        let (index, cache) = (index.clone(), cache.clone());
        thread::spawn(move || loop {
            thread::sleep(REFRESH);
            let etag = index.read().unwrap().etag.clone();
            match fetch(&url, etag.as_deref()) {
                Ok(Some(fresh)) => {
                    eprintln!("reloaded {} entries", fresh.entries.len());
                    *index.write().unwrap() = fresh;
                    cache.lock().unwrap().clear();
                }
                Ok(None) => {}
                Err(e) => eprintln!("refresh failed: {e}"),
            }
        });
    }

    let server = Arc::new(Server::http(&addr).expect("bind"));
    let headers = [
        Header::from_bytes("Content-Type", "application/json; charset=utf-8").unwrap(),
        Header::from_bytes("Access-Control-Allow-Origin", "*").unwrap(),
        Header::from_bytes("Cache-Control", "public, max-age=3600").unwrap(),
    ];
    let workers: Vec<_> = (0..THREADS)
        .map(|_| {
            let (server, index, cache, headers) =
                (server.clone(), index.clone(), cache.clone(), headers.clone());
            thread::spawn(move || {
                for request in server.incoming_requests() {
                    let (path, params) = request.url().split_once('?').unwrap_or((request.url(), ""));
                    if path != "/search" {
                        let _ = request.respond(Response::empty(404));
                        continue;
                    }
                    let query = form_urlencoded::parse(params.as_bytes())
                        .find(|(k, _)| k == "q")
                        .map(|(_, v)| normalize(&v))
                        .unwrap_or_default();
                    let cached = cache.lock().unwrap().get(&query).cloned();
                    let body = if query.is_empty() {
                        Arc::new("[]".to_owned())
                    } else if let Some(hit) = cached {
                        hit
                    } else {
                        let body = Arc::new(index.read().unwrap().search(&query));
                        let mut cache = cache.lock().unwrap();
                        if cache.len() >= CACHE_CAP {
                            cache.clear();
                        }
                        cache.insert(query, body.clone());
                        body
                    };
                    let mut response = Response::from_string(body.as_str());
                    for header in &headers {
                        response.add_header(header.clone());
                    }
                    let _ = request.respond(response);
                }
            })
        })
        .collect();
    for worker in workers {
        worker.join().unwrap();
    }
}
