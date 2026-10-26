import Foundation
import Observation

/// The dictionary on the phone. The app ships with a whole one (make -C
/// shabdakosh app-dictionary); after that it keeps itself current from the
/// repository's dictionary-* releases (.github/workflows/dictionary.yml),
/// quietly: each release's small update applies on top of the one before, and
/// only a dictionary too far behind for that downloads a whole new one.
@Observable
@MainActor
final class Shabdakosh {
    static let shared = Shabdakosh()

    private static let releases = URL(string: "https://api.github.com/repos/ayys/illegal-in-nepal/releases?per_page=100")!
    private static let tagPrefix = "dictionary-"
    private static let full = "dictionary-v\(OfflineStore.schema).sqlite.gz"
    private static let update = "dictionary-v\(OfflineStore.schema)-update.sqlite.gz"
    private static let checkEvery: TimeInterval = 6 * 3600

    private(set) var store: OfflineStore?
    private var updating = false

    /// The dictionary, opened on first use.
    func ready() throws -> OfflineStore {
        if let store { return store }
        let store = try Self.newest()
        self.store = store
        // Load the search list now, so the first search doesn't wait for it.
        Task.detached { await store.prepareSearch() }
        return store
    }

    /// The bundled dictionary or the updated one, whichever is newer; tags
    /// sort by time. An updated one older than the bundle (after the app
    /// itself updates) is dropped.
    private static func newest() throws -> OfflineStore {
        guard let bundled = bundledURL() else { throw OfflineStore.Failure.open("dictionary.sqlite") }
        let shipped = try OfflineStore(bundled)
        let installed = try installedURL()
        if let updated = try? OfflineStore(installed) {
            if updated.version >= shipped.version { return updated }
            try? FileManager.default.removeItem(at: installed)
        }
        return shipped
    }

    // MARK: Updating

    /// Brings the dictionary up to the newest release, without telling the
    /// reader; runs at most every few hours, and never on Low Data Mode.
    func update() async {
        let defaults = UserDefaults.standard
        if let last = defaults.object(forKey: "dictionaryChecked") as? Date,
           Date().timeIntervalSince(last) < Self.checkEvery {
            return
        }
        guard !updating, let current = try? ready() else { return }
        updating = true
        defer { updating = false }
        do {
            let releases = try await Self.dictionaryReleases()
            defaults.set(Date(), forKey: "dictionaryChecked")
            guard let newest = releases.first, newest.tag > current.version else { return }
            try await Self.catchUp(from: current, to: releases)
            let store = try Self.newest()
            self.store = store
            Task.detached { await store.prepareSearch() }
        } catch {
            // Quietly try again next time.
        }
    }

    /// Applies the updates of every release after `current`'s, oldest first,
    /// to a copy of it; or, when that chain is broken, fetches the newest
    /// whole dictionary, on Wi-Fi only.
    private static func catchUp(from current: OfflineStore, to releases: [Release]) async throws {
        let newer = releases.prefix { $0.tag > current.version }.reversed()
        let chain = Array(newer)
        let installed = try installedURL()
        let source = (try? OfflineStore(installed))?.version == current.version ? installed : bundledURL()!
        let work = try directory().appending(path: "incoming.sqlite")
        if chain.first?.base == current.version, chain.allSatisfy({ $0.update != nil }) {
            try await Task.detached {
                try? FileManager.default.removeItem(at: work)
                try FileManager.default.copyItem(at: source, to: work)
            }.value
            for release in chain {
                let gz = try await download(release.update!, cellular: true)
                defer { try? FileManager.default.removeItem(at: gz) }
                let file = try directory().appending(path: "update.sqlite")
                try await Task.detached {
                    try? FileManager.default.removeItem(at: file)
                    try Gzip.decompress(gz, to: file)
                    defer { try? FileManager.default.removeItem(at: file) }
                    guard try OfflineStore.apply(file, to: work) == release.tag else {
                        throw OfflineStore.Failure.update(release.tag)
                    }
                }.value
            }
        } else {
            let newest = releases[0]
            let gz = try await download(newest.full, cellular: false)
            defer { try? FileManager.default.removeItem(at: gz) }
            try await Task.detached {
                try? FileManager.default.removeItem(at: work)
                try Gzip.decompress(gz, to: work)
            }.value
        }
        try await install(work, expecting: releases[0].tag)
    }

    /// Checks a finished dictionary and puts it in place of the updated one.
    private static func install(_ work: URL, expecting tag: String) async throws {
        let installed = try installedURL()
        try await Task.detached {
            let candidate = try OfflineStore(work)
            guard candidate.version == tag, await candidate.isIntact() else {
                throw OfflineStore.Failure.update(candidate.version)
            }
        }.value
        if FileManager.default.fileExists(atPath: installed.path) {
            _ = try FileManager.default.replaceItemAt(installed, withItemAt: work)
        } else {
            try FileManager.default.moveItem(at: work, to: installed)
        }
    }

    // MARK: Files

    private static func directory() throws -> URL {
        var url = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask,
                                              appropriateFor: nil, create: true)
            .appending(path: "Dictionary", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        // It can always be fetched again; keep it out of backups.
        var values = URLResourceValues()
        values.isExcludedFromBackup = true
        try url.setResourceValues(values)
        return url
    }

    private static func installedURL() throws -> URL {
        try directory().appending(path: "dictionary.sqlite")
    }

    private static func bundledURL() -> URL? {
        Bundle.main.url(forResource: "dictionary", withExtension: "sqlite")
            ?? Bundle.main.url(forResource: "dictionary", withExtension: "sqlite", subdirectory: "Dictionary")
    }

    // MARK: Releases

    struct Release: Sendable {
        let tag: String
        /// The release before this one, which `update` applies to.
        let base: String?
        let full: URL
        let update: URL?
    }

    private struct GitHubRelease: Decodable {
        struct Asset: Decodable {
            let name: String
            let browser_download_url: URL
        }

        let tag_name: String
        let draft: Bool
        let prerelease: Bool
        let assets: [Asset]
    }

    enum Failure: Error {
        case status(Int)
    }

    /// Dictionary releases this app can read, newest first.
    private static func dictionaryReleases() async throws -> [Release] {
        var request = URLRequest(url: releases)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        let (data, response) = try await session(cellular: true).data(for: request)
        let code = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard code == 200 else { throw Failure.status(code) }
        let found = try JSONDecoder().decode([GitHubRelease].self, from: data)
            .filter { !$0.draft && !$0.prerelease && $0.tag_name.hasPrefix(tagPrefix) }
            .sorted { $0.tag_name > $1.tag_name }
        return found.enumerated().compactMap { i, release in
            guard let whole = release.assets.first(where: { $0.name == full }) else { return nil }
            return Release(tag: release.tag_name,
                           base: i + 1 < found.count ? found[i + 1].tag_name : nil,
                           full: whole.browser_download_url,
                           update: release.assets.first { $0.name == update }?.browser_download_url)
        }
    }

    /// Updates are small and may use mobile data; whole dictionaries wait for
    /// Wi-Fi. Neither runs in Low Data Mode.
    private static func session(cellular: Bool) -> URLSession {
        let config = URLSessionConfiguration.default
        config.allowsExpensiveNetworkAccess = cellular
        config.allowsConstrainedNetworkAccess = false
        return URLSession(configuration: config)
    }

    private static func download(_ url: URL, cellular: Bool) async throws -> URL {
        let (file, response) = try await session(cellular: cellular).download(from: url)
        let code = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard code == 200 else {
            try? FileManager.default.removeItem(at: file)
            throw Failure.status(code)
        }
        // The system deletes `file` when this returns; keep a copy.
        let kept = try directory().appending(path: UUID().uuidString + ".gz")
        try FileManager.default.moveItem(at: file, to: kept)
        return kept
    }
}

enum Nepal {
    /// Today's date in Nepal, YYYY-MM-DD, as the site and the service count days.
    static var today: String {
        let format = DateFormatter()
        format.calendar = Calendar(identifier: .gregorian)
        format.locale = Locale(identifier: "en_US_POSIX")
        format.timeZone = TimeZone(identifier: "Asia/Kathmandu")
        format.dateFormat = "yyyy-MM-dd"
        return format.string(from: Date())
    }
}
