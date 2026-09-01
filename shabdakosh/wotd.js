(() => {
    const nepalDay = () =>
        new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kathmandu" });

    const sha256Hex = async (text) => {
        const buf = await crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(text)
        );
        return [...new Uint8Array(buf)]
            .map((b) => b.toString(16).padStart(2, "0"))
            .join("");
    };

    const slugify = (word) => {
        let s = word.normalize("NFKC").trim().replace(/[ /]/g, "-");
        s = s.replace(/[^\p{L}\p{N}_\-\u0900-\u097F]/gu, "");
        s = s.replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
        return s || "entry";
    };

    const inflateJson = async (buf) => {
        const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
        const isGzip = bytes.length >= 2 && bytes[0] === 0x1f && bytes[1] === 0x8b;
        if (!isGzip) {
            return JSON.parse(new TextDecoder("utf-8").decode(bytes));
        }
        if (!window.DecompressionStream) {
            throw new Error("gzip");
        }
        const stream = new Blob([bytes])
            .stream()
            .pipeThrough(new DecompressionStream("gzip"));
        return JSON.parse(await new Response(stream).text());
    };

    const loadJson = async (url) => {
        const res = await fetch(url);
        if (!res.ok) throw new Error(url + " " + res.status);
        const buf = new Uint8Array(await res.arrayBuffer());
        const isGzip = buf.length >= 2 && buf[0] === 0x1f && buf[1] === 0x8b;
        if (isGzip) return inflateJson(buf);
        return JSON.parse(new TextDecoder("utf-8").decode(buf));
    };

    const today = async (base) => {
        const prefix = base || "./";
        const day = nepalDay();
        const meta = await loadJson(prefix + "wotd.json");
        if (!meta.n) throw new Error("empty");
        const hex = await sha256Hex(day);
        const idx = Number(BigInt("0x" + hex) % BigInt(meta.n));
        const size = meta.shard;
        const rows = await loadJson(prefix + "wotd/" + Math.floor(idx / size) + ".json.gz");
        const row = rows[idx % size];
        if (!row) throw new Error("row");
        return { day, word: row[0], sense: row[1], slug: slugify(row[0]) };
    };

    window.Wotd = { nepalDay, slugify, today };
})();
