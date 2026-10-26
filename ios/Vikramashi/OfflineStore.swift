//! The offline dictionary: a SQLite file made by shabdakosh/app_db.py, which
//! the app ships with and updates. Search, entries and the word of the day
//! work from it exactly as the service (dic/) does from the site's data.

import CryptoKit
import Foundation
import SQLite3

actor OfflineStore {
    static let schema = 2

    enum Failure: LocalizedError {
        case open(String)
        case schema(String)
        case update(String)

        var errorDescription: String? {
            switch self {
            case .open(let message): "शब्दकोश खोल्न सकिएन: \(message)"
            case .schema(let found): "यो एपले शब्दकोशको संस्करण \(found) पढ्न सक्दैन।"
            case .update(let message): "शब्दकोश अद्यावधिक गर्न सकिएन: \(message)"
            }
        }
    }

    /// Closes the database when the store goes away.
    private final class Connection: @unchecked Sendable {
        let db: OpaquePointer

        init(_ db: OpaquePointer) {
            self.db = db
        }

        deinit {
            sqlite3_close(db)
        }
    }

    nonisolated let version: String
    nonisolated let count: Int
    private let connection: Connection
    private var db: OpaquePointer { connection.db }
    private var index: SearchIndex?
    private var lexicon: CrosswordLexicon?

    /// Opens a dictionary read-only. Files are replaced, never changed in
    /// place, so SQLite may treat them as immutable.
    init(_ url: URL) throws {
        let handle = try Self.open(url, flags: SQLITE_OPEN_READONLY, immutable: true)
        func meta(_ key: String) -> String? {
            Self.rows(handle, "SELECT value FROM meta WHERE key = ?", [key]) { Self.text($0, 0) }.first
        }
        guard let schema = meta("schema"), schema == String(Self.schema) else {
            let found = meta("schema") ?? "?"
            sqlite3_close(handle)
            throw Failure.schema(found)
        }
        connection = Connection(handle)
        version = meta("version") ?? "?"
        count = Int(meta("entries") ?? "") ?? 0
    }

    private static func open(_ url: URL, flags: Int32, immutable: Bool) throws -> OpaquePointer {
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        if immutable {
            components.queryItems = [URLQueryItem(name: "immutable", value: "1")]
        }
        var handle: OpaquePointer?
        guard sqlite3_open_v2(components.url!.absoluteString, &handle, flags | SQLITE_OPEN_URI | SQLITE_OPEN_NOMUTEX,
                              nil) == SQLITE_OK,
              let handle
        else {
            let message = handle.map { String(cString: sqlite3_errmsg($0)) } ?? "?"
            sqlite3_close(handle)
            throw Failure.open(message)
        }
        return handle
    }

    /// Ordered lists an update splices (app_db.LISTS), with their columns.
    private static let lists = [("search", "word, slug"), ("wotd", "word, slug"), ("crossword", "word, clue")]

    /// Applies an update from app_db.py to the dictionary at `url`, in place,
    /// as app_db.apply does: the caller works on a copy and swaps it in.
    /// Returns the version it brings the dictionary to.
    static func apply(_ update: URL, to url: URL) throws -> String {
        let db = try open(url, flags: SQLITE_OPEN_READWRITE, immutable: false)
        defer { sqlite3_close(db) }
        func run(_ sql: String, _ bindings: [String] = []) throws {
            var statement: OpaquePointer?
            guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK, let statement else {
                throw Failure.update(String(cString: sqlite3_errmsg(db)))
            }
            defer { sqlite3_finalize(statement) }
            let transient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
            for (i, value) in bindings.enumerated() {
                sqlite3_bind_text(statement, Int32(i + 1), value, -1, transient)
            }
            guard sqlite3_step(statement) == SQLITE_DONE else { throw Failure.update(String(cString: sqlite3_errmsg(db))) }
        }
        func meta(_ table: String) -> [String: String] {
            Dictionary(Self.rows(db, "SELECT key, value FROM \(table)", []) { (Self.text($0, 0), Self.text($0, 1)) },
                       uniquingKeysWith: { $1 })
        }

        try run("ATTACH DATABASE ? AS u", [update.path])
        let ours = meta("main.meta"), theirs = meta("u.meta")
        guard theirs["schema"] == String(schema), let version = theirs["version"], let base = theirs["base"],
              base == ours["version"]
        else {
            throw Failure.update("\(theirs["base"] ?? "?") ≠ \(ours["version"] ?? "?")")
        }
        try run("BEGIN")
        do {
            try run("DELETE FROM entries WHERE slug IN (SELECT slug FROM u.removed)")
            try run("INSERT OR REPLACE INTO entries SELECT * FROM u.entries")
            for (table, cols) in lists {
                let range = (theirs[table] ?? "").split(separator: ":").map(String.init)
                guard range.count == 2 else { continue }
                try run("CREATE TEMP TABLE spliced(id INTEGER PRIMARY KEY, \(cols))")
                try run("INSERT INTO spliced(\(cols)) SELECT \(cols) FROM main.\(table) WHERE id < ? ORDER BY id",
                        [range[0]])
                try run("INSERT INTO spliced(\(cols)) SELECT \(cols) FROM u.\(table) ORDER BY id")
                try run("INSERT INTO spliced(\(cols)) SELECT \(cols) FROM main.\(table) WHERE id >= ? ORDER BY id",
                        [range[1]])
                try run("DELETE FROM main.\(table)")
                try run("INSERT INTO main.\(table) SELECT * FROM spliced")
                try run("DROP TABLE spliced")
            }
            try run("UPDATE main.meta SET value = ? WHERE key = 'version'", [version])
            try run("UPDATE main.meta SET value = ? WHERE key = 'entries'", [theirs["entries"] ?? ""])
            try run("COMMIT")
        } catch {
            try? run("ROLLBACK")
            throw error
        }
        try run("DETACH DATABASE u")
        return version
    }

    /// Whether the file reads back whole; for downloads, before they replace
    /// the dictionary in use.
    func isIntact() -> Bool {
        Self.rows(db, "PRAGMA quick_check", []) { Self.text($0, 0) } == ["ok"]
    }

    // MARK: Entries

    func entry(_ slug: String) -> WordPage? {
        Self.rows(db, "SELECT word, body FROM entries WHERE slug = ?", [slug]) { row in
            WordPage(word: Self.text(row, 0), body: Self.text(row, 1))
        }.first ?? nil
    }

    // MARK: Word of the day

    /// The day's word, picked like wotd_lib.pick_for_day: the entry at
    /// sha256(day) mod n, reading the digest as a big-endian integer.
    func wordOfDay(_ day: String) -> WordOfDay? {
        let n = UInt64(Self.rows(db, "SELECT count(*) FROM wotd", []) { sqlite3_column_int64($0, 0) }.first ?? 0)
        guard n > 0 else { return nil }
        let index = SHA256.hash(data: Data(day.utf8)).reduce(UInt64(0)) { ($0 * 256 + UInt64($1)) % n }
        let sql = """
            SELECT wotd.word, entries.preview, wotd.slug FROM wotd LEFT JOIN entries USING (slug) WHERE wotd.id = ?
            """
        return Self.rows(db, sql, [String(index + 1)]) { row in
            // wotd_lib.first_sense: the first sense, without its number.
            WordOfDay(day: day, word: Self.text(row, 0), sense: Self.text(row, 1).withoutSenseNumber,
                      slug: Self.text(row, 2))
        }.first
    }

    // MARK: Crossword

    /// The crossword lexicon's [word, clue] rows, in order; loaded once.
    func crosswordLexicon() -> CrosswordLexicon {
        if let lexicon { return lexicon }
        let rows = Self.rows(db, "SELECT word, clue FROM crossword ORDER BY id", []) { (Self.text($0, 0), Self.text($0, 1)) }
        let lexicon = CrosswordLexicon(rows)
        self.lexicon = lexicon
        return lexicon
    }

    /// The puzzle for a Nepal day, YYYY-MM-DD.
    func crossword(_ day: String) -> Puzzle? {
        crosswordLexicon().puzzle(for: day)
    }

    // MARK: Search

    /// Up to 20 entries for `query`, ranked as dic/src/search.rs ranks them.
    func search(_ query: String) -> [Entry] {
        let index = prepareSearch()
        return index.search(SearchIndex.normalize(query))
    }

    /// Loads the search list; done once, ahead of the first search.
    @discardableResult
    func prepareSearch() -> SearchIndex {
        if let index { return index }
        let sql = """
            SELECT search.word, search.slug, entries.grammar, entries.preview
            FROM search JOIN entries USING (slug) ORDER BY search.id
            """
        let rows = Self.rows(db, sql, []) { row in
            Entry(word: Self.text(row, 0), slug: Self.text(row, 1), grammar: Self.text(row, 2), preview: Self.text(row, 3))
        }
        let index = SearchIndex(rows)
        self.index = index
        return index
    }

    // MARK: SQLite

    private static func text(_ row: OpaquePointer, _ column: Int32) -> String {
        sqlite3_column_text(row, column).map { String(cString: $0) } ?? ""
    }

    private static func rows<T>(_ db: OpaquePointer, _ sql: String, _ bindings: [String],
                                _ read: (OpaquePointer) -> T) -> [T] {
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK, let statement else { return [] }
        defer { sqlite3_finalize(statement) }
        let transient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
        for (i, value) in bindings.enumerated() {
            sqlite3_bind_text(statement, Int32(i + 1), value, -1, transient)
        }
        var out: [T] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            out.append(read(statement))
        }
        return out
    }
}

extension WordPage {
    /// An entry's body as app_db.py stores it: [[grammar, [sense, ...]], ...],
    /// each sense a list of [text] or [text, slug], slug "" meaning the text.
    init?(word: String, body: String) {
        guard let blocks = try? JSONSerialization.jsonObject(with: Data(body.utf8)) as? [[Any]] else { return nil }
        self.init(word: word, blocks: blocks.compactMap { block in
            guard block.count == 2, let grammar = block[0] as? String, let senses = block[1] as? [[[String]]] else {
                return nil
            }
            return Block(grammar: grammar, senses: senses.map { sense in
                sense.compactMap { run in
                    guard let text = run.first else { return nil }
                    let slug = run.count > 1 ? (run[1].isEmpty ? text : run[1]) : nil
                    return Span(text: text, slug: slug)
                }
            })
        })
    }
}

/// dic/src/search.rs, scalar for scalar: the same folding, edit distances and
/// tiers, so the app finds what the site finds.
struct SearchIndex: Sendable {
    private static let limit = 20

    private let entries: [Entry]
    private let words: [[UInt8]]
    private let loose: [[Unicode.Scalar]]
    private let previews: [[UInt8]]

    init(_ entries: [Entry]) {
        self.entries = entries
        words = entries.map { Array(Self.normalize($0.word).utf8) }
        loose = entries.map { Self.loosen(Self.normalize($0.word)) }
        previews = entries.map { Array(Self.normalize($0.preview).utf8) }
    }

    static func normalize(_ s: String) -> String {
        s.trimmingCharacters(in: .whitespacesAndNewlines).precomposedStringWithCanonicalMapping.lowercased()
    }

    /// Folds spellings commonly confused when typing Nepali, including
    /// conjuncts typed without the halant.
    static func loosen(_ s: String) -> [Unicode.Scalar] {
        s.unicodeScalars.compactMap { c in
            switch c {
            case "\u{093C}", "\u{094D}", "\u{200C}", "\u{200D}": nil
            case "ी": "ि"
            case "ू": "ु"
            case "ई": "इ"
            case "ऊ": "उ"
            case "ँ": "ं"
            case "श", "ष": "स"
            case "व": "ब"
            case "ण": "न"
            default: c
            }
        }
    }

    /// Edits allowed between a query of `length` characters and a word.
    private static func maxEdits(_ length: Int) -> Int {
        switch length {
        case 0...2: 0
        case 3...4: 1
        case 5...8: 2
        default: 3
        }
    }

    /// Levenshtein distance from `q` to all of `w` and to its closest prefix,
    /// or nil if both exceed `k`.
    private static func distances(_ q: [Unicode.Scalar], _ w: [Unicode.Scalar], _ k: Int) -> (full: Int, prefix: Int)? {
        if w.count + k < q.count { return nil }
        var row = Array(0...w.count)
        for (i, qc) in q.enumerated() {
            var diagonal = row[0]
            row[0] = i + 1
            var smallest = row[0]
            for (j, wc) in w.enumerated() {
                let above = row[j + 1]
                row[j + 1] = min(diagonal + (qc == wc ? 0 : 1), above + 1, row[j] + 1)
                diagonal = above
                smallest = min(smallest, row[j + 1])
            }
            if smallest > k { return nil }
        }
        let prefix = row.min()!
        return prefix <= k ? (row[w.count], prefix) : nil
    }

    private static func contains(_ haystack: [UInt8], _ needle: [UInt8]) -> Bool {
        guard !needle.isEmpty else { return true }
        guard haystack.count >= needle.count else { return false }
        return haystack.withUnsafeBytes { h in
            needle.withUnsafeBytes { n in
                memmem(h.baseAddress, h.count, n.baseAddress, n.count) != nil
            }
        }
    }

    /// Ranks, best first: the exact word; the word up to folded spelling;
    /// words starting with the query, exactly then up to folding; words a few
    /// edits away; words containing the query; words whose beginning is a few
    /// edits away; definitions containing the query. Shorter words first.
    /// `query` must already be normalized.
    func search(_ query: String) -> [Entry] {
        guard !query.isEmpty else { return [] }
        let q = Array(query.utf8)
        let looseQuery = Self.loosen(query)
        let k = Self.maxEdits(looseQuery.count)
        var hits: [(tier: Int, edits: Int, length: Int, i: Int)] = []
        for i in entries.indices {
            let word = words[i]
            let fuzzy = Self.distances(looseQuery, loose[i], k)
            let tier: Int, edits: Int
            if word == q {
                (tier, edits) = (0, 0)
            } else if let fuzzy, fuzzy.full == 0 {
                (tier, edits) = (1, 0)
            } else if word.starts(with: q) {
                (tier, edits) = (2, 0)
            } else if let fuzzy, fuzzy.prefix == 0 {
                (tier, edits) = (3, 0)
            } else if let fuzzy, fuzzy.full <= k {
                (tier, edits) = (4, fuzzy.full)
            } else if Self.contains(word, q) {
                (tier, edits) = (5, 0)
            } else if let fuzzy {
                (tier, edits) = (6, fuzzy.prefix)
            } else if Self.contains(previews[i], q) {
                (tier, edits) = (7, 0)
            } else {
                continue
            }
            hits.append((tier, edits, loose[i].count, i))
        }
        hits.sort { ($0.tier, $0.edits, $0.length, $0.i) < ($1.tier, $1.edits, $1.length, $1.i) }
        return hits.prefix(Self.limit).map { entries[$0.i] }
    }
}
