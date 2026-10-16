import io, json, os, sys, urllib.request, concurrent.futures as cf
from PIL import Image

UA = "Mozilla/5.0"
T = 1200


def fetch(url):
    import time
    for k in range(8):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120).read()
        except Exception as e:
            print('ERR',url,repr(e)[:120],flush=True)
            time.sleep(3 * (k + 1))
    raise RuntimeError(url)


def full(sid, out):
    info = json.loads(fetch(sid + "/info.json"))
    W, H = info["width"], info["height"]
    img = Image.new("RGB", (W, H), "white")
    jobs = [(x, y, min(T, W - x), min(T, H - y)) for y in range(0, H, T) for x in range(0, W, T)]

    def one(r):
        x, y, w, h = r
        return r, Image.open(io.BytesIO(fetch(f"{sid}/{x},{y},{w},{h}/full/0/default.jpg"))).convert("RGB")

    with cf.ThreadPoolExecutor(2) as ex:
        for (x, y, w, h), t in ex.map(one, jobs):
            img.paste(t, (x, y))
    img.save(out, quality=90)
    return W, H


if __name__ == "__main__":
    pid, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    m = json.loads(fetch(f"https://eap.bl.uk/archive-file/{pid}/manifest"))
    for k, c in enumerate(m["items"], 1):
        body = c["items"][0]["items"][0]["body"]
        svc = body["service"][0] if isinstance(body["service"], list) else body["service"]
        sid = (svc.get("@id") or svc.get("id")).replace("http://", "https://")
        fn = os.path.join(outdir, f"{k:02d}.jpg")
        if not os.path.exists(fn):
            print(fn, *full(sid, fn), flush=True)
