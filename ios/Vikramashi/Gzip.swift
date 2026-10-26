import Compression
import Foundation

/// Unpacks .gz files: the dictionary ships and updates gzipped.
enum Gzip {
    enum Failure: Error {
        case notGzip
    }

    /// Writes the contents of the gzip file `source` to `destination`.
    static func decompress(_ source: URL, to destination: URL) throws {
        let gz = try Data(contentsOf: source, options: .mappedIfSafe)
        let start = try headerLength(gz)
        // The last 8 bytes are a CRC and the size, not part of the stream.
        guard gz.count >= start + 8 else { throw Failure.notGzip }
        let deflated = gz[start..<(gz.count - 8)]

        FileManager.default.createFile(atPath: destination.path, contents: nil)
        let output = try FileHandle(forWritingTo: destination)
        defer { try? output.close() }
        let filter = try OutputFilter(.decompress, using: .zlib) { data in
            if let data { try output.write(contentsOf: data) }
        }
        let chunk = 1 << 20
        var at = deflated.startIndex
        while at < deflated.endIndex {
            let end = min(at + chunk, deflated.endIndex)
            try filter.write(deflated[at..<end])
            at = end
        }
        try filter.finalize()
    }

    /// The header's length, past the optional extra field, name, comment and CRC.
    private static func headerLength(_ gz: Data) throws -> Int {
        let bytes = [UInt8](gz.prefix(10))
        guard bytes.count == 10, bytes[0] == 0x1f, bytes[1] == 0x8b, bytes[2] == 8 else { throw Failure.notGzip }
        let flags = bytes[3]
        var at = gz.startIndex + 10
        if flags & 0x04 != 0 {
            guard gz.count >= at + 2 else { throw Failure.notGzip }
            at += 2 + Int(gz[at]) + Int(gz[at + 1]) << 8
        }
        for flag: UInt8 in [0x08, 0x10] where flags & flag != 0 {
            guard let zero = gz[at...].firstIndex(of: 0) else { throw Failure.notGzip }
            at = zero + 1
        }
        if flags & 0x02 != 0 {
            at += 2
        }
        return at - gz.startIndex
    }
}
