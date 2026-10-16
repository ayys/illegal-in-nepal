import sys, concurrent.futures as cf
sys.argv = [sys.argv[0], "x", "0", "0"] + sys.argv[1:]
from eapcrawl import get  # noqa: E402

ids = [a for a in sys.argv[4:]]
with cf.ThreadPoolExecutor(8) as ex:
    for pid, lab, n in ex.map(get, ids):
        if lab:
            print(pid, "|", lab, "|", n, flush=True)
