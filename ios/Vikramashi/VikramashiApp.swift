import SwiftUI

@main
struct VikramashiApp: App {
    @State private var library = Library()
    @Environment(\.scenePhase) private var scenePhase

    init() {
        Theme.setUp()
    }

    var body: some Scene {
        WindowGroup {
            TabView {
                HomeView()
                    .tabItem { Label("शब्दकोश", systemImage: "character.book.closed") }
                CrosswordView()
                    .tabItem { Label("वर्गपहेली", systemImage: "square.grid.3x3.square") }
                SavedView()
                    .tabItem { Label("सङ्ग्रह", systemImage: "bookmark") }
            }
            .tint(.rust)
            .environment(library)
        }
        // Keep the dictionary current, quietly, whenever the app comes back.
        .onChange(of: scenePhase, initial: true) { _, phase in
            if phase == .active {
                Task { await Shabdakosh.shared.update() }
            }
        }
    }
}
