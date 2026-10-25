import SwiftUI

/// Words the reader has saved, newest first.
struct SavedView: View {
    @Environment(Library.self) private var library

    var body: some View {
        WordStack {
            Group {
                if library.saved.isEmpty {
                    Notice(systemImage: "bookmark", title: "सङ्ग्रह खाली छ",
                           message: "शब्दको पानामा माथिको बुकमार्क थिचेर शब्द यहाँ राख्नुहोस्।")
                } else {
                    List {
                        ForEach(library.saved) { word in
                            NavigationLink(value: word.route) {
                                WordRow(word: word.word, grammar: word.grammar, gloss: word.gloss, chevron: false)
                            }
                            .listRowBackground(Color.paper)
                            .listRowSeparatorTint(.rule)
                        }
                        .onDelete { library.unsave(at: $0) }
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(.paper)
            .navigationTitle("सङ्ग्रह")
        }
    }
}

#Preview {
    SavedView().environment(Library())
}
