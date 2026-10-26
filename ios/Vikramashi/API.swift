//! The dictionary comes from the copy on the phone (Shabdakosh); only the
//! daily crossword comes from dic.illegal-in-nepal.org (the service in dic/).

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
    static let base = URL(string: "https://dic.illegal-in-nepal.org")!
    static let site = URL(string: "https://illegal-in-nepal.org")!

    enum Failure: LocalizedError {
        /// The service answers 503 until its data has loaded.
        case unavailable
        case status(Int)
        case notFound
        case noWordToday

        var errorDescription: String? {
            switch self {
            case .unavailable: "पहेली तयार हुँदैछ। केही बेरपछि फेरि प्रयास गर्नुहोस्।"
            case .status(let code): "सर्भरले \(code) फर्कायो।"
            case .notFound: "यो शब्द भेटिएन।"
            case .noWordToday: "आजको शब्द भेटिएन।"
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

    private static func dictionary() async throws -> OfflineStore {
        try await MainActor.run { try Shabdakosh.shared.ready() }
    }

    static func crossword() async throws -> Puzzle {
        try await get(base.appending(path: "crossword"))
    }

    private static func get<T: Decodable>(_ url: URL) async throws -> T {
        try JSONDecoder().decode(T.self, from: try await data(url))
    }

    /// The service sends Cache-Control, so URLSession's cache answers
    /// repeats; when the network fails, the last cached answer is used
    /// instead, however old.
    private static func data(_ url: URL) async throws -> Data {
        do {
            return try await fetch(URLRequest(url: url))
        } catch let error as URLError where error.code != .cancelled {
            guard let cached = try? await fetch(URLRequest(url: url, cachePolicy: .returnCacheDataDontLoad)) else {
                throw error
            }
            return cached
        }
    }

    private static func fetch(_ request: URLRequest) async throws -> Data {
        let (data, response) = try await URLSession.shared.data(for: request)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard status == 200 else { throw status == 503 ? Failure.unavailable : Failure.status(status) }
        return data
    }
}
