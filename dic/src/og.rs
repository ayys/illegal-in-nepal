//! Link-preview (Open Graph) cards: a page's title and text on a 1200×630 PNG.

use std::path::Path;
use std::sync::{Arc, Mutex};

use cosmic_text::skrifa::instance::{LocationRef, Size};
use cosmic_text::skrifa::{FontRef, MetadataProvider};
use cosmic_text::{Attrs, Buffer, Color, Family, FontSystem, Metrics, Shaping, SwashCache, Wrap, fontdb, harfrust};
use scraper::{Html, Selector};

const WIDTH: usize = 1200;
const HEIGHT: usize = 630;
const MARGIN: f32 = 80.0;
const BG: [u8; 3] = [0xff, 0xf1, 0xdc];
const INK: [u8; 3] = [0x2c, 0x18, 0x10];
const MUTE: [u8; 3] = [0x8a, 0x64, 0x56];
const ACCENT: [u8; 3] = [0xb0, 0x3a, 0x22];

const SERIF: &str = "TiroDevanagariHindi-Regular.ttf";
const HAND: &str = "Kalam-Bold.ttf";

pub struct Card {
    pub title: String,
    /// (grammar tag, text) per paragraph.
    pub paragraphs: Vec<(String, String)>,
    pub footer: String,
    /// False when the page has no og:title, so the card is only a guess.
    pub tagged: bool,
}

/// The card fonts have no emoji; drop them and tidy spacing.
fn clean(s: &str) -> String {
    let kept: String = s
        .chars()
        .filter(|&c| !matches!(c, '\u{2600}'..='\u{27bf}' | '\u{fe0f}' | '\u{1f000}'..='\u{1faff}'))
        .collect();
    let mut out = String::new();
    for word in kept.split_whitespace() {
        let punctuation = word.starts_with([',', '.', ';', ':', '!', '?', '।']);
        if !out.is_empty() && !punctuation {
            out.push(' ');
        }
        out += word;
    }
    out
}

/// Title, entry definitions (or og:description) and whether og:title was set.
pub fn parse_page(html: &str, footer: String) -> Card {
    let doc = Html::parse_document(html);
    let select = |s: &str| Selector::parse(s).expect("valid selector");
    let mut og_title = None;
    let mut og_description = None;
    for meta in doc.select(&select("meta[property^=\"og:\"]")) {
        let content = meta.attr("content").unwrap_or("").to_owned();
        match meta.attr("property") {
            Some("og:title") => og_title = Some(content),
            Some("og:description") => og_description = Some(content),
            _ => {}
        }
    }
    let tagged = og_title.is_some();
    let title = match og_title.filter(|t| !t.is_empty()) {
        Some(t) => t,
        None => doc.select(&select("title")).flat_map(|t| t.text()).collect(),
    };

    // Each grammar tag starts a block; the definitions after it are its senses.
    let mut blocks: Vec<(String, Vec<String>)> = Vec::new();
    for el in doc.select(&select("span[class=\"gram-tag\"], p[class=\"main-definition\"]")) {
        let text: String = el.text().collect();
        if el.value().name() == "span" {
            blocks.push((text, Vec::new()));
        } else {
            if blocks.is_empty() {
                blocks.push((String::new(), Vec::new()));
            }
            blocks.last_mut().unwrap().1.push(text);
        }
    }
    let paragraphs = if blocks.is_empty() {
        vec![(String::new(), clean(&og_description.unwrap_or_default()))]
    } else {
        blocks
            .into_iter()
            .filter(|(_, senses)| !senses.is_empty())
            .map(|(grammar, senses)| (clean(&grammar), clean(&senses.join(" "))))
            .collect()
    };
    Card { title: clean(&title), paragraphs, footer, tagged }
}

struct Face {
    family: String,
    /// Ascender height per unit of font size.
    ascent: f32,
    /// Space advance per unit of font size, after Latin and after Devanagari
    /// text. cosmic-text shapes spaces without their neighbours' script, so
    /// lines are laid out a word at a time.
    space: [f32; 2],
}

fn is_devanagari(word: &str) -> Option<bool> {
    word.chars().rev().find(|c| c.is_alphanumeric()).map(|c| ('\u{0900}'..='\u{097f}').contains(&c))
}

pub struct Renderer {
    fonts: Mutex<(FontSystem, SwashCache)>,
    serif: Face,
    hand: Face,
}

fn load(db: &mut fontdb::Database, path: &Path) -> std::io::Result<Face> {
    let data = std::fs::read(path)?;
    let invalid = |e: String| std::io::Error::new(std::io::ErrorKind::InvalidData, format!("{}: {e}", path.display()));
    let font = FontRef::new(&data).map_err(|e| invalid(e.to_string()))?;
    let metrics = font.metrics(Size::unscaled(), LocationRef::default());
    let em = f32::from(metrics.units_per_em);
    let ascent = metrics.ascent / em;
    let shaper_data = harfrust::ShaperData::new(&font);
    let shaper = shaper_data.shaper(&font).build();
    let space = [harfrust::script::LATIN, harfrust::script::DEVANAGARI].map(|script| {
        let mut buffer = harfrust::UnicodeBuffer::new();
        buffer.push_str(" ");
        buffer.set_script(script);
        buffer.guess_segment_properties();
        shaper.shape(buffer, &[]).glyph_positions().iter().map(|p| p.x_advance as f32).sum::<f32>() / em
    });
    let ids = db.load_font_source(fontdb::Source::Binary(Arc::new(data)));
    let family = ids
        .first()
        .and_then(|&id| db.face(id))
        .and_then(|face| face.families.first())
        .map(|(name, _)| name.clone())
        .ok_or_else(|| invalid("no font family".into()))?;
    Ok(Face { family, ascent, space })
}

struct Canvas(Vec<u8>);

impl Canvas {
    fn new() -> Self {
        Canvas(BG.repeat(WIDTH * HEIGHT))
    }

    fn fill(&mut self, x0: usize, y0: usize, x1: usize, y1: usize, rgb: [u8; 3]) {
        for y in y0..y1.min(HEIGHT) {
            for x in x0..x1.min(WIDTH) {
                let i = (y * WIDTH + x) * 3;
                self.0[i..i + 3].copy_from_slice(&rgb);
            }
        }
    }

    fn blend(&mut self, x: i32, y: i32, w: u32, h: u32, color: Color) {
        let alpha = u32::from(color.a());
        let rgb = [color.r(), color.g(), color.b()];
        for py in y.max(0)..(y + h as i32).min(HEIGHT as i32) {
            for px in x.max(0)..(x + w as i32).min(WIDTH as i32) {
                let i = (py as usize * WIDTH + px as usize) * 3;
                for (dst, &src) in self.0[i..i + 3].iter_mut().zip(&rgb) {
                    *dst = ((u32::from(*dst) * (255 - alpha) + u32::from(src) * alpha + 127) / 255) as u8;
                }
            }
        }
    }

    fn png(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let mut encoder = png::Encoder::new(&mut out, WIDTH as u32, HEIGHT as u32);
        encoder.set_color(png::ColorType::Rgb);
        encoder.set_compression(png::Compression::High);
        let mut writer = encoder.write_header().expect("png header");
        writer.write_image_data(&self.0).expect("png data");
        writer.finish().expect("png end");
        out
    }
}

/// Shapes and draws single lines of text.
struct Pen<'a> {
    fonts: &'a mut FontSystem,
    cache: &'a mut SwashCache,
    canvas: Canvas,
}

impl Pen<'_> {
    fn shape(&mut self, text: &str, face: &Face, size: f32) -> Buffer {
        let mut buffer = Buffer::new(self.fonts, Metrics::new(size, size * 1.5));
        buffer.set_wrap(self.fonts, Wrap::None);
        buffer.set_size(self.fonts, None, None);
        let attrs = Attrs::new().family(Family::Name(&face.family));
        buffer.set_text(self.fonts, text, &attrs, Shaping::Advanced, None);
        buffer.shape_until_scroll(self.fonts, false);
        buffer
    }

    fn word_width(&mut self, word: &str, face: &Face, size: f32) -> f32 {
        if word.is_empty() {
            return 0.0;
        }
        self.shape(word, face, size).layout_runs().map(|run| run.line_w).fold(0.0, f32::max)
    }

    /// The x of each word in a line, and the line's width. A space takes the
    /// script of the text before it.
    fn layout(&mut self, text: &str, face: &Face, size: f32) -> (Vec<(f32, String)>, f32) {
        let mut words = Vec::new();
        let (mut x, mut devanagari) = (0.0, false);
        for (i, word) in text.split(' ').enumerate() {
            if i > 0 {
                x += face.space[usize::from(devanagari)] * size;
            }
            words.push((x, word.to_owned()));
            x += self.word_width(word, face, size);
            devanagari = is_devanagari(word).unwrap_or(devanagari);
        }
        (words, x)
    }

    fn width(&mut self, text: &str, face: &Face, size: f32) -> f32 {
        self.layout(text, face, size).1
    }

    /// Draw with the top of the font's ascender at y.
    fn text(&mut self, x: f32, y: f32, text: &str, face: &Face, size: f32, rgb: [u8; 3]) {
        for (offset, word) in self.layout(text, face, size).0 {
            if word.is_empty() {
                continue;
            }
            let buffer = self.shape(&word, face, size);
            let Some(baseline) = buffer.layout_runs().next().map(|run| run.line_y) else { continue };
            let (dx, dy) = ((x + offset).round() as i32, (y + face.ascent * size - baseline).round() as i32);
            let canvas = &mut self.canvas;
            buffer.draw(self.fonts, self.cache, Color::rgb(rgb[0], rgb[1], rgb[2]), |px, py, w, h, color| {
                canvas.blend(px + dx, py + dy, w, h, color);
            });
        }
    }

    /// Greedy word wrap; text past max_lines is cut and ends with an ellipsis.
    fn wrap(&mut self, text: &str, face: &Face, size: f32, width: f32, max_lines: usize) -> Vec<String> {
        let mut lines: Vec<String> = Vec::new();
        for word in text.split_whitespace() {
            match lines.last_mut() {
                Some(last) if self.width(&format!("{last} {word}"), face, size) <= width => {
                    last.push(' ');
                    last.push_str(word);
                }
                _ => lines.push(word.to_owned()),
            }
        }
        if lines.len() > max_lines {
            lines.truncate(max_lines);
            let mut last = lines.pop().unwrap();
            while !last.is_empty() && self.width(&format!("{last}…"), face, size) > width {
                last.pop();
            }
            lines.push(format!("{}…", last.trim_end()));
        }
        lines
    }
}

impl Renderer {
    pub fn new(dir: &Path) -> std::io::Result<Self> {
        let mut db = fontdb::Database::new();
        let serif = load(&mut db, &dir.join(SERIF))?;
        let hand = load(&mut db, &dir.join(HAND))?;
        let fonts = FontSystem::new_with_locale_and_db("ne-NP".into(), db);
        Ok(Renderer { fonts: Mutex::new((fonts, SwashCache::new())), serif, hand })
    }

    pub fn render(&self, card: &Card) -> Vec<u8> {
        let mut guard = self.fonts.lock().unwrap();
        let (fonts, cache) = &mut *guard;
        let mut pen = Pen { fonts, cache, canvas: Canvas::new() };
        let (serif, hand) = (&self.serif, &self.hand);
        let width = WIDTH as f32 - 2.0 * MARGIN;
        pen.canvas.fill(0, 0, WIDTH, 15, ACCENT);

        let mut size = 120.0;
        while size > 56.0 && pen.width(&card.title, serif, size) > width {
            size -= 4.0;
        }
        let mut y = MARGIN;
        for line in pen.wrap(&card.title, serif, size, width, 2) {
            pen.text(MARGIN, y, &line, serif, size, INK);
            y += (size * 1.3).floor();
        }

        y += 20.0;
        let bottom = HEIGHT as f32 - 140.0;
        let texts: Vec<String> =
            card.paragraphs.iter().map(|(tag, text)| format!("{tag} {text}").trim().to_owned()).collect();
        // Shrink the body until every paragraph fits, or settle for the smallest size.
        let (mut size, mut step) = (44.0, 0.0);
        while size >= 26.0 {
            step = (size * 1.4f32).floor();
            let lines: usize = texts.iter().map(|t| pen.wrap(t, serif, size, width, 999).len()).sum();
            let gaps = texts.len().saturating_sub(1) as f32 * (step / 3.0).floor();
            if lines as f32 * step + gaps <= bottom - y || size == 26.0 {
                break;
            }
            size -= 2.0;
        }
        for ((tag, _), text) in card.paragraphs.iter().zip(&texts) {
            let room = ((bottom - y) / step).floor();
            if room <= 0.0 {
                break;
            }
            for (i, line) in pen.wrap(text, serif, size, width, room as usize).into_iter().enumerate() {
                let mut x = MARGIN;
                let mut line = line.as_str();
                if i == 0 && !tag.is_empty() {
                    pen.text(x, y, tag, serif, size, ACCENT);
                    x += pen.width(&format!("{tag} "), serif, size);
                    let skip = line.char_indices().nth(tag.chars().count()).map_or(line.len(), |(i, _)| i);
                    line = line[skip..].trim_start();
                }
                pen.text(x, y, line, serif, size, INK);
                y += step;
            }
            y += (step / 3.0).floor();
        }

        let rule = HEIGHT - 120;
        pen.canvas.fill(MARGIN as usize, rule - 1, WIDTH - MARGIN as usize + 1, rule + 1, MUTE);
        pen.text(MARGIN, HEIGHT as f32 - 100.0, &card.footer, hand, 40.0, ACCENT);
        pen.canvas.png()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cleans_text() {
        assert_eq!(clean("  नमस्ते 🙏 , संसार ।  "), "नमस्ते, संसार।");
    }

    #[test]
    fn parses_entries() {
        let html = r#"<html><head><title>T</title><meta property="og:title" content="किताब">
            <meta property="og:description" content="unused"></head><body>
            <span class="gram-tag">ना.</span><p class="main-definition">पुस्तक; <b>ग्रन्थ</b></p>
            <p class="main-definition">अर्को</p><span class="gram-tag">वि.</span></body></html>"#;
        let card = parse_page(html, String::new());
        assert_eq!(card.title, "किताब");
        assert!(card.tagged);
        assert_eq!(card.paragraphs, [("ना.".to_owned(), "पुस्तक; ग्रन्थ अर्को".to_owned())]);

        let card = parse_page("<title>Only</title><meta property=\"og:description\" content=\"d\">", String::new());
        assert_eq!((card.title.as_str(), card.tagged), ("Only", false));
        assert_eq!(card.paragraphs, [(String::new(), "d".to_owned())]);
    }

    #[test]
    fn renders_png() {
        let Ok(renderer) = Renderer::new(Path::new(&std::env::var("DIC_FONTS").unwrap_or("/opt/dic/fonts".into())))
        else {
            eprintln!("skipped: set DIC_FONTS to the font directory");
            return;
        };
        let card = Card {
            title: "आजको शब्द".into(),
            paragraphs: vec![("ना.".into(), "दिनदिनै नेपाली बृहत शब्दकोशबाट एउटा नयाँ शब्द।".into())],
            footer: "illegal-in-nepal.org  ·  शब्दकोश".into(),
            tagged: true,
        };
        {
            let mut guard = renderer.fonts.lock().unwrap();
            let (fonts, cache) = &mut *guard;
            let mut pen = Pen { fonts, cache, canvas: Canvas::new() };
            // Widths from PIL with libraqm.
            assert!((pen.width("वा वा", &renderer.serif, 44.0) - 87.47).abs() < 0.1);
            assert!((pen.width("मुद्रित वा लेखिएको", &renderer.serif, 44.0) - 295.73).abs() < 0.1);
        }
        let png = renderer.render(&card);
        assert!(png.starts_with(b"\x89PNG"));
        if let Ok(out) = std::env::var("OG_SAMPLE") {
            std::fs::write(out, png).unwrap();
        }
    }
}
