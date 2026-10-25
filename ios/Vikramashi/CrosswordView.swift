import SwiftUI

/// आजको वर्गपहेली: the grid, the active clue and an अक्षर keyboard, like
/// the crossword apps, so no Nepali system keyboard is needed.
struct CrosswordView: View {
    @Environment(\.scenePhase) private var scenePhase
    @State private var game: CrosswordGame?
    @State private var error: String?
    @State private var showClues = false
    @State private var confirmReveal = false
    @State private var confirmClear = false

    var body: some View {
        WordStack {
            Group {
                if let game {
                    board(game)
                } else if let error {
                    Notice(systemImage: "wifi.exclamationmark", title: "पहेली आएन", message: error)
                } else {
                    ProgressView().tint(.mute)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(.paper)
            .navigationTitle("वर्गपहेली")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar { toolbar }
            .task { await load() }
            // A new puzzle starts at Nepal midnight.
            .onChange(of: scenePhase) { _, phase in
                if phase == .active { Task { await load() } }
            }
            .sheet(isPresented: $showClues) {
                if let game {
                    ClueList(game: game) { word in
                        game.go(to: word)
                        showClues = false
                    }
                    .presentationDetents([.medium, .large])
                }
            }
            .confirmationDialog("सबै उत्तर देखाउने?", isPresented: $confirmReveal, titleVisibility: .visible) {
                Button("उत्तर देखाउनुहोस्", role: .destructive) { game?.revealAll() }
            } message: {
                Text("भर्न बाँकी हरेक शब्दको १० अङ्क कट्छ।")
            }
            .confirmationDialog("सबै कोठा मेटाउने?", isPresented: $confirmClear, titleVisibility: .visible) {
                Button("मेटाउनुहोस्", role: .destructive) { game?.clear() }
            } message: {
                Text("कटेको अङ्क फर्किँदैन।")
            }
        }
    }

    @ToolbarContentBuilder private var toolbar: some ToolbarContent {
        if let game {
            ToolbarItemGroup(placement: .primaryAction) {
                Button {
                    showClues = true
                } label: {
                    Image(systemName: "list.bullet")
                }
                .accessibilityLabel("सबै सङ्केत")
                Menu {
                    Button("यो शब्द भर्नुहोस्", systemImage: "character.cursor.ibeam") { game.revealWord() }
                        .disabled(game.isRight(game.active))
                    Button("सबै उत्तर देखाउनुहोस्", systemImage: "eye") { confirmReveal = true }
                    Divider()
                    Button("सबै मेटाउनुहोस्", systemImage: "trash", role: .destructive) { confirmClear = true }
                } label: {
                    Image(systemName: "ellipsis")
                }
                .accessibilityLabel("सहायता")
            }
        }
    }

    private func board(_ game: CrosswordGame) -> some View {
        VStack(spacing: 0) {
            HStack {
                Text("अङ्क \(game.score.nepali)/\(game.maxScore.nepali)")
                    .foregroundStyle(.rust)
                    .contentTransition(.numericText())
                    .animation(.snappy, value: game.score)
                Spacer()
                let right = game.puzzle.words.indices.filter(game.isRight).count
                Text("\(right.nepali)/\(game.puzzle.words.count.nepali) शब्द")
                    .foregroundStyle(.mute)
            }
            .font(.subheadline.weight(.semibold))
            .padding(.horizontal, 20)
            .padding(.top, 4)
            CrosswordGrid(game: game)
                .padding(.horizontal, 16)
                .padding(.top, 8)
                .frame(maxHeight: .infinity)
            if game.solved {
                Solved(game: game)
            } else {
                ClueBar(game: game)
                AksharKeyboard(game: game)
            }
        }
    }

    private func load() async {
        do {
            let puzzle = try await API.crossword()
            if game?.puzzle.day != puzzle.day {
                game = CrosswordGame(puzzle: puzzle)
            }
            error = nil
        } catch {
            if game == nil { self.error = error.localizedDescription }
        }
    }
}

struct CrosswordGrid: View {
    let game: CrosswordGame

    var body: some View {
        let (rows, cols) = game.bounds
        let active = game.activeCells
        let wrong = game.wrongCells
        let revealed = game.revealedCells
        VStack(spacing: 0) {
            ForEach(Array(rows), id: \.self) { r in
                HStack(spacing: 0) {
                    ForEach(Array(cols), id: \.self) { c in
                        let cell = Cell(r: r, c: c)
                        square(cell, active: active.contains(cell), wrong: wrong.contains(cell),
                               revealed: revealed.contains(cell))
                    }
                }
            }
        }
        .aspectRatio(CGFloat(cols.count) / CGFloat(rows.count), contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 6, style: .continuous).stroke(.block, lineWidth: 2))
        .sensoryFeedback(.selection, trigger: game.cursor)
    }

    @ViewBuilder
    private func square(_ cell: Cell, active: Bool, wrong: Bool, revealed: Bool) -> some View {
        if game.isOpen(cell) {
            let isCursor = cell == game.cursor
            ZStack(alignment: .topLeading) {
                Rectangle().fill(isCursor ? Color.rust.opacity(0.32) : active ? Color.rust.opacity(0.12) : Color.card)
                if let number = game.number(at: cell) {
                    Text(number.nepali)
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(.mute)
                        .padding(.leading, 3)
                        .padding(.top, 1)
                }
                Text(game.entry(at: cell))
                    .font(.serif(26, relativeTo: .title2))
                    .minimumScaleFactor(0.5)
                    .lineLimit(1)
                    .foregroundStyle(wrong ? Color.red : revealed ? Color.mute : Color.ink)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .padding(.top, 4)
            }
            .overlay(Rectangle().stroke(.block.opacity(0.35), lineWidth: 0.5))
            .aspectRatio(1, contentMode: .fit)
            .contentShape(Rectangle())
            .onTapGesture { game.tap(cell) }
            .accessibilityElement()
            .accessibilityLabel(game.entry(at: cell).isEmpty ? "खाली" : game.entry(at: cell))
            .accessibilityAddTraits(.isButton)
        } else {
            Rectangle().fill(.block).aspectRatio(1, contentMode: .fit)
        }
    }
}

/// The active clue; tap it to turn, or step through clues with the arrows.
struct ClueBar: View {
    let game: CrosswordGame

    var body: some View {
        let word = game.activeWord
        HStack(spacing: 0) {
            arrow("chevron.left", label: "अघिल्लो सङ्केत") { game.moveWord(-1) }
            Button(action: game.toggleDirection) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(word.number.nepali) \(word.dir.name)")
                        .font(.caption.weight(.bold))
                        .foregroundStyle(.rust)
                    Text("\(word.clue) (\(word.cells.count.nepali))")
                        .font(.serif(18, relativeTo: .body))
                        .foregroundStyle(.ink)
                        .lineLimit(2)
                        .minimumScaleFactor(0.8)
                        .multilineTextAlignment(.leading)
                }
                .frame(maxWidth: .infinity, minHeight: 52, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            arrow("chevron.right", label: "अर्को सङ्केत") { game.moveWord(1) }
        }
        .padding(.vertical, 6)
        .background(.wash)
    }

    private func arrow(_ image: String, label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: image)
                .font(.body.weight(.semibold))
                .foregroundStyle(.rust)
                .frame(width: 44, height: 52)
        }
        .accessibilityLabel(label)
    }
}

/// Letters in varga order; the top row holds vowel signs, or for one
/// keystroke the independent vowels.
struct AksharKeyboard: View {
    let game: CrosswordGame
    @State private var vowels = false

    private static let signs = ["ा", "ि", "ी", "ु", "ू", "े", "ै", "ो", "ौ", "ृ"]
    private static let independent = ["अ", "आ", "इ", "ई", "उ", "ऊ", "ए", "ऐ", "ओ", "औ"]
    private static let consonants = [
        ["क", "ख", "ग", "घ", "ङ", "च", "छ", "ज", "झ", "ट"],
        ["ठ", "ड", "ढ", "ण", "त", "थ", "द", "ध", "न", "प"],
        ["फ", "ब", "भ", "म", "य", "र", "ल", "व", "श", "ष"],
    ]

    var body: some View {
        VStack(spacing: 7) {
            HStack(spacing: 5) {
                if vowels {
                    ForEach(Self.independent, id: \.self) { vowel in
                        key(vowel, tinted: true) {
                            game.type(vowel)
                            vowels = false
                        }
                    }
                } else {
                    ForEach(Self.signs, id: \.self) { sign in
                        key("◌" + sign, tinted: true) { game.mark(sign.unicodeScalars.first!) }
                    }
                }
            }
            ForEach(Self.consonants, id: \.self) { row in
                HStack(spacing: 5) {
                    ForEach(row, id: \.self) { letter in
                        key(letter) { game.type(letter) }
                    }
                }
            }
            HStack(spacing: 5) {
                Button {
                    vowels.toggle()
                } label: {
                    Text(vowels ? "◌ा" : "अ")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(KeyStyle(selected: vowels))
                .accessibilityLabel(vowels ? "मात्रा" : "स्वर")
                key("स") { game.type("स") }
                key("ह") { game.type("ह") }
                key("ऋ") { game.type("ऋ") }
                key("◌ँ", tinted: true) { game.mark("\u{0901}") }
                key("◌ं", tinted: true) { game.mark("\u{0902}") }
                key("◌ः", tinted: true) { game.mark("\u{0903}") }
                Button(action: game.delete) {
                    Image(systemName: "delete.left")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(KeyStyle())
                .accessibilityLabel("मेटाउनुहोस्")
            }
        }
        .padding(.horizontal, 4)
        .padding(.top, 8)
        .padding(.bottom, 6)
        .background(.wash.opacity(0.6))
        .sensoryFeedback(.error, trigger: game.rejected)
    }

    private func key(_ label: String, tinted: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(label)
                .frame(maxWidth: .infinity, minHeight: 44)
        }
        .buttonStyle(KeyStyle(tinted: tinted))
    }
}

struct KeyStyle: ButtonStyle {
    var tinted = false
    var selected = false

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 21))
            .foregroundStyle(tinted || selected ? Color.rust : Color.ink)
            .background(
                RoundedRectangle(cornerRadius: 7, style: .continuous)
                    .fill(configuration.isPressed || selected ? Color.wash : Color.card)
                    .shadow(color: .black.opacity(0.18), radius: 0, x: 0, y: 1)
            )
            .scaleEffect(configuration.isPressed ? 0.94 : 1)
    }
}

/// Shown in place of the keyboard once every word is right.
struct Solved: View {
    let game: CrosswordGame

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text("बधाई छ!").font(.hand(30)).foregroundStyle(.rust)
                Text("आजको पहेली पूरा भयो। अङ्क \(game.score.nepali)/\(game.maxScore.nepali)")
                    .font(.serif(19))
                    .foregroundStyle(.ink)
                SectionLabel("आजका शब्दहरू").padding(.top, 8)
                ForEach(game.clueOrder, id: \.self) { i in
                    let word = game.puzzle.words[i]
                    NavigationLink(value: WordRoute(slug: word.word)) {
                        WordRow(word: word.word, grammar: "", gloss: word.clue)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(20)
        }
        .frame(maxHeight: 340)
        .background(.wash)
    }
}

/// Every clue, across then down; tap one to go to it.
struct ClueList: View {
    let game: CrosswordGame
    let select: (Int) -> Void

    var body: some View {
        NavigationStack {
            List {
                ForEach([Puzzle.Direction.across, .down], id: \.self) { dir in
                    Section(dir.name) {
                        ForEach(game.clueOrder.filter { game.puzzle.words[$0].dir == dir }, id: \.self) { i in
                            row(i)
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
            .background(.paper)
            .navigationTitle("सङ्केत")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
        }
    }

    private func row(_ i: Int) -> some View {
        let word = game.puzzle.words[i]
        return Button {
            select(i)
        } label: {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(word.number.nepali)
                    .font(.headline)
                    .foregroundStyle(.rust)
                    .frame(minWidth: 20, alignment: .leading)
                Text("\(word.clue) (\(word.cells.count.nepali))")
                    .font(.serif(18))
                    .foregroundStyle(.ink)
                Spacer(minLength: 0)
                if game.isRight(i) {
                    Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                } else if game.isFull(i) {
                    Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
                }
            }
        }
        .listRowBackground(i == game.active ? Color.wash : Color.card)
    }
}

#Preview {
    CrosswordView()
}
