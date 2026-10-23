"""book − model for Mars–Saturn, arcminutes, at Kathmandu sunrise."""
import sys
sys.path.insert(0, "../..")
import surya
import ss_planets as ss
from swiss2083 import BOOK, deg, diff

if __name__ == "__main__":
    print("book − pure SS, arcmin")
    for day, row in BOOK.items():
        jd = surya.sunrise(day)
        print(day, "  ".join(f"{b} {diff(deg(t), ss.true_planet(jd, b)):+8.2f}" for b, t in zip(ss.ORDER, row)))
