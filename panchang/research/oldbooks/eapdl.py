import json, os, re, sys, html, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120).read()


def desc(pid):
    s = fetch(f"https://eap.bl.uk/archive-file/{pid}").decode()
    t = re.sub(r"<script.*?</script>", " ", s, flags=re.S)
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
    i = t.find("View images from this file")
    j = t.find("Related files")
    return t[i:j][:900]


def services(pid):
    d = json.loads(fetch(f"https://eap.bl.uk/archive-file/{pid}/manifest"))
    out = []
    for c in d["items"]:
        body = c["items"][0]["items"][0]["body"]
        svc = body.get("service", [{}])
        svc = svc[0] if isinstance(svc, list) else svc
        sid = svc.get("@id") or svc.get("id")
        out.append((sid, c.get("width"), c.get("height")))
    return out


if __name__ == "__main__":
    mode, pid = sys.argv[1], sys.argv[2]
    if mode == "desc":
        print(pid, "::", desc(pid))
    elif mode == "list":
        for s in services(pid):
            print(*s)
    elif mode == "dl":
        outdir = sys.argv[3]
        os.makedirs(outdir, exist_ok=True)
        for k, (sid, w, h) in enumerate(services(pid), 1):
            fn = os.path.join(outdir, f"{k:02d}.jpg")
            if not os.path.exists(fn):
                open(fn, "wb").write(fetch(sid.replace("http://", "https://") + "/full/full/0/default.jpg"))
            print(fn, w, h, flush=True)
