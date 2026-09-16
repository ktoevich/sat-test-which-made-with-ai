/**
 * The profile's charts, drawn as inline SVG from the analytics the API returns.
 *
 * The rating chart plots the rating after every finished test, on a scale
 * banded by tier, with a tooltip per point. The topics chart shows how many
 * questions of each content domain the student has got right, as a donut or
 * as bars; a domain is clickable, to practise it.
 */

import { el, escapeHtml } from '../../core/dom.js';
import { sectionName, t } from '../../core/i18n.js';

const TIER_BANDS = [
  { name: 'Newbie', from: 800, to: 1200, color: '#94a3b8' },
  { name: 'Pupil', from: 1200, to: 1400, color: '#22c55e' },
  { name: 'Specialist', from: 1400, to: 1600, color: '#06b6d4' },
  { name: 'Expert', from: 1600, to: 1900, color: '#6366f1' },
  { name: 'Candidate Master', from: 1900, to: 2100, color: '#d946ef' },
  { name: 'Master', from: 2100, to: 2400, color: '#f97316' },
];

const DOMAIN_COLORS = {
  Algebra: '#f87171',
  'Advanced Math': '#c084fc',
  'Problem-Solving and Data Analysis': '#60a5fa',
  'Geometry and Trigonometry': '#34d399',
  'Craft and Structure': '#fb923c',
  'Information and Ideas': '#38bdf8',
  'Expression of Ideas': '#a3e635',
  'Standard English Conventions': '#f472b6',
};

const tierColor = (rating) =>
  [...TIER_BANDS].reverse().find((band) => rating >= band.from)?.color ?? TIER_BANDS[0].color;

const formatDate = (iso) => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? String(iso)
    : date.toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: '2-digit' });
};

/** The numbers summarising a rating history: tests, peak, best gain, average score. */
export function ratingSummary(points) {
  if (!points.length) return null;
  const peak = points.reduce((best, p) => (p.rating_after > best.rating_after ? p : best), points[0]);
  const bestGain = Math.max(...points.map((p) => (p.rating_after ?? 0) - (p.rating_before ?? 0)));
  const average = Math.round(points.reduce((sum, p) => sum + p.score, 0) / points.length);
  return { tests: points.length, peak: peak.rating_after, peakAt: peak.taken_at, bestGain, average };
}

/**
 * Draw the rating chart into `container`; `tooltip` is the element hovering a
 * point fills. Returns nothing; an empty history draws a hint instead.
 */
export function renderRatingChart(container, tooltip, points) {
  container.replaceChildren();
  tooltip?.classList.add('hidden');
  const data = (points ?? []).filter((p) => p.rating_after != null);
  if (!data.length) {
    container.append(el('div', { className: 'chart-empty', text: t('chart_rating_empty') }));
    return;
  }

  const width = 960;
  const height = 340;
  const pad = { left: 56, right: 140, top: 30, bottom: 44 };
  const chartW = width - pad.left - pad.right;
  const chartH = height - pad.top - pad.bottom;

  const ratings = data.flatMap((p) => [p.rating_after, p.rating_before ?? p.rating_after]);
  const low = Math.min(...ratings, 1100);
  const high = Math.max(...ratings, 1500);
  const minRating = Math.floor((low - 100) / 100) * 100;
  const maxRating = Math.ceil((high + 100) / 100) * 100;
  const y = (value) => pad.top + chartH - ((value - minRating) / (maxRating - minRating)) * chartH;
  const x = (index) => (data.length === 1 ? pad.left + chartW / 2 : pad.left + (index / (data.length - 1)) * chartW);

  let svg = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(t('chart_rating_title'))}">`;
  svg += `<defs>
    <linearGradient id="rating-area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.25"></stop>
      <stop offset="100%" stop-color="#3b82f6" stop-opacity="0"></stop>
    </linearGradient>
  </defs>`;

  // Tier bands, only the ones inside the visible range.
  TIER_BANDS.forEach((band) => {
    const top = Math.max(band.from, minRating);
    const bottom = Math.min(band.to, maxRating);
    if (bottom <= top) return;
    svg += `<rect x="${pad.left}" y="${y(bottom)}" width="${chartW}" height="${y(top) - y(bottom)}" fill="${band.color}" opacity="0.08"></rect>`;
    svg += `<text x="${pad.left + chartW + 10}" y="${(y(top) + y(bottom)) / 2 + 4}" font-size="11" font-weight="700" fill="${band.color}">${escapeHtml(t(`tier_${band.name}`))}</text>`;
  });

  for (let r = minRating; r <= maxRating; r += 100) {
    svg += `<line x1="${pad.left}" y1="${y(r)}" x2="${pad.left + chartW}" y2="${y(r)}" stroke="currentColor" stroke-opacity="0.12" stroke-dasharray="${r % 200 ? '3,3' : 'none'}"></line>`;
    svg += `<text x="${pad.left - 8}" y="${y(r) + 4}" text-anchor="end" font-size="11" fill="currentColor" opacity="0.6">${r}</text>`;
  }
  svg += `<rect x="${pad.left}" y="${pad.top}" width="${chartW}" height="${chartH}" fill="none" stroke="currentColor" stroke-opacity="0.2" rx="3"></rect>`;

  const coords = data.map((p, i) => ({ x: x(i), y: y(p.rating_after), point: p }));
  const line = coords.map((c, i) => `${i ? 'L' : 'M'} ${c.x} ${c.y}`).join(' ');
  svg += `<path d="${line} L ${coords[coords.length - 1].x} ${y(minRating)} L ${coords[0].x} ${y(minRating)} Z" fill="url(#rating-area)"></path>`;
  svg += `<path d="${line}" fill="none" stroke="#3b82f6" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>`;

  const peak = Math.max(...data.map((p) => p.rating_after));
  coords.forEach((c, i) => {
    const isLast = i === coords.length - 1;
    const isPeak = c.point.rating_after === peak;
    svg += `<line x1="${c.x}" y1="${pad.top + chartH}" x2="${c.x}" y2="${pad.top + chartH + 6}" stroke="currentColor" stroke-opacity="0.35"></line>`;
    if (data.length <= 12 || i % Math.ceil(data.length / 12) === 0 || isLast) {
      svg += `<text x="${c.x}" y="${pad.top + chartH + 22}" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.7">${escapeHtml(formatDate(c.point.taken_at))}</text>`;
    }
    if (isPeak) {
      svg += `<g transform="translate(${c.x}, ${c.y - 26})"><rect x="-30" y="-11" width="60" height="20" rx="10" fill="#f59e0b"></rect><text x="0" y="3" text-anchor="middle" font-size="11" font-weight="800" fill="#fff">🏆 ${peak}</text></g>`;
    } else if (isLast) {
      svg += `<g transform="translate(${c.x}, ${c.y - 24})"><rect x="-24" y="-10" width="48" height="18" rx="9" fill="#06b6d4"></rect><text x="0" y="3" text-anchor="middle" font-size="10.5" font-weight="800" fill="#fff">${c.point.rating_after}</text></g>`;
    }
    svg += `<g class="rating-point" data-index="${i}"><circle cx="${c.x}" cy="${c.y}" r="14" fill="transparent"></circle><circle cx="${c.x}" cy="${c.y}" r="${isPeak || isLast ? 6.5 : 5}" fill="var(--color-surface)" stroke="${isPeak ? '#f59e0b' : tierColor(c.point.rating_after)}" stroke-width="2.8"></circle></g>`;
  });
  svg += '</svg>';
  container.innerHTML = svg;

  if (!tooltip) return;
  container.querySelectorAll('.rating-point').forEach((node) => {
    node.addEventListener('mouseenter', () => {
      const point = data[Number(node.dataset.index)];
      const delta = (point.rating_after ?? 0) - (point.rating_before ?? point.rating_after);
      tooltip.innerHTML = `
        <div><strong>${escapeHtml(sectionName(point.section))}</strong> · ${escapeHtml(formatDate(point.taken_at))}</div>
        <div>${escapeHtml(t('col_score'))}: <strong>${point.score}</strong> (${point.correct}/${point.total})</div>
        <div>${escapeHtml(t('col_rating'))}: <strong>${point.rating_before ?? '–'} → ${point.rating_after}</strong>
          <span class="${delta >= 0 ? 'rating-delta--up' : 'rating-delta--down'}">(${delta >= 0 ? '+' : ''}${delta})</span></div>`;
      tooltip.classList.remove('hidden');
      const box = container.getBoundingClientRect();
      const target = node.getBoundingClientRect();
      let left = target.left - box.left + target.width / 2 - tooltip.offsetWidth / 2;
      left = Math.max(8, Math.min(left, box.width - tooltip.offsetWidth - 8));
      let top = target.top - box.top - tooltip.offsetHeight - 10;
      if (top < 0) top = target.bottom - box.top + 10;
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
    });
    node.addEventListener('mouseleave', () => tooltip.classList.add('hidden'));
  });
}

/**
 * Draw the domains chart into `container`. `topics` is the API's list of
 * `{section, domain, correct, seen}`; `mode` is `circle` or `bars`; `onPick`
 * gets `(section, domain)` when a domain is clicked.
 */
export function renderTopicsChart(container, topics, mode, onPick) {
  container.replaceChildren();
  const data = (topics ?? []).filter((topic) => topic.correct > 0);
  if (!data.length) {
    container.append(el('div', { className: 'chart-empty', text: t('chart_topics_empty') }));
    return;
  }
  const total = data.reduce((sum, topic) => sum + topic.correct, 0);
  const colorOf = (topic) => DOMAIN_COLORS[topic.domain] ?? '#94a3b8';
  const pick = (topic) => () => onPick?.(topic.section, topic.domain);

  if (mode === 'bars') {
    const most = Math.max(...data.map((topic) => topic.correct));
    const list = el('div', { className: 'topics-bars' });
    data.forEach((topic, index) => {
      const row = el('div', { className: 'topics-bar', title: topic.domain });
      row.append(
        el('div', { className: 'topics-bar__row' }, [
          el('span', {}, [
            el('span', { className: 'topics-legend__swatch', style: `background:${colorOf(topic)}` }),
            el('strong', { text: `#${index + 1} ${topic.domain}` }),
            el('span', { className: 'topics-legend__numbers', text: ` · ${sectionName(topic.section, { short: true })}` }),
          ]),
          el('span', { className: 'topics-legend__numbers', text: `${t('chart_right_of', { right: topic.correct, seen: topic.seen })} (${Math.round((topic.correct / total) * 100)}%)` }),
        ]),
        el('div', { className: 'topics-bar__track' }, [
          el('div', { className: 'topics-bar__fill', style: `width:${Math.max(4, (topic.correct / most) * 100)}%;background:${colorOf(topic)}` }),
        ]),
      );
      row.addEventListener('click', pick(topic));
      list.append(row);
    });
    container.append(list);
    return;
  }

  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const outer = 96;
  const inner = 58;
  let angle = -Math.PI / 2;
  let paths = '';
  data.forEach((topic, index) => {
    const slice = (topic.correct / total) * 2 * Math.PI;
    const end = angle + slice;
    const large = slice > Math.PI ? 1 : 0;
    const p = (r, a) => `${cx + r * Math.cos(a)} ${cy + r * Math.sin(a)}`;
    // A single full slice needs two arcs; nudge the end a hair short of a full turn.
    const stop = data.length === 1 ? end - 0.0001 : end;
    paths += `<path class="topics-donut__slice" data-index="${index}" d="M ${p(outer, angle)} A ${outer} ${outer} 0 ${large} 1 ${p(outer, stop)} L ${p(inner, stop)} A ${inner} ${inner} 0 ${large} 0 ${p(inner, angle)} Z" fill="${colorOf(topic)}" stroke="var(--color-surface)" stroke-width="2"><title>${escapeHtml(topic.domain)}: ${topic.correct}</title></path>`;
    angle = end;
  });
  const donut = el('div', { className: 'topics-donut' });
  donut.innerHTML = `<svg viewBox="0 0 ${size} ${size}" role="img" aria-label="${escapeHtml(t('chart_topics_title'))}">${paths}
    <text x="${cx}" y="${cy - 4}" text-anchor="middle" font-size="26" font-weight="900" fill="var(--color-text-strong)">${total}</text>
    <text x="${cx}" y="${cy + 16}" text-anchor="middle" font-size="11" font-weight="600" fill="var(--color-text-muted)">${escapeHtml(t('chart_total_right'))}</text>
  </svg>`;
  const legend = el('div', { className: 'topics-legend' });
  data.forEach((topic) => {
    const item = el('div', { className: 'topics-legend__item', title: topic.domain }, [
      el('span', {}, [
        el('span', { className: 'topics-legend__swatch', style: `background:${colorOf(topic)}` }),
        el('strong', { text: topic.domain }),
        el('span', { className: 'topics-legend__numbers', text: ` · ${sectionName(topic.section, { short: true })}` }),
      ]),
      el('span', { className: 'topics-legend__numbers', text: `${t('chart_right_of', { right: topic.correct, seen: topic.seen })} (${Math.round((topic.correct / total) * 100)}%)` }),
    ]);
    item.addEventListener('click', pick(topic));
    legend.append(item);
  });
  donut.append(legend);
  donut.querySelectorAll('.topics-donut__slice').forEach((slice) => {
    slice.addEventListener('click', pick(data[Number(slice.dataset.index)]));
  });
  container.append(donut);
}

/** The colour a domain is drawn in, for chips elsewhere. */
export const domainColor = (domain) => DOMAIN_COLORS[domain] ?? '#94a3b8';
