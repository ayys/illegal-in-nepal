"""Ketaki's mean-motion formulas (p53-62), per ahargana A in days."""
import ketaki
FORMULA = {  # degrees per day
    "sun": 69 / 70 - 1 / (158 * 60),
    "mars": 10 / 19 - 10 / (73 * 60),
    "mercury": 3 * 30 / 22 + 1 / 700,
    "jupiter": 1 / 12 - 1 / (69 * 60),
    "venus": 8 / 5 + 1 / (8 * 60) + 1 / (6 * 3600),
    "saturn": 1 / 30 + 1 / (132 * 60),
}
def make_mean(mode):
    def mean(body, jd):
        a = jd - ketaki.EPOCH
        if mode == "epoch":
            return (ketaki.MEAN0[body] + FORMULA[body] * a) % 360
        cycles, rest = divmod(a, ketaki.CYCLE)
        return (ketaki.MEAN0[body] + cycles * ketaki.REMAINDER[body] + FORMULA[body] * rest) % 360
    return mean
