//! Nepali (Romanized) - Pro, the macOS layout by Suvash Thapaliya
//! (github.com/suvash/nepali-romanized-pro), folded onto a phone: the keys
//! keep their QWERTY places, three rows of eleven.

import Foundation

enum NepaliLayout {
    enum Layer {
        /// No modifier.
        case plain
        /// Shift.
        case shift
        /// Caps lock: conjuncts, and Latin digits.
        case caps
    }

    /// QWERTY positions, as the rows appear on the phone.
    static let rows: [[Character]] = [
        ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "["],
        ["a", "s", "d", "f", "g", "h", "j", "k", "l", "]", "\\"],
        ["z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "`"],
    ]

    private static let plain: [Character: String] = [
        "`": "ऽ", "1": "१", "2": "२", "3": "३", "4": "४", "5": "५", "6": "६", "7": "७", "8": "८", "9": "९", "0": "०",
        "q": "ट", "w": "ौ", "e": "े", "r": "र", "t": "त", "y": "य", "u": "ु", "i": "ि", "o": "ो", "p": "प",
        "[": "इ", "]": "ए", "\\": "ॐ",
        "a": "ा", "s": "स", "d": "द", "f": "उ", "g": "ग", "h": "ह", "j": "ज", "k": "क", "l": "ल",
        "z": "ष", "x": "ड", "c": "च", "v": "व", "b": "ब", "n": "न", "m": "म", ",": ",", ".": "।", "/": "्",
    ]

    private static let shift: [Character: String] = [
        "`": "़",
        "q": "ठ", "w": "औ", "e": "ै", "r": "ृ", "t": "थ", "y": "ञ", "u": "ू", "i": "ी", "o": "ओ", "p": "फ",
        "[": "ई", "]": "ऐ", "\\": "ः",
        "a": "आ", "s": "श", "d": "ध", "f": "ऊ", "g": "घ", "h": "अ", "j": "झ", "k": "ख", "l": "ळ",
        "z": "ऋ", "x": "ढ", "c": "छ", "v": "ँ", "b": "भ", "n": "ण", "m": "ं", ",": "ङ", ".": "॥", "/": "?",
    ]

    /// Only the keys that differ from `plain`.
    private static let caps: [Character: String] = [
        "`": "ऱ्", "q": "ट्ट", "r": "त्र", "t": "त्त",
        "s": "श्र", "d": "द्ध", "f": "द्व", "g": "द्य", "j": "ज्ञ", "k": "क्ष", ".": "॰",
    ]

    static func output(_ key: Character, _ layer: Layer) -> String {
        switch layer {
        case .plain: plain[key] ?? ""
        case .shift: shift[key] ?? ""
        case .caps: caps[key] ?? plain[key] ?? ""
        }
    }

    /// The second page: digits and punctuation from the layout's other keys.
    static let symbols: [[String]] = [
        ["१", "२", "३", "४", "५", "६", "७", "८", "९", "०"],
        ["-", "/", ":", ";", "(", ")", "रू.", "&", "@", "\""],
        ["।", "॥", ",", ".", "?", "!", "'", "%", "ऽ", "॰"],
    ]

    /// Whether `text` is a sign that joins the letter before it, so its key
    /// shows it on a dotted circle.
    static func isMark(_ text: String) -> Bool {
        guard let scalar = text.unicodeScalars.first, text.unicodeScalars.count == 1 else { return false }
        return [.nonspacingMark, .spacingMark].contains(scalar.properties.generalCategory)
    }

    static func label(_ text: String) -> String {
        isMark(text) ? "◌" + text : text
    }
}
