(function (exports) {
    'use strict';

    // Puzzles come from the API (dic/src/crossword.rs); this is the scoring.
    const WORD_POINTS = 10;
    const MISS_COST = 2;

    const maxScore = (words) => words.length * WORD_POINTS;

    // A revealed word earns nothing; each wrong guess costs MISS_COST.
    const score = (words, reveals, misses) =>
        Math.max(0, maxScore(words) - reveals * WORD_POINTS - misses * MISS_COST);

    exports.maxScore = maxScore;
    exports.score = score;
})(typeof module !== 'undefined' && module.exports ? module.exports : (window.Crossword = {}));
