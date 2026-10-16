import json, sys, urllib.request, concurrent.futures as cf

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
proj = sys.argv[1]  # e.g. EAP1485-1
maxp = int(sys.argv[2])
maxf = int(sys.argv[3])


def get(pid):
    url = f"https://eap.bl.uk/archive-file/{pid}/manifest"
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30)
        d = json.loads(r.read())
        lab = d.get("label")
        if isinstance(lab, dict):
            lab = list(lab.values())[0][0]
        n = len(d.get("items", d.get("sequences", [{}])[0].get("canvases", [])))
        return pid, lab, n
    except Exception as e:
        return pid, None, str(e)[:40]


ids = [f"{proj}-{p}-{f}" for p in range(1, maxp + 1) for f in range(1, maxf + 1)]
with cf.ThreadPoolExecutor(8) as ex:
    for pid, lab, n in ex.map(get, ids):
        if lab:
            print(pid, "|", lab, "|", n, flush=True)
