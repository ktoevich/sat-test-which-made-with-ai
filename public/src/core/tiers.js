/**
 * The tiers a score falls into, on the test's own 200-800 scale: Basic, then
 * Intermediate from 500, Advanced from 600 and Elite from 700.
 *
 * A student's tier is the band of their best score in either section — the
 * API sends it as `user.tier`; a single attempt's band colours its row in the
 * history, its place on the leaderboard and its point on the rating graph.
 */

/** Highest first, so the first one a score reaches is its tier. */
export const TIERS = [
  { key: 'elite', from: 700, color: '#6366f1' },
  { key: 'advanced', from: 600, color: '#06b6d4' },
  { key: 'intermediate', from: 500, color: '#22c55e' },
  { key: 'basic', from: 0, color: '#94a3b8' },
];

const BASIC = TIERS[TIERS.length - 1];

/** The tier of a score; no score yet is Basic. */
export function tierOf(score) {
  const value = Number(score);
  if (score == null || score === '' || Number.isNaN(value)) return BASIC;
  return TIERS.find((tier) => value >= tier.from) ?? BASIC;
}

/** The tier with this key, for a `user.tier` the API sent; anything else is Basic. */
export const tierByKey = (key) => TIERS.find((tier) => tier.key === key) ?? BASIC;
