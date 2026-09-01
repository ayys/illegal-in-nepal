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

    const pickForDay = async (entries, day) => {
        const hex = await sha256Hex(day);
        const idx = Number(BigInt("0x" + hex) % BigInt(entries.length));
        return entries[idx];
    };

    const loadEntries = async (base) => {
        const prefix = base || "./";
        const gz = await fetch(prefix + "wotd-data.json.gz");
        if (gz.ok) {
            const buf = new Uint8Array(await gz.arrayBuffer());
            const isGzip = buf.length >= 2 && buf[0] === 0x1f && buf[1] === 0x8b;
            if (!isGzip) {
                return JSON.parse(new TextDecoder("utf-8").decode(buf));
            }
            if (window.DecompressionStream) {
                const stream = new Blob([buf])
                    .stream()
                    .pipeThrough(new DecompressionStream("gzip"));
                return JSON.parse(await new Response(stream).text());
            }
        }
        const res = await fetch(prefix + "wotd-data.json");
        if (!res.ok) throw new Error("data " + res.status);
        return res.json();
    };

    const today = async (base) => {
        const day = nepalDay();
        const entries = await loadEntries(base);
        if (!entries.length) throw new Error("empty");
        const picked = await pickForDay(entries, day);
        return { day, ...picked };
    };

    window.Wotd = { nepalDay, pickForDay, loadEntries, today };
})();
