//! The site's look: warm paper, brown ink, a rust accent, Tiro Devanagari
//! for words and Kalam for the odd hand-lettered label (site/common.css).

import CoreText
import SwiftUI

extension ShapeStyle where Self == Color {
    static var paper: Color { Color("Paper") }
    static var card: Color { Color("Card") }
    static var wash: Color { Color("Wash") }
    static var ink: Color { Color("Ink") }
    static var mute: Color { Color("Mute") }
    static var rule: Color { Color("Rule") }
    static var rust: Color { Color("AccentColor") }
    static var block: Color { Color("Block") }
}

extension Int {
    /// In Devanagari digits: 25 → "२५".
    var nepali: String {
        String(String(self).map { digit in
            digit.wholeNumberValue.map { Character(Unicode.Scalar(0x0966 + $0)!) } ?? digit
        })
    }
}

extension Font {
    /// Tiro Devanagari Hindi, scaling with Dynamic Type like `style`.
    static func serif(_ size: CGFloat, relativeTo style: TextStyle = .body) -> Font {
        .custom("TiroDevaHindi-Regular", size: size, relativeTo: style)
    }

    static func hand(_ size: CGFloat, relativeTo style: TextStyle = .caption) -> Font {
        .custom("Kalam-Bold", size: size, relativeTo: style)
    }
}

@MainActor
enum Theme {
    /// Makes the bundled fonts available to Font.custom and sets navigation
    /// titles in the serif, which SwiftUI has no modifier for.
    static func setUp() {
        for url in Bundle.main.urls(forResourcesWithExtension: "ttf", subdirectory: nil) ?? [] {
            CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
        }
        #if canImport(UIKit)
        guard let ink = UIColor(named: "Ink"),
              let large = UIFont(name: "TiroDevaHindi-Regular", size: 38),
              let inline = UIFont(name: "TiroDevaHindi-Regular", size: 20)
        else { return }
        let bar = UINavigationBar.appearance()
        bar.largeTitleTextAttributes = [
            .font: UIFontMetrics(forTextStyle: .largeTitle).scaledFont(for: large), .foregroundColor: ink,
        ]
        bar.titleTextAttributes = [
            .font: UIFontMetrics(forTextStyle: .headline).scaledFont(for: inline), .foregroundColor: ink,
        ]
        #endif
    }
}

/// Grammar abbreviations spelled out, from the सङ्केतसूची of नेपाली बृहत्
/// शब्दकोश. The data writes them without spaces ("अक्रि." for "अ. क्रि.").
enum Grammar {
    private static let names = [
        "ना.": "नाम", "वि.": "विशेषण", "सर्व.": "सर्वनाम",
        "क्रि.": "क्रिया", "अक्रि.": "अकर्मक क्रिया", "सक्रि.": "सकर्मक क्रिया",
        "कक्रि.": "कर्मवाच्य क्रिया", "प्रेक्रि.": "प्रेरणार्थक क्रिया", "क्रिप.": "क्रिया-पदावली",
        "क्रिवि.": "क्रियाविशेषण", "विबो.": "विस्मयादिबोधक", "नायो.": "नामयोगी",
        "संयो.": "संयोजक", "निपा.": "निपात", "उप.": "उपसर्ग", "विभ.": "विभक्ति",
        "अव्य.": "अव्यय", "पस.": "परसर्ग", "पूस.": "पूर्वसर्ग",
    ]

    /// "वि./ ना." → "विशेषण / नाम"; tags not in the list stay abbreviated.
    static func name(_ tag: String) -> String {
        tag.split(separator: "/")
            .map { part in
                let part = part.trimmingCharacters(in: .whitespaces)
                return names[part.replacingOccurrences(of: " ", with: "")] ?? part
            }
            .joined(separator: " / ")
    }
}

/// A small rounded label, like the site's chips.
struct Chip: View {
    let text: String

    init(_ text: String) {
        self.text = text
    }

    var body: some View {
        Text(text)
            .font(.footnote.weight(.semibold))
            .foregroundStyle(.rust)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(.rust.opacity(0.1), in: Capsule())
    }
}

/// A small-caps style section heading.
struct SectionLabel: View {
    let text: String

    init(_ text: String) {
        self.text = text
    }

    var body: some View {
        Text(text)
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(.mute)
    }
}
