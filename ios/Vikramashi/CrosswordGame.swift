//! The daily crossword's rules, as on the site (shabdakosh/आजको-वर्गपहेली.html
//! and crossword.js): one अक्षर per cell, a vowel sign typed next joins the
//! cell just filled, and scoring with the same points.

import Foundation
import Observation

/// Today's puzzle, as dic/src/crossword.rs serializes it.
struct Puzzle: Decodable, Sendable {
    enum Direction: String, Decodable, Sendable {
        case across, down

        var name: String { self == .across ? "तेर्सो" : "ठाडो" }
        var other: Direction { self == .across ? .down : .across }
    }

    struct Word: Decodable, Sendable {
        let number: Int
        let dir: Direction
        let row: Int
        let col: Int
        let word: String
        let clue: String
        /// The answer, one अक्षर per cell.
        let cells: [String]
    }

    /// The Nepal day, YYYY-MM-DD.
    let day: String
    let size: Int
    /// The answer in each open cell; nil for blocks.
    let grid: [[String?]]
    let words: [Word]
}

struct Cell: Hashable, Sendable {
    let r: Int
    let c: Int
}

@Observable
@MainActor
final class CrosswordGame {
    static let wordPoints = 10
    static let missCost = 2

    let puzzle: Puzzle
    private(set) var entries: [[String]]
    /// Words filled by "शब्द भर" or "उत्तर"; they earn nothing.
    private(set) var revealed: Set<Int> = []
    /// Each distinct wrong guess at a word, as "word:guess".
    private(set) var misses: Set<String> = []
    private(set) var active = 0
    private(set) var cursor: Cell
    /// Bumped when a key does nothing, for feedback.
    private(set) var rejected = 0
    /// The cursor's cell was just typed in: a vowel sign joins it and the
    /// next letter moves on.
    private var editing = false
    private let owners: [Cell: [Puzzle.Direction: Int]]
    private let defaults: UserDefaults

    init(puzzle: Puzzle, defaults: UserDefaults = .standard) {
        self.puzzle = puzzle
        self.defaults = defaults
        var owners: [Cell: [Puzzle.Direction: Int]] = [:]
        for (i, word) in puzzle.words.enumerated() {
            for cell in Self.cells(of: word) {
                owners[cell, default: [:]][word.dir] = i
            }
        }
        self.owners = owners
        entries = Array(repeating: Array(repeating: "", count: puzzle.size), count: puzzle.size)
        cursor = puzzle.words.first.map { Cell(r: $0.row, c: $0.col) } ?? Cell(r: 0, c: 0)
        load()
        active = clueOrder.contains(active) ? active : (clueOrder.first ?? 0)
        cursor = firstEmpty(active) ?? cells(active).first ?? cursor
    }

    // MARK: Reading the board

    private static func cells(of word: Puzzle.Word) -> [Cell] {
        word.cells.indices.map { i in
            word.dir == .across ? Cell(r: word.row, c: word.col + i) : Cell(r: word.row + i, c: word.col)
        }
    }

    func cells(_ word: Int) -> [Cell] {
        Self.cells(of: puzzle.words[word])
    }

    func entry(at cell: Cell) -> String {
        entries[cell.r][cell.c]
    }

    func isOpen(_ cell: Cell) -> Bool {
        puzzle.grid[cell.r][cell.c] != nil
    }

    func number(at cell: Cell) -> Int? {
        puzzle.words.first { $0.row == cell.r && $0.col == cell.c }?.number
    }

    func isFull(_ word: Int) -> Bool {
        cells(word).allSatisfy { !entry(at: $0).isEmpty }
    }

    func isRight(_ word: Int) -> Bool {
        cells(word).map(entry(at:)) == puzzle.words[word].cells
    }

    var solved: Bool {
        puzzle.words.indices.allSatisfy(isRight)
    }

    var maxScore: Int { puzzle.words.count * Self.wordPoints }

    var score: Int {
        max(0, maxScore - revealed.count * Self.wordPoints - misses.count * Self.missCost)
    }

    var activeWord: Puzzle.Word { puzzle.words[active] }

    var activeCells: Set<Cell> { Set(cells(active)) }

    /// Cells of a filled word that is wrong.
    var wrongCells: Set<Cell> {
        Set(puzzle.words.indices.filter { isFull($0) && !isRight($0) }.flatMap(cells))
    }

    var revealedCells: Set<Cell> {
        Set(revealed.flatMap(cells))
    }

    /// Rows and columns with an open cell, so all-block edges can be left out.
    var bounds: (rows: ClosedRange<Int>, cols: ClosedRange<Int>) {
        let open = puzzle.grid.indices.flatMap { r in puzzle.grid[r].indices.compactMap { c in puzzle.grid[r][c] == nil ? nil : Cell(r: r, c: c) } }
        let rows = open.map(\.r), cols = open.map(\.c)
        return ((rows.min() ?? 0)...(rows.max() ?? 0), (cols.min() ?? 0)...(cols.max() ?? 0))
    }

    /// Across clues, then down, as the site lists them.
    var clueOrder: [Int] {
        [Puzzle.Direction.across, .down].flatMap { dir in puzzle.words.indices.filter { puzzle.words[$0].dir == dir } }
    }

    private func firstEmpty(_ word: Int) -> Cell? {
        cells(word).first { entry(at: $0).isEmpty }
    }

    /// The next clue in `step` direction that still has an empty cell, or
    /// simply the next clue once the grid is full.
    private func nextWord(_ step: Int) -> Int {
        let order = clueOrder
        guard let at = order.firstIndex(of: active), order.count > 1 else { return active }
        let ahead = (1..<order.count).map { order[(at + step * $0 + order.count * order.count) % order.count] }
        return ahead.first { firstEmpty($0) != nil } ?? ahead[0]
    }

    // MARK: Moving

    /// Tapping the cursor's cell again turns to the other direction.
    func tap(_ cell: Cell) {
        guard isOpen(cell) else { return }
        if cell == cursor {
            toggleDirection()
            return
        }
        cursor = cell
        if !activeCells.contains(cell), let owned = owners[cell] {
            active = owned[activeWord.dir] ?? owned[activeWord.dir.other] ?? active
        }
        editing = false
        save()
    }

    func toggleDirection() {
        if let other = owners[cursor]?[activeWord.dir.other] {
            active = other
            editing = false
            save()
        }
    }

    func go(to word: Int) {
        active = word
        cursor = firstEmpty(word) ?? cells(word)[0]
        editing = false
        save()
    }

    func moveWord(_ step: Int) {
        go(to: nextWord(step))
    }

    // MARK: Typing

    /// A consonant or independent vowel: the cell just typed in stays put
    /// until the next letter, which moves on to the next empty cell.
    func type(_ letter: String) {
        if editing {
            advance()
        }
        set(cursor, letter)
        editing = true
    }

    /// A vowel sign or chandrabindu / anusvara / visarga, joined to the
    /// cursor's letter, or to the one before an empty cursor.
    func mark(_ mark: Unicode.Scalar) {
        var target = cursor
        if entry(at: cursor).isEmpty {
            let path = cells(active)
            if let i = path.firstIndex(of: cursor), i > 0 {
                target = path[i - 1]
            }
        }
        guard let joined = Self.join(mark, to: entry(at: target)) else {
            rejected += 1
            return
        }
        set(target, joined)
        cursor = target
        editing = true
    }

    /// Takes back the last keystroke in the cell being typed in; in an empty
    /// cell, clears the one before and moves there.
    func delete() {
        if !entry(at: cursor).isEmpty {
            if editing {
                var scalars = Array(entry(at: cursor).unicodeScalars)
                scalars.removeLast()
                set(cursor, String(String.UnicodeScalarView(scalars)))
            } else {
                set(cursor, "")
            }
            editing = !entry(at: cursor).isEmpty
            return
        }
        let path = cells(active)
        if let i = path.firstIndex(of: cursor), i > 0 {
            cursor = path[i - 1]
            set(cursor, "")
        }
        editing = false
    }

    private func advance() {
        let path = cells(active)
        let rest = path.drop { $0 != cursor }.dropFirst()
        if let next = rest.first(where: { entry(at: $0).isEmpty }) ?? rest.first {
            cursor = next
        } else {
            go(to: nextWord(1))
        }
    }

    /// A cell's letter with `mark` in its place: one vowel sign after a
    /// consonant, then one of ँ ं ः. Nil if the mark can't go there.
    static func join(_ mark: Unicode.Scalar, to akshar: String) -> String? {
        let scalars = Array(akshar.unicodeScalars)
        guard let base = scalars.first else { return nil }
        let isSign = (0x0901...0x0903).contains(mark.value)
        var vowelSign = scalars.dropFirst().first { (0x093E...0x094C).contains($0.value) }
        var sign = scalars.dropFirst().first { (0x0901...0x0903).contains($0.value) }
        if isSign {
            sign = mark
        } else {
            guard (0x0915...0x0939).contains(base.value) else { return nil }
            vowelSign = mark
        }
        return String(String.UnicodeScalarView([base] + [vowelSign, sign].compactMap { $0 }))
    }

    // MARK: Help

    /// "शब्द भर": fills the active word, which then earns nothing.
    func revealWord() {
        reveal(active)
        changed()
    }

    /// "उत्तर": fills every word.
    func revealAll() {
        puzzle.words.indices.forEach(reveal)
        changed()
    }

    /// "मेटाउ": empties the grid; points already lost stay lost.
    func clear() {
        entries = entries.map { $0.map { _ in "" } }
        go(to: clueOrder.first ?? 0)
        changed()
    }

    private func reveal(_ word: Int) {
        guard !isRight(word) else { return }
        for (cell, akshar) in zip(cells(word), puzzle.words[word].cells) {
            entries[cell.r][cell.c] = akshar
        }
        revealed.insert(word)
        editing = false
    }

    // MARK: Saving

    private func set(_ cell: Cell, _ value: String) {
        entries[cell.r][cell.c] = value
        changed()
    }

    private func changed() {
        for word in puzzle.words.indices where !revealed.contains(word) && isFull(word) && !isRight(word) {
            misses.insert("\(word):\(cells(word).map(entry(at:)).joined())")
        }
        save()
    }

    private struct Saved: Codable {
        var cells: [[String]]
        var revealed: [Int]
        var misses: [String]
        var active: Int
    }

    private var key: String { "vargapaheli:\(puzzle.day)" }

    private func save() {
        let saved = Saved(cells: entries, revealed: revealed.sorted(), misses: misses.sorted(), active: active)
        defaults.set(try? JSONEncoder().encode(saved), forKey: key)
    }

    private func load() {
        guard let data = defaults.data(forKey: key),
              let saved = try? JSONDecoder().decode(Saved.self, from: data),
              saved.cells.count == puzzle.size, saved.cells.allSatisfy({ $0.count == puzzle.size })
        else { return }
        entries = saved.cells
        revealed = Set(saved.revealed.filter(puzzle.words.indices.contains))
        misses = Set(saved.misses)
        active = puzzle.words.indices.contains(saved.active) ? saved.active : 0
    }
}
