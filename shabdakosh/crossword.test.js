'use strict';

const assert = require('assert');
const { maxScore, score } = require('./crossword.js');

const pair = [{ word: 'किताब' }, { word: 'आँगन' }];
assert.strictEqual(maxScore(pair), 20, 'each word is worth 10');
assert.strictEqual(score(pair, 0, 0), 20, 'a clean solve keeps the maximum');
assert.strictEqual(score(pair, 1, 0), 10, 'a revealed word earns nothing');
assert.strictEqual(score(pair, 0, 3), 14, 'each wrong guess costs 2');
assert.strictEqual(score(pair, 2, 5), 0, 'the score never goes below zero');
console.log('crossword scoring ok');
