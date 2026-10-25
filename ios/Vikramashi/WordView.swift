import SwiftUI

/// A dictionary page, by its file name without .html.
struct WordRoute: Hashable, Sendable {
    let slug: String

    init(slug: String) {
        self.slug = slug.hasSuffix(".html") ? String(slug.dropLast(".html".count)) : slug
    }

    /// Reads the in-app links that definitions use for other words.
    init?(url: URL) {
        guard url.scheme == "vikramashi", url.host() == "word",
              let slug = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                  .queryItems?.first(where: { $0.name == "slug" })?.value
        else { return nil }
        self.init(slug: slug)
    }

    /// Opens this word inside the app.
    var link: URL {
        var components = URLComponents()
        components.scheme = "vikramashi"
        components.host = "word"
        components.queryItems = [URLQueryItem(name: "slug", value: slug)]
        return components.url!
    }

    var webURL: URL { API.site.appending(path: "shabdakosh/\(slug).html") }
}

/// One entry, as dic/src/word.rs serializes it.
struct WordPage: Decodable, Sendable {
    struct Block: Decodable, Sendable {
        /// Empty when the dictionary gives none.
        let grammar: String
        let senses: [[Span]]
    }

    /// A run of a sense's text; `slug` is set when it links to another entry.
    struct Span: Decodable, Sendable {
        let text: String
        let slug: String?
    }

    let word: String
    let blocks: [Block]

    /// Distinct grammar tags, in order.
    var grammar: [String] {
        blocks.map(\.grammar).filter { !$0.isEmpty }.reduce(into: []) { tags, tag in
            if !tags.contains(tag) { tags.append(tag) }
        }
    }

    func ref(slug: String) -> WordRef {
        let first = blocks.first?.senses.first.map { $0.map(\.text).joined() } ?? ""
        return WordRef(slug: slug, word: word, gloss: first.withoutSenseNumber, grammar: blocks.first?.grammar ?? "")
    }
}

/// A sense laid out for reading: its number, whether it only points to
/// another entry, and its text with links to other words.
struct Sense {
    let number: String?
    let isReference: Bool
    let text: AttributedString

    init(_ spans: [WordPage.Span]) {
        var spans = spans
        var number: String?
        var isReference = false
        if let first = spans.first, first.slug == nil {
            var head = first.text
            if let match = head.firstMatch(of: #/^\s*([०-९0-9]+)\.\s*/#) {
                number = String(match.1)
                head.removeSubrange(match.range)
            }
            // "हे." is the dictionary's "see": the sense is another entry.
            if let match = head.firstMatch(of: #/^\s*हे\.\s*/#) {
                isReference = true
                head.removeSubrange(match.range)
            }
            spans[0] = WordPage.Span(text: head, slug: nil)
        }
        self.number = number
        self.isReference = isReference
        text = spans.reduce(into: AttributedString()) { out, span in
            var run = AttributedString(span.text)
            if let slug = span.slug {
                run.link = WordRoute(slug: slug).link
                run.swiftUI.underlineStyle = Text.LineStyle(pattern: .dot, color: .mute.opacity(0.6))
            }
            out += run
        }
    }
}

struct WordView: View {
    let route: WordRoute
    @Environment(Library.self) private var library
    @State private var page: WordPage?
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header
                if let page {
                    ForEach(page.blocks.indices, id: \.self) { i in
                        block(page.blocks[i], heading: page.blocks.count > 1 || page.grammar.count > 1)
                    }
                    Link(destination: route.webURL) {
                        Label("illegal-in-nepal.org मा हेर्नुहोस्", systemImage: "safari")
                            .font(.footnote)
                            .foregroundStyle(.mute)
                    }
                    .padding(.top, 40)
                } else if let error {
                    Notice(systemImage: "wifi.exclamationmark", title: "अर्थ आएन", message: error)
                        .padding(.top, 40)
                } else {
                    ProgressView().tint(.mute).frame(maxWidth: .infinity).padding(.top, 56)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 22)
            .padding(.bottom, 40)
        }
        .background(.paper)
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .toolbar {
            ToolbarItemGroup(placement: .primaryAction) {
                if let page {
                    let saved = library.isSaved(route.slug)
                    Button {
                        withAnimation(.snappy) { library.toggleSaved(page.ref(slug: route.slug)) }
                    } label: {
                        Image(systemName: saved ? "bookmark.fill" : "bookmark")
                            .contentTransition(.symbolEffect(.replace))
                    }
                    .accessibilityLabel(saved ? "सङ्ग्रहबाट हटाउनुहोस्" : "सङ्ग्रहमा राख्नुहोस्")
                    .sensoryFeedback(.selection, trigger: saved)
                }
                ShareLink(item: route.webURL)
            }
        }
        .task { await load() }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(page?.word ?? route.slug)
                .font(.serif(52, relativeTo: .largeTitle))
                .foregroundStyle(.ink)
                .textSelection(.enabled)
            if let page, !page.grammar.isEmpty {
                HStack(spacing: 8) {
                    ForEach(page.grammar, id: \.self) { Chip(Grammar.name($0)) }
                }
            }
            RuleLine().padding(.top, 10)
        }
        .padding(.top, 20)
        .padding(.bottom, 24)
    }

    private func block(_ block: WordPage.Block, heading: Bool) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            if heading && !block.grammar.isEmpty {
                Text(Grammar.name(block.grammar))
                    .font(.hand(19))
                    .foregroundStyle(.rust)
            }
            let senses = block.senses.map(Sense.init)
            let numbered = senses.contains { $0.number != nil }
            ForEach(senses.indices, id: \.self) { i in
                row(senses[i], numbered: numbered)
            }
        }
        .padding(.bottom, 28)
    }

    private func row(_ sense: Sense, numbered: Bool) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            if numbered {
                Text(sense.number ?? "")
                    .font(.title3.weight(.bold))
                    .foregroundStyle(.rust)
                    .frame(minWidth: 18, alignment: .leading)
            }
            VStack(alignment: .leading, spacing: 4) {
                if sense.isReference {
                    Text("हेर्नुहोस्")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.mute)
                }
                Text(sense.text)
                    .font(.serif(21))
                    .foregroundStyle(.ink)
                    .tint(.ink)
                    .lineSpacing(5)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private func load() async {
        do {
            let page = try await API.word(route)
            self.page = page
            error = nil
            library.viewed(page.ref(slug: route.slug))
        } catch {
            if page == nil { self.error = error.localizedDescription }
        }
    }
}

/// A NavigationStack whose word links open WordView instead of the website.
struct WordStack<Root: View>: View {
    @ViewBuilder let root: () -> Root
    @State private var path: [WordRoute] = []

    var body: some View {
        NavigationStack(path: $path) {
            root().navigationDestination(for: WordRoute.self) { WordView(route: $0) }
        }
        .environment(\.openURL, OpenURLAction { url in
            guard let route = WordRoute(url: url) else { return .systemAction }
            path.append(route)
            return .handled
        })
    }
}

#Preview {
    WordStack { WordView(route: WordRoute(slug: "घर")) }.environment(Library())
}
