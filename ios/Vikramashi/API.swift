//! Everything comes from the dictionary on the phone (Shabdakosh): search,
//! entries, the word of the day and the daily crossword.

import Foundation

/// One search hit: a row of the site's search data.
struct Entry: Identifiable, Hashable, Sendable {
    let word: String
    /// Page name, without .html.
    let slug: String
    let grammar: String
    let preview: String

    var id: String { slug }
    var route: WordRoute { WordRoute(slug: slug) }
}

/// Today's word, picked as the site picks it.
struct WordOfDay: Hashable, Sendable {
    /// The Nepal day, YYYY-MM-DD.
    let day: String
    let word: String
    let sense: String
    /// Page name, without .html.
    let slug: String

    var route: WordRoute { WordRoute(slug: slug) }
}

enum API {
    /// The website, for sharing and reading a word there.
    static let site = URL(string: "https://illegal-in-nepal.org")!

    enum Failure: LocalizedError {
        case notFound
        case noWordToday
        case noPuzzleToday

        var errorDescription: String? {
            switch self {
            case .notFound: "यो शब्द भेटिएन।"
            case .noWordToday: "आजको शब्द भेटिएन।"
            case .noPuzzleToday: "आजको पहेली बन्न सकेन।"
            }
        }
    }

    static func search(_ query: String) async throws -> [Entry] {
        try await dictionary().search(query)
    }

    static func wordOfDay() async throws -> WordOfDay {
        guard let word = try await dictionary().wordOfDay(Nepal.today) else { throw Failure.noWordToday }
        return word
    }

    static func word(_ route: WordRoute) async throws -> WordPage {
        guard let page = try await dictionary().entry(route.slug) else { throw Failure.notFound }
        return page
    }

    /// Today's crossword, built from the dictionary's lexicon as the site builds it.
    static func crossword() async throws -> Puzzle {
        guard let puzzle = try await dictionary().crossword(Nepal.today) else { throw Failure.noPuzzleToday }
        return puzzle
    }

    private static func dictionary() async throws -> OfflineStore {
        try await MainActor.run { try Shabdakosh.shared.ready() }
    }
}
