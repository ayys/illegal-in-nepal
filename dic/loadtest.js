// k6 run dic/loadtest.js   (-e UNCACHED=1 to type random strings,
//                              -e BASE=http://127.0.0.1:8091 to skip Cloudflare)
//
// Each iteration is one person typing a word into the search box: the page
// debounces input by 100 ms, so every keystroke followed by a longer pause
// sends a request for the text typed so far, without waiting for earlier ones.
import http from "k6/http";
import { check } from "k6";
import { Counter, Trend } from "k6/metrics";
import { setTimeout } from "k6/timers";

const BASE = __ENV.BASE || "https://dic.illegal-in-nepal.org";
const DEBOUNCE = 0.1;
const WORDS = [
    "माया", "पानी", "घर", "प्रेम", "सत्य", "विद्यालय", "सम्झना", "किताब", "नेपाली", "आमा",
    "बुबा", "दिन", "रात", "मान्छे", "हिमाल", "नदी", "खोला", "गीत", "भाषा", "शब्द",
    "धर्म", "कर्म", "ज्ञान", "विज्ञान", "सरकार", "देश", "गाउँ", "सहर", "बाटो", "मन",
    "सुन्दर", "राम्रो", "नराम्रो", "खुसी", "दुःख", "भोक", "तिर्खा", "चिया", "भात", "दाल",
];
const LETTERS = [..."कखगघचछजझटठडढतथदधनपफबभमयरलवशसह"];
const SIGNS = ["", "ा", "ि", "ी", "ु", "ू", "े", "ो", "ं"];

const keystrokes = new Counter("keystrokes");
// From the last keystroke until its results are on screen, debounce included.
const resultsWait = new Trend("results_wait", true);

export const options = {
    stages: [
        { duration: "20s", target: 20 },
        { duration: "40s", target: 50 },
        { duration: "40s", target: 100 },
        { duration: "20s", target: 0 },
    ],
    thresholds: {
        http_req_failed: ["rate<0.01"],
        results_wait: ["p(95)<800"],
    },
};

const pick = (list) => list[Math.floor(Math.random() * list.length)];
const between = (lo, hi) => lo + Math.random() * (hi - lo);

// Drop, repeat or swap a random character, as a hurried typist would.
function typo(word) {
    const chars = [...word];
    const i = Math.floor(Math.random() * chars.length);
    switch (Math.floor(Math.random() * 3)) {
        case 0: chars.splice(i, 1); break;
        case 1: chars.splice(i, 0, chars[i]); break;
        default: chars[i] = chars[(i + 1) % chars.length];
    }
    return chars.join("") || word;
}

// Random syllables: practically never repeat, so every request is a full scan.
function random() {
    let s = "";
    for (let n = 2 + Math.floor(Math.random() * 3); n > 0; n--) s += pick(LETTERS) + pick(SIGNS);
    return s;
}

const wait = (seconds) => new Promise((resolve) => setTimeout(resolve, seconds * 1000));

// Like the page, a new request doesn't wait for the previous one; the page
// aborts the old fetch, but the server still does the work.
async function search(query, final) {
    const res = await http.asyncRequest("GET", `${BASE}/search?q=${encodeURIComponent(query)}`, null, {
        tags: { final: String(final) },
    });
    check(res, {
        "status 200": (r) => r.status === 200,
        "json array": (r) => Array.isArray(r.json()),
    });
}

export default async function () {
    const text = __ENV.UNCACHED ? random() : Math.random() < 0.3 ? typo(pick(WORDS)) : pick(WORDS);
    const keys = [...text];
    const requests = [];
    let shown = null;
    for (let i = 0; i < keys.length; i++) {
        keystrokes.add(1);
        const last = i === keys.length - 1;
        const gap = last ? Infinity : between(0.05, 0.35);
        if (gap > DEBOUNCE) {
            await wait(DEBOUNCE);
            const query = keys.slice(0, i + 1).join("");
            if (last) {
                const typed = Date.now() - DEBOUNCE * 1000;
                shown = search(query, true).then(() => resultsWait.add(Date.now() - typed));
            } else {
                requests.push(search(query, false));
                await wait(gap - DEBOUNCE);
            }
        } else {
            await wait(gap);
        }
    }
    await shown;
    await wait(between(2, 5));
    await Promise.all(requests);
}
