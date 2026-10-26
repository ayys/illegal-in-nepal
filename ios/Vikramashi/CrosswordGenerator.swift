//! The daily crossword, made on the phone: dic/src/crossword.rs draw for
//! draw (itself a port of crossword.js), so the app's puzzle for a day is the
//! site's, and progress saved by day and cell stays valid. Keep every draw
//! from the generator in the same order.

import CryptoKit
import Foundation

/// The crossword lexicon, indexed for building puzzles.
struct CrosswordLexicon: Sendable {
    // Keep these and akshars in sync with dic/src/crossword.rs.
    static let size = 7
    private static let minLength = 3
    private static let minWords = 6
    private static let targetWords = 10
    private static let maxAttempts = 50

    fileprivate struct Entry: Sendable {
        let word: String
        let clue: String
        let cells: [String]
    }

    fileprivate let entries: [Entry]
    fileprivate let byKey: [String: [Int]]
    fileprivate let starters: [Int]

    var count: Int { entries.count }

    /// Rows of crossword.json.gz: [word, clue].
    init(_ rows: [(String, String)]) {
        var entries: [Entry] = []
        var byKey: [String: [Int]] = [:]
        var starters: [Int] = []
        for (word, clue) in rows {
            guard let cells = Self.akshars(word), (Self.minLength...Self.size).contains(cells.count) else { continue }
            let id = entries.count
            if cells.count == 4 || cells.count == 5 {
                starters.append(id)
            }
            for (i, a) in cells.enumerated() {
                byKey[Self.key(cells.count, i, a), default: []].append(id)
            }
            entries.append(Entry(word: word, clue: clue, cells: cells))
        }
        self.entries = entries
        self.byKey = byKey
        self.starters = starters
    }

    fileprivate static func key(_ length: Int, _ i: Int, _ akshar: String) -> String {
        "\(length):\(i):\(akshar)"
    }

    /// Split into cells: an independent vowel, or a consonant with an
    /// optional vowel sign, then an optional chandrabindu / anusvara /
    /// visarga. Nil if anything else (e.g. a conjunct) is in the word.
    static func akshars(_ word: String) -> [String]? {
        let scalars = Array(word.precomposedStringWithCanonicalMapping.unicodeScalars)
        func within(_ i: Int, _ lo: UInt32, _ hi: UInt32) -> Bool {
            i < scalars.count && (lo...hi).contains(scalars[i].value)
        }
        var cells: [String] = []
        var i = 0
        while i < scalars.count {
            let start = i
            if within(i, 0x0905, 0x0914) {
                i += 1
            } else if within(i, 0x0915, 0x0939) {
                i += 1
                if within(i, 0x093E, 0x094C) {
                    i += 1
                }
            } else {
                return nil
            }
            if within(i, 0x0901, 0x0903) {
                i += 1
            }
            var cell = String.UnicodeScalarView()
            cell.append(contentsOf: scalars[start..<i])
            cells.append(String(cell))
        }
        return cells.isEmpty ? nil : cells
    }

    /// The puzzle for a Nepal day, YYYY-MM-DD.
    func puzzle(for day: String) -> Puzzle? {
        guard !starters.isEmpty else { return nil }
        for attempt in 0..<Self.maxAttempts {
            var rand = Rand(attempt == 0 ? day : "\(day)#\(attempt)")
            if let puzzle = build(day, &rand) {
                return puzzle
            }
        }
        return nil
    }

    private func build(_ day: String, _ rand: inout Rand) -> Puzzle? {
        var board = Board(lexicon: self)
        let first = starters[rand.below(starters.count)]
        let length = entries[first].cells.count
        board.place(first, Self.size / 2, (Self.size - length) / 2, .across)

        while board.placed.count < Self.targetWords {
            var seen = Set<Slot>()
            var options: [Slot] = []
            for w in board.placed {
                let (dr, dc) = w.dir.step
                let dir = w.dir.other
                let (nr, nc) = dir.step
                for i in 0..<entries[w.entry].cells.count {
                    for length in Self.minLength...Self.size {
                        for k in 0..<length {
                            let slot = Slot(row: w.row + dr * i - nr * k, col: w.col + dc * i - nc * k, dir: dir,
                                            length: length)
                            if seen.insert(slot).inserted {
                                options.append(slot)
                            }
                        }
                    }
                }
            }
            rand.shuffle(&options)
            var found: (Slot, Int)?
            for slot in options {
                if let id = board.candidate(slot, &rand) {
                    found = (slot, id)
                    break
                }
            }
            guard let (slot, id) = found else { break }
            board.place(id, slot.row, slot.col, slot.dir)
        }

        let across = board.placed.filter { $0.dir == .across }.count
        guard board.placed.count >= Self.minWords, across >= 2, board.placed.count - across >= 2 else { return nil }

        let starts = Array(Set(board.placed.map { $0.row * Self.size + $0.col })).sorted()
        let words = board.placed.map { w in
            let entry = entries[w.entry]
            return Puzzle.Word(number: starts.firstIndex(of: w.row * Self.size + w.col)! + 1, dir: w.dir.direction,
                               row: w.row, col: w.col, word: entry.word, clue: entry.clue, cells: entry.cells)
        }
        .sorted { ($0.dir == .across ? 0 : 1, $0.number) < ($1.dir == .across ? 0 : 1, $1.number) }
        return Puzzle(day: day, size: Self.size, grid: board.grid, words: words)
    }
}

/// sfc32, seeded from the first 16 bytes of a SHA-256 digest.
private struct Rand {
    private var a, b, c, d: UInt32

    init(_ seed: String) {
        let digest = Array(SHA256.hash(data: Data(seed.utf8)))
        func word(_ i: Int) -> UInt32 {
            digest[i * 4..<i * 4 + 4].reduce(0) { $0 << 8 | UInt32($1) }
        }
        (a, b, c, d) = (word(0), word(1), word(2), word(3))
    }

    mutating func next() -> Double {
        let t = a &+ b &+ d
        d = d &+ 1
        a = b ^ (b >> 9)
        b = c &+ (c << 3)
        c = ((c << 21) | (c >> 11)) &+ t
        return Double(t) / 4_294_967_296
    }

    /// Math.floor(rand() * n)
    mutating func below(_ n: Int) -> Int {
        Int((next() * Double(n)).rounded(.down))
    }

    mutating func shuffle<T>(_ list: inout [T]) {
        guard list.count > 1 else { return }
        for i in stride(from: list.count - 1, through: 1, by: -1) {
            list.swapAt(i, below(i + 1))
        }
    }
}

private enum Dir: Int, Hashable {
    case across = 0, down = 1

    var step: (Int, Int) { self == .across ? (0, 1) : (1, 0) }
    var other: Dir { self == .across ? .down : .across }
    var direction: Puzzle.Direction { self == .across ? .across : .down }
}

private struct Slot: Hashable {
    let row: Int
    let col: Int
    let dir: Dir
    let length: Int
}

private struct Board {
    struct Placed {
        let entry: Int
        let row: Int
        let col: Int
        let dir: Dir
    }

    let lexicon: CrosswordLexicon
    var grid: [[String?]]
    var taken: [[[Bool]]]
    var placed: [Placed] = []
    /// Words already in the grid, compared as bytes, as in Rust.
    var used: Set<[UInt8]> = []

    init(lexicon: CrosswordLexicon) {
        self.lexicon = lexicon
        let size = CrosswordLexicon.size
        grid = Array(repeating: Array(repeating: nil, count: size), count: size)
        taken = Array(repeating: Array(repeating: [false, false], count: size), count: size)
    }

    private static func inside(_ r: Int, _ c: Int) -> Bool {
        r >= 0 && c >= 0 && r < CrosswordLexicon.size && c < CrosswordLexicon.size
    }

    private func at(_ r: Int, _ c: Int) -> String? {
        Self.inside(r, c) ? grid[r][c] : nil
    }

    mutating func place(_ id: Int, _ row: Int, _ col: Int, _ dir: Dir) {
        let entry = lexicon.entries[id]
        let (dr, dc) = dir.step
        for (i, a) in entry.cells.enumerated() {
            let (r, c) = (row + dr * i, col + dc * i)
            grid[r][c] = a
            taken[r][c][dir.rawValue] = true
        }
        placed.append(Placed(entry: id, row: row, col: col, dir: dir))
        used.insert(Array(entry.word.utf8))
    }

    func candidate(_ slot: Slot, _ rand: inout Rand) -> Int? {
        let (row, col, dir, length) = (slot.row, slot.col, slot.dir, slot.length)
        let (dr, dc) = dir.step
        let endR = row + dr * (length - 1)
        let endC = col + dc * (length - 1)
        guard Self.inside(row, col), Self.inside(endR, endC) else { return nil }
        if at(row - dr, col - dc) != nil || at(endR + dr, endC + dc) != nil { return nil }

        var fixed: [(Int, String)] = []
        for i in 0..<length {
            let (r, c) = (row + dr * i, col + dc * i)
            if let a = grid[r][c] {
                if taken[r][c][dir.rawValue] { return nil }
                fixed.append((i, a))
            } else if at(r + dc, c + dr) != nil || at(r - dc, c - dr) != nil {
                return nil
            }
        }
        if fixed.isEmpty || fixed.count == length { return nil }

        var bucket: [Int]?
        for (i, a) in fixed {
            guard let list = lexicon.byKey[CrosswordLexicon.key(length, i, a)] else { return nil }
            if bucket == nil || list.count < bucket!.count {
                bucket = list
            }
        }
        guard let bucket else { return nil }
        let offset = rand.below(bucket.count)
        for k in 0..<bucket.count {
            let id = bucket[(offset + k) % bucket.count]
            let entry = lexicon.entries[id]
            if !used.contains(Array(entry.word.utf8)), fixed.allSatisfy({ entry.cells[$0.0] == $0.1 }) {
                return id
            }
        }
        return nil
    }
}
