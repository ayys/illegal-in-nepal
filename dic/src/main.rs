//! Backend for dic.illegal-in-nepal.org.
//!
//! GET /search?q=<query>  up to 20 dictionary entries as JSON
//! GET /wotd              today's word as JSON
//! GET /crossword         today's crossword as JSON
//! GET /<path>.png        a link-preview card for SITE/<path>.html; the
//!                        word-of-the-day page's card shows today's word
//!
//! Data comes from the site's shabdakosh/ directory and is re-fetched every
//! REFRESH. Days are Nepal days.

mod crossword;
mod og;
mod search;
mod wotd;

use std::collections::HashMap;
use std::io::Read;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::Duration;

use flate2::read::GzDecoder;
use sha2::{Digest, Sha256};
use tiny_http::{Header, Request, Response, Server};

type Error = Box<dyn std::error::Error + Send + Sync>;

const CACHE_CAP: usize = 10_000;
const REFRESH: Duration = Duration::from_secs(3600);
/// Retry sooner while some data has never loaded.
const RETRY: Duration = Duration::from_secs(60);
const THREADS: usize = 4;
const WOTD_IMAGE: &str = "/shabdakosh/आजको-शब्द.png";
const SECTIONS: [(&str, &str); 2] = [("shabdakosh", "शब्दकोश"), ("blog", "ब्लग")];

static PARTIALS: AtomicU64 = AtomicU64::new(0);

/// A gzipped JSON file on the site, kept up to date by ETag.
struct Feed<T> {
    url: String,
    parse: fn(&str) -> serde_json::Result<T>,
    loaded: RwLock<Option<(Arc<T>, Option<String>)>>,
}

impl<T> Feed<T> {
    fn new(base: &str, name: &str, parse: fn(&str) -> serde_json::Result<T>) -> Self {
        Feed { url: format!("{base}{name}"), parse, loaded: RwLock::new(None) }
    }

    fn get(&self) -> Option<Arc<T>> {
        self.loaded.read().unwrap().as_ref().map(|(value, _)| value.clone())
    }

    fn fetch(&self, etag: Option<&str>) -> Result<Option<(T, Option<String>)>, Error> {
        let mut request = ureq::get(&self.url).timeout(Duration::from_secs(120));
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
        Ok(Some(((self.parse)(&json)?, etag)))
    }

    /// Returns true if new data was loaded.
    fn refresh(&self) -> bool {
        let etag = self.loaded.read().unwrap().as_ref().and_then(|(_, etag)| etag.clone());
        match self.fetch(etag.as_deref()) {
            Ok(Some((value, etag))) => {
                *self.loaded.write().unwrap() = Some((Arc::new(value), etag));
                eprintln!("loaded {}", self.url);
                true
            }
            Ok(None) => false,
            Err(e) => {
                eprintln!("loading {}: {e}", self.url);
                false
            }
        }
    }
}

/// One value per day, rebuilt when the day or its data changes.
#[derive(Default)]
struct Daily(Mutex<Option<(String, Arc<Vec<u8>>)>>);

impl Daily {
    fn get(&self, day: &str, make: impl FnOnce() -> Option<Vec<u8>>) -> Option<Arc<Vec<u8>>> {
        if let Some((d, value)) = &*self.0.lock().unwrap() {
            if d == day {
                return Some(value.clone());
            }
        }
        let value = Arc::new(make()?);
        *self.0.lock().unwrap() = Some((day.to_owned(), value.clone()));
        Some(value)
    }

    fn clear(&self) {
        *self.0.lock().unwrap() = None;
    }
}

struct App {
    site: String,
    cache_dir: PathBuf,
    renderer: og::Renderer,
    search: Feed<search::Index>,
    wotd: Feed<Vec<wotd::Entry>>,
    crossword: Feed<crossword::Lexicon>,
    searches: Mutex<HashMap<String, Arc<String>>>,
    wotd_json: Daily,
    wotd_png: Daily,
    crossword_json: Daily,
}

impl App {
    /// Returns true once every feed has loaded.
    fn refresh(&self) -> bool {
        if self.search.refresh() {
            self.searches.lock().unwrap().clear();
        }
        if self.wotd.refresh() {
            self.wotd_json.clear();
            self.wotd_png.clear();
        }
        if self.crossword.refresh() {
            self.crossword_json.clear();
        }
        self.search.get().is_some() && self.wotd.get().is_some() && self.crossword.get().is_some()
    }

    fn handle(&self, request: Request) {
        let url = request.url().to_owned();
        let (path, params) = url.split_once('?').unwrap_or((&url, ""));
        let response = match path {
            "/search" => self.search(params),
            "/wotd" => self.wotd(),
            "/crossword" => self.crossword(),
            _ if url.ends_with(".png") => self.image(&url),
            _ => Response::from_data(Vec::new()).with_status_code(404),
        };
        let _ = request.respond(response);
    }

    fn search(&self, params: &str) -> Response<std::io::Cursor<Vec<u8>>> {
        let query = form_urlencoded::parse(params.as_bytes())
            .find(|(k, _)| k == "q")
            .map(|(_, v)| search::normalize(&v))
            .unwrap_or_default();
        let Some(index) = self.search.get() else { return unavailable() };
        let cached = self.searches.lock().unwrap().get(&query).cloned();
        let body = if query.is_empty() {
            Arc::new("[]".to_owned())
        } else if let Some(hit) = cached {
            hit
        } else {
            let body = Arc::new(index.search(&query));
            let mut cache = self.searches.lock().unwrap();
            if cache.len() >= CACHE_CAP {
                cache.clear();
            }
            cache.insert(query, body.clone());
            body
        };
        json(body.as_bytes().to_vec(), 3600)
    }

    fn wotd(&self) -> Response<std::io::Cursor<Vec<u8>>> {
        let day = wotd::today();
        let Some(entries) = self.wotd.get() else { return unavailable() };
        let body = self.wotd_json.get(&day, || {
            wotd::pick(&entries, &day).map(|pick| serde_json::to_vec(&pick).expect("pick serializes"))
        });
        match body {
            Some(body) => json(body.to_vec(), wotd::until_tomorrow()),
            None => unavailable(),
        }
    }

    fn crossword(&self) -> Response<std::io::Cursor<Vec<u8>>> {
        let day = wotd::today();
        let Some(lexicon) = self.crossword.get() else { return unavailable() };
        let body = self.crossword_json.get(&day, || {
            crossword::for_day(&lexicon, &day).map(|puzzle| serde_json::to_vec(&puzzle).expect("puzzle serializes"))
        });
        match body {
            Some(body) => json(body.to_vec(), wotd::until_tomorrow()),
            None => unavailable(),
        }
    }

    fn image(&self, url: &str) -> Response<std::io::Cursor<Vec<u8>>> {
        if !url.starts_with('/') || url.contains(['?', '#']) || url.contains("..") {
            return Response::from_data(Vec::new()).with_status_code(404);
        }
        if percent_decode(url) == WOTD_IMAGE {
            return self.wotd_image();
        }
        let hex: String = Sha256::digest(url.as_bytes()).iter().map(|b| format!("{b:02x}")).collect();
        let cached = self.cache_dir.join(format!("{hex}.png"));
        if let Ok(png) = std::fs::read(&cached) {
            return image(png, "public, max-age=86400".into());
        }
        let page = format!("{}{}.html", self.site, &url[..url.len() - ".png".len()]);
        let html = match ureq::get(&page).timeout(Duration::from_secs(10)).set("User-Agent", "og-image").call() {
            Ok(response) => match response.into_string() {
                Ok(html) => html,
                Err(_) => return Response::from_data(Vec::new()).with_status_code(502),
            },
            Err(ureq::Error::Status(404, _)) => return Response::from_data(Vec::new()).with_status_code(404),
            Err(_) => return Response::from_data(Vec::new()).with_status_code(502),
        };
        let section = url.trim_start_matches('/').split('/').next().unwrap_or("");
        let footer = match SECTIONS.iter().find(|(dir, _)| *dir == section) {
            Some((_, name)) => format!("illegal-in-nepal.org  ·  {name}"),
            None => "illegal-in-nepal.org".into(),
        };
        let card = og::parse_page(&html, footer);
        let png = self.renderer.render(&card);
        // Untagged pages are drawn from <title> alone; don't keep those.
        if !card.tagged {
            return image(png, "no-store".into());
        }
        let partial = cached.with_extension(format!("{}.partial", PARTIALS.fetch_add(1, Ordering::Relaxed)));
        let saved = std::fs::create_dir_all(&self.cache_dir)
            .and_then(|_| std::fs::write(&partial, &png))
            .and_then(|_| std::fs::rename(&partial, &cached));
        if let Err(e) = saved {
            eprintln!("caching {}: {e}", cached.display());
        }
        image(png, "public, max-age=86400".into())
    }

    /// Today's word on a card; the site also offers it as an embeddable banner.
    fn wotd_image(&self) -> Response<std::io::Cursor<Vec<u8>>> {
        let day = wotd::today();
        let Some(entries) = self.wotd.get() else { return unavailable() };
        let png = self.wotd_png.get(&day, || {
            let pick = wotd::pick(&entries, &day)?;
            Some(self.renderer.render(&og::Card {
                title: pick.word.to_owned(),
                paragraphs: vec![(String::new(), pick.sense.to_owned())],
                footer: "illegal-in-nepal.org  ·  आजको शब्द".into(),
                tagged: true,
            }))
        });
        match png {
            Some(png) => image(png.to_vec(), format!("public, max-age={}", wotd::until_tomorrow())),
            None => unavailable(),
        }
    }
}

fn header(name: &str, value: &str) -> Header {
    Header::from_bytes(name, value).expect("valid header")
}

fn json(body: Vec<u8>, max_age: u64) -> Response<std::io::Cursor<Vec<u8>>> {
    Response::from_data(body)
        .with_header(header("Content-Type", "application/json; charset=utf-8"))
        .with_header(header("Access-Control-Allow-Origin", "*"))
        .with_header(header("Cache-Control", &format!("public, max-age={max_age}")))
}

fn image(png: Vec<u8>, cache_control: String) -> Response<std::io::Cursor<Vec<u8>>> {
    Response::from_data(png)
        .with_header(header("Content-Type", "image/png"))
        .with_header(header("Access-Control-Allow-Origin", "*"))
        .with_header(header("Cache-Control", &cache_control))
}

fn unavailable() -> Response<std::io::Cursor<Vec<u8>>> {
    Response::from_data(Vec::new())
        .with_status_code(503)
        .with_header(header("Access-Control-Allow-Origin", "*"))
        .with_header(header("Cache-Control", "no-store"))
}

fn percent_decode(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        let hex = bytes.get(i + 1..i + 3).and_then(|h| std::str::from_utf8(h).ok());
        match (bytes[i], hex.and_then(|h| u8::from_str_radix(h, 16).ok())) {
            (b'%', Some(b)) => {
                out.push(b);
                i += 3;
            }
            (b, _) => {
                out.push(b);
                i += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn main() {
    let env = |name: &str, default: &str| std::env::var(name).unwrap_or_else(|_| default.to_owned());
    let site = env("DIC_SITE", "https://illegal-in-nepal.org");
    let data = env("DIC_DATA", &format!("{site}/shabdakosh/"));
    let addr = env("DIC_ADDR", "127.0.0.1:8091");
    let fonts = env("DIC_FONTS", "/opt/dic/fonts");

    let app = Arc::new(App {
        renderer: og::Renderer::new(fonts.as_ref()).unwrap_or_else(|e| panic!("loading fonts from {fonts}: {e}")),
        cache_dir: env("CACHE_DIRECTORY", "/tmp/dic-cache").into(),
        search: Feed::new(&data, "search-data.json.gz", search::Index::parse),
        wotd: Feed::new(&data, "wotd.json.gz", wotd::parse),
        crossword: Feed::new(&data, "crossword.json.gz", crossword::Lexicon::parse),
        site,
        searches: Mutex::default(),
        wotd_json: Daily::default(),
        wotd_png: Daily::default(),
        crossword_json: Daily::default(),
    });
    let mut ready = app.refresh();
    if let Some(index) = app.search.get() {
        eprintln!("{} search entries", index.len());
    }
    if let Some(lexicon) = app.crossword.get() {
        eprintln!("{} crossword words", lexicon.len());
    }

    {
        let app = app.clone();
        thread::spawn(move || {
            loop {
                thread::sleep(if ready { REFRESH } else { RETRY });
                ready = app.refresh();
            }
        });
    }

    let server = Arc::new(Server::http(&addr).expect("bind"));
    let workers: Vec<_> = (0..THREADS)
        .map(|_| {
            let (server, app) = (server.clone(), app.clone());
            thread::spawn(move || {
                for request in server.incoming_requests() {
                    app.handle(request);
                }
            })
        })
        .collect();
    for worker in workers {
        worker.join().unwrap();
    }
}
