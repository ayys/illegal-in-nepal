//! A dictionary entry as JSON, read from its page on the site.

use scraper::{ElementRef, Html, Node, Selector};
use serde::Serialize;

#[derive(Serialize)]
pub struct Entry {
    pub word: String,
    pub blocks: Vec<Block>,
}

#[derive(Serialize)]
pub struct Block {
    /// Empty when the page gives none.
    pub grammar: String,
    pub senses: Vec<Vec<Span>>,
}

/// A run of a sense's text; `slug` is set when it links to another entry.
#[derive(Serialize)]
pub struct Span {
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub slug: Option<String>,
}

/// A page name under /shabdakosh/, without .html.
pub fn valid(slug: &str) -> bool {
    !slug.is_empty() && !slug.starts_with('.') && !slug.contains(['/', '\\', '?', '#', '%'])
}

/// Reads a page written by shabdakosh/generator.py: an <h1>, then grammar
/// tags each followed by their senses, as og::parse_page also reads them.
/// None if the page has no senses.
pub fn parse(html: &str) -> Option<Entry> {
    let doc = Html::parse_document(html);
    let select = |s: &str| Selector::parse(s).expect("valid selector");
    let word = doc.select(&select("h1")).next()?.text().collect::<String>().trim().to_owned();
    let mut blocks: Vec<Block> = Vec::new();
    for el in doc.select(&select("span[class=\"gram-tag\"], p[class=\"main-definition\"]")) {
        if el.value().name() == "span" {
            let tag: String = el.text().collect();
            let grammar = tag.trim().trim_start_matches('[').trim_end_matches(']').to_owned();
            blocks.push(Block { grammar, senses: Vec::new() });
        } else {
            if blocks.is_empty() {
                blocks.push(Block { grammar: String::new(), senses: Vec::new() });
            }
            blocks.last_mut().unwrap().senses.push(spans(el));
        }
    }
    blocks.retain(|block| !block.senses.is_empty());
    (!blocks.is_empty()).then_some(Entry { word, blocks })
}

/// A sense's text, split where it links to other entries.
fn spans(sense: ElementRef) -> Vec<Span> {
    let mut out: Vec<Span> = Vec::new();
    for child in sense.children() {
        let (text, slug) = match child.value() {
            Node::Text(text) => (text.to_string(), None),
            Node::Element(el) => {
                let text = ElementRef::wrap(child).map(|el| el.text().collect()).unwrap_or_default();
                let slug = (el.name() == "a")
                    .then(|| el.attr("href"))
                    .flatten()
                    .and_then(|href| href.strip_prefix("./")?.strip_suffix(".html"))
                    .map(crate::percent_decode);
                (text, slug)
            }
            _ => continue,
        };
        if text.is_empty() {
            continue;
        }
        match out.last_mut() {
            Some(last) if last.slug.is_none() && slug.is_none() => last.text += &text,
            _ => out.push(Span { text, slug }),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn checks_slugs() {
        assert!(valid("घर") && valid("अँ-त"));
        assert!(!valid("") && !valid("../x") && !valid("a/b") && !valid(".hidden") && !valid("%2e%2e"));
    }

    #[test]
    fn parses_entries() {
        let html = r#"<h1>घर </h1><section>
            <div><span class="gram-tag">[ना.]</span></div>
            <p class="main-definition">१. <a href="./कुण्डली.html">कुण्डली</a>मा <b>ग्रह</b>का स्थान।</p>
            <p class="main-definition"><a href="./%E0%A4%96.html">ख</a></p>
            <div><span class="gram-tag">[वि.]</span></div></section>"#;
        let entry = parse(html).unwrap();
        assert_eq!(entry.word, "घर");
        assert_eq!(entry.blocks.len(), 1);
        assert_eq!(
            serde_json::to_string(&entry.blocks[0]).unwrap(),
            r#"{"grammar":"ना.","senses":[[{"text":"१. "},{"text":"कुण्डली","slug":"कुण्डली"},{"text":"मा ग्रहका स्थान।"}],[{"text":"ख","slug":"ख"}]]}"#
        );
        assert!(parse("<h1>Blog</h1><p>Not a dictionary page.</p>").is_none());
    }

    #[test]
    fn parses_site_page() {
        let Ok(html) = std::fs::read_to_string("../site/shabdakosh/घर.html") else {
            eprintln!("skipped: build the site first");
            return;
        };
        let entry = parse(&html).unwrap();
        assert_eq!(entry.word, "घर");
        assert_eq!(entry.blocks[0].grammar, "ना.");
        assert_eq!(entry.blocks[0].senses.len(), 5);
        assert!(entry.blocks[0].senses[0].iter().any(|span| span.slug.as_deref() == Some("कुण्डली")));
    }
}
