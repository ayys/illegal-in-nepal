//! Word of the day, picked the same way as wotd_lib.pick_for_day.

use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Nepal is UTC+5:45 all year.
const NEPAL_OFFSET: u64 = 5 * 3600 + 45 * 60;
const DAY: u64 = 86_400;

/// One row of wotd.json.gz: word, first sense, page slug.
#[derive(Deserialize)]
pub struct Entry(String, String, String);

#[derive(Serialize)]
pub struct Pick<'a> {
    pub day: &'a str,
    pub word: &'a str,
    pub sense: &'a str,
    pub slug: &'a str,
}

pub fn parse(json: &str) -> serde_json::Result<Vec<Entry>> {
    serde_json::from_str(json)
}

/// The entry at sha256(day) mod n, reading the digest as a big-endian integer.
pub fn pick<'a>(entries: &'a [Entry], day: &'a str) -> Option<Pick<'a>> {
    let n = entries.len() as u128;
    if n == 0 {
        return None;
    }
    let index = Sha256::digest(day.as_bytes()).iter().fold(0u128, |r, &b| (r * 256 + b as u128) % n);
    let Entry(word, sense, slug) = &entries[index as usize];
    Some(Pick { day, word, sense, slug })
}

fn nepal_seconds() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).expect("clock after 1970").as_secs() + NEPAL_OFFSET
}

/// Today's date in Nepal as YYYY-MM-DD.
pub fn today() -> String {
    let days = (nepal_seconds() / DAY) as i64;
    // Civil-from-days, after Howard Hinnant's date algorithms.
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = doy - (153 * mp + 2) / 5 + 1;
    let month = if mp < 10 { mp + 3 } else { mp - 9 };
    let year = yoe + era * 400 + i64::from(month <= 2);
    format!("{year:04}-{month:02}-{day:02}")
}

/// Seconds until the date changes in Nepal.
pub fn until_tomorrow() -> u64 {
    DAY - nepal_seconds() % DAY
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn picks_like_python() {
        // int(hashlib.sha256(day.encode()).hexdigest(), 16) % n
        let entries: Vec<Entry> =
            (0..104_729).map(|i| Entry(i.to_string(), String::new(), String::new())).collect();
        assert_eq!(pick(&entries, "2026-10-14").unwrap().word, "35989");
        assert_eq!(pick(&entries, "2027-01-01").unwrap().word, "78356");
        assert_eq!(pick(&entries[..7], "2026-10-14").unwrap().word, "0");
    }

    #[test]
    fn today_is_a_date() {
        let day = today();
        assert_eq!(day.len(), 10);
        assert!(day.starts_with("20"));
    }
}
