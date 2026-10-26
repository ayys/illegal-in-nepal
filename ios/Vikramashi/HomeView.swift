import SwiftUI

/// Search, with today's word and recently viewed words while the box is empty.
struct HomeView: View {
    @Environment(Library.self) private var library
    @Environment(\.scenePhase) private var scenePhase
    @State private var query = ""
    @State private var results: [Entry] = []
    /// The query `results` answer, once they arrive.
    @State private var resultsFor: String?
    @State private var searchError: String?
    @State private var today: WordOfDay?
    @State private var todayFailed = false

    private var trimmed: String { query.trimmingCharacters(in: .whitespaces) }

    var body: some View {
        WordStack {
            Group {
                if trimmed.isEmpty {
                    home
                } else {
                    resultsList
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(.paper)
            .navigationTitle("शब्दकोश")
            .searchable(text: $query, placement: searchPlacement, prompt: "नेपाली शब्द खोज्नुहोस्")
            .autocorrectionDisabled()
            .task(id: query) { await search() }
            .task { await loadToday() }
            // The word changes at Nepal midnight; check whenever the app comes back.
            .onChange(of: scenePhase) { _, phase in
                if phase == .active { Task { await loadToday() } }
            }
        }
    }

    private var searchPlacement: SearchFieldPlacement {
        #if os(iOS)
        .navigationBarDrawer(displayMode: .always)
        #else
        .automatic
        #endif
    }

    // MARK: Empty search box

    private var home: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 32) {
                if !todayFailed {
                    NavigationLink(value: today?.route ?? WordRoute(slug: "")) {
                        WordOfDayCard(word: today)
                    }
                    .buttonStyle(.plain)
                    .disabled(today == nil)
                }
                if library.recent.isEmpty {
                    hint
                } else {
                    recent
                }
                KeyboardTip()
            }
            .padding(.horizontal, 20)
            .padding(.top, 8)
            .padding(.bottom, 32)
        }
        .scrollDismissesKeyboard(.immediately)
    }

    private var recent: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                SectionLabel("हालै हेरिएका")
                Spacer()
                Button("हटाउनुहोस्") {
                    withAnimation { library.clearRecent() }
                }
                .font(.subheadline)
            }
            .padding(.bottom, 4)
            ForEach(library.recent) { word in
                NavigationLink(value: word.route) {
                    WordRow(word: word.word, grammar: word.grammar, gloss: word.gloss)
                }
                .buttonStyle(.plain)
                if word != library.recent.last {
                    RuleLine()
                }
            }
        }
    }

    private var hint: some View {
        VStack(alignment: .leading, spacing: 8) {
            SectionLabel("खोज्ने तरिका")
            Text("शब्द वा अर्थको अंश लेख्नुहोस्। हिज्जे अलि फरक परे पनि मिल्दा शब्दहरू भेटिन्छन्।")
                .font(.serif(18))
                .foregroundStyle(.mute)
        }
    }

    // MARK: Searching

    @ViewBuilder private var resultsList: some View {
        if let searchError, resultsFor != trimmed {
            Notice(systemImage: "wifi.exclamationmark", title: "खोज्न सकिएन", message: searchError)
        } else if resultsFor != trimmed && results.isEmpty {
            ProgressView().tint(.mute)
        } else if results.isEmpty {
            Notice(systemImage: "text.magnifyingglass", title: "कुनै शब्द भेटिएन",
                   message: "“\(trimmed)” सँग मिल्ने शब्द छैन। अर्को हिज्जे प्रयास गर्नुहोस्।")
        } else {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    ForEach(results) { entry in
                        NavigationLink(value: entry.route) {
                            WordRow(word: entry.word, grammar: entry.grammar, gloss: entry.preview)
                        }
                        .buttonStyle(.plain)
                        RuleLine()
                    }
                }
                .padding(.horizontal, 20)
            }
            .scrollDismissesKeyboard(.immediately)
        }
    }

    /// Runs again on every keystroke, cancelling the last run, so waiting
    /// first sends one request once typing pauses.
    private func search() async {
        let trimmed = trimmed
        guard !trimmed.isEmpty else {
            results = []
            resultsFor = nil
            searchError = nil
            return
        }
        try? await Task.sleep(for: .milliseconds(250))
        guard !Task.isCancelled else { return }
        do {
            let found = try await API.search(trimmed)
            results = found
            resultsFor = trimmed
            searchError = nil
        } catch {
            if !Task.isCancelled { searchError = error.localizedDescription }
        }
    }

    private func loadToday() async {
        do {
            today = try await API.wordOfDay()
            todayFailed = false
        } catch {
            // Keep showing the word already on screen.
            if today == nil { todayFailed = true }
        }
    }
}

struct WordOfDayCard: View {
    let word: WordOfDay?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("आजको शब्द").font(.hand(18)).foregroundStyle(.rust)
                Spacer()
                Text(date).font(.footnote).foregroundStyle(.mute)
            }
            Text(word?.word ?? "शब्द")
                .font(.serif(46, relativeTo: .largeTitle))
                .foregroundStyle(.ink)
                .padding(.top, 4)
            Text(word?.sense.withoutSenseNumber ?? "आजको शब्दको अर्थ यहाँ देखिन्छ।")
                .font(.serif(19))
                .foregroundStyle(.ink.opacity(0.85))
                .lineLimit(3)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 6) {
                Text("पूरा अर्थ")
                Image(systemName: "arrow.right")
            }
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(.rust)
            .padding(.top, 6)
        }
        .padding(22)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.wash, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
        .redacted(reason: word == nil ? .placeholder : [])
    }

    /// "2026-10-25" as "२५ अक्टोबर".
    private var date: String {
        guard let day = word?.day else { return "" }
        let input = DateFormatter()
        input.dateFormat = "yyyy-MM-dd"
        input.timeZone = TimeZone(identifier: "Asia/Kathmandu")
        guard let parsed = input.date(from: day) else { return day }
        let output = DateFormatter()
        output.locale = Locale(identifier: "ne_NP")
        output.timeZone = input.timeZone
        output.setLocalizedDateFormatFromTemplate("dMMMM")
        return output.string(from: parsed)
    }
}

/// One word in a list: headword, part of speech, and the start of its meaning.
struct WordRow: View {
    let word: String
    let grammar: String
    let gloss: String
    var chevron = true

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(word)
                        .font(.serif(24, relativeTo: .title2))
                        .foregroundStyle(.ink)
                    if !grammar.isEmpty {
                        Text(Grammar.name(grammar))
                            .font(.footnote.weight(.medium))
                            .foregroundStyle(.rust)
                    }
                }
                if !gloss.isEmpty {
                    Text(gloss.withoutSenseNumber)
                        .font(.serif(16, relativeTo: .subheadline))
                        .foregroundStyle(.mute)
                        .lineLimit(2)
                }
            }
            Spacer(minLength: 0)
            if chevron {
                Image(systemName: "chevron.right")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.rule)
            }
        }
        .padding(.vertical, 12)
        .contentShape(Rectangle())
    }
}

/// Points to the system keyboard that comes with the app, until dismissed.
struct KeyboardTip: View {
    @AppStorage("keyboardTipHidden") private var hidden = false

    var body: some View {
        if !hidden {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Label("नेपाली किबोर्ड", systemImage: "keyboard")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.rust)
                    Spacer()
                    Button {
                        withAnimation { hidden = true }
                    } label: {
                        Image(systemName: "xmark")
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(.mute)
                    }
                    .accessibilityLabel("लुकाउनुहोस्")
                }
                Text("जुनसुकै एपमा Nepali Romanized Pro लेआउटमा नेपाली लेख्नुहोस्।")
                    .font(.serif(17))
                    .foregroundStyle(.ink)
                Text("Settings → General → Keyboard → Keyboards → Add New Keyboard → Vikramashi")
                    .font(.footnote)
                    .foregroundStyle(.mute)
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.card, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 18, style: .continuous).stroke(.rule, lineWidth: 0.5))
        }
    }
}

struct RuleLine: View {
    var body: some View {
        Rectangle().fill(.rule).frame(height: 0.5)
    }
}

/// A centered icon, title and line of text for empty and error states.
struct Notice: View {
    let systemImage: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: systemImage)
                .font(.system(size: 40, weight: .light))
                .foregroundStyle(.rule)
            Text(title)
                .font(.serif(24, relativeTo: .title2))
                .foregroundStyle(.ink)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.mute)
                .multilineTextAlignment(.center)
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

extension String {
    /// "१. घरको काम" → "घरको काम".
    var withoutSenseNumber: String {
        replacing(#/^\s*[०-९0-9]+\.\s*/#, with: "")
    }
}

#Preview {
    HomeView().environment(Library())
}
