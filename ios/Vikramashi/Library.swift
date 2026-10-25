import Foundation
import Observation

/// A word as it appears in lists: enough to show a row and open its page.
struct WordRef: Codable, Hashable, Identifiable, Sendable {
    let slug: String
    let word: String
    /// The first sense, as plain text.
    let gloss: String
    /// The first grammar tag, abbreviated.
    let grammar: String

    var id: String { slug }
    var route: WordRoute { WordRoute(slug: slug) }
}

/// Saved words and recently viewed ones, kept in UserDefaults.
@Observable
@MainActor
final class Library {
    private static let recentLimit = 30
    private let defaults: UserDefaults

    private(set) var saved: [WordRef] {
        didSet { store(saved, as: "saved") }
    }

    private(set) var recent: [WordRef] {
        didSet { store(recent, as: "recent") }
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        saved = Self.load("saved", from: defaults)
        recent = Self.load("recent", from: defaults)
    }

    func isSaved(_ slug: String) -> Bool {
        saved.contains { $0.slug == slug }
    }

    func toggleSaved(_ word: WordRef) {
        if isSaved(word.slug) {
            saved.removeAll { $0.slug == word.slug }
        } else {
            saved.insert(word, at: 0)
        }
    }

    func unsave(at offsets: IndexSet) {
        saved.remove(atOffsets: offsets)
    }

    func viewed(_ word: WordRef) {
        recent.removeAll { $0.slug == word.slug }
        recent.insert(word, at: 0)
        if recent.count > Self.recentLimit {
            recent.removeLast(recent.count - Self.recentLimit)
        }
    }

    func clearRecent() {
        recent = []
    }

    private func store(_ words: [WordRef], as key: String) {
        defaults.set(try? JSONEncoder().encode(words), forKey: key)
    }

    private static func load(_ key: String, from defaults: UserDefaults) -> [WordRef] {
        guard let data = defaults.data(forKey: key) else { return [] }
        return (try? JSONDecoder().decode([WordRef].self, from: data)) ?? []
    }
}
