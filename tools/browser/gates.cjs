#!/usr/bin/env node
/* 真浏览器门禁（Playwright Chromium + axe-core）。由 tools/ledger-run.py 调用，也可单独跑：
 *   node tools/browser/gates.cjs spec.json
 * spec: { base_url, pages: ["index.html", ...], out_dir, cfg: {browser: {...}} }
 * stdout 输出一个 JSON：{ engine, gates: { <gate_id>: { verdict, evidence: [...] } } }
 *
 * 门禁：
 *   G2   触控目标：移动视口下可见可交互元素 ≥ min_target_px（句中内联链接豁免并列出）
 *   G3   零横向截断：移动视口 scrollWidth ≤ 视口宽，且无元素越出视口（overflow-x:hidden 静默裁剪也算）
 *   G9   真机渲染复验：桌面＋移动、生产 CSP 下，控制台零错误零警告、无页面异常、无 CSP 拦截、
 *        站内资源无 4xx/5xx/加载失败、页面有可见文字；截图存档
 *   A4   键盘可达：Tab 走查可达全部可聚焦元素，且每个元素聚焦时有可见焦点指示（outline/box-shadow）
 *   M4   减少动态效果：reduce 下全部 transition/animation 时长 ≤ reduced_motion_max_ms、无无限循环动画，
 *        且页面文字与可见元素数和正常模式一致（替代不是藏内容）
 *   T5   CTA 单行：按钮类元素文字不折行（桌面＋移动）
 *   G16  axe-core WCAG 自动扫描：浅色＋深色两种配色下，按 axe_tags 零违规
 *   M1   关动效静态帧：只生成截图（animations: disabled）作为证据，结论仍是 waived，待人工目检
 * 任一页面加载失败 -> 该页涉及的门禁 fail（没测不算过）。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const cfg = spec.cfg.browser;
const [MW, MH] = cfg.viewports.mobile;
const [DW, DH] = cfg.viewports.desktop;
const AXE_SRC = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const ENGINE = `playwright ${require('playwright/package.json').version} chromium + axe-core ${require('axe-core/package.json').version}`;
fs.mkdirSync(spec.out_dir, { recursive: true });

const R = {};
for (const g of ['G2', 'G3', 'G9', 'A4', 'M4', 'T5', 'G16', 'M1']) R[g] = { problems: [], checked: 0, artifacts: [] };
const slug = (p) => p.replace(/[^\w.-]+/g, '_');

function describe() {
  // 在页面里注册一个给元素生成短描述的函数
  window.__qaDesc = (el) => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    else if (el.classList.length) s += '.' + [...el.classList].slice(0, 2).join('.');
    const t = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 24);
    return t ? `${s}「${t}」` : s;
  };
  window.__qaVisible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), select:not([disabled]), ' +
  'textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]';
const INTERACTIVE = FOCUSABLE + ', [role=button], [role=link], [onclick]';
const CTA = 'button, [role=button], input[type=submit], input[type=button], a[class*="btn"], a[class*="button"], a[class*="cta"], .cta';

async function open(browser, opts, rel) {
  const ctx = await browser.newContext(opts);
  await ctx.addInitScript(() => {
    window.__csp = [];
    document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(`${e.violatedDirective} ${e.blockedURI || 'inline'}`));
  });
  await ctx.addInitScript(describe);
  const page = await ctx.newPage();
  const log = { console: [], errors: [], requests: [] };
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') log.console.push(`${m.type()}: ${m.text().slice(0, 120)}`); });
  page.on('pageerror', (e) => log.errors.push(String(e.message || e).slice(0, 120)));
  page.on('requestfailed', (r) => { if (r.url().startsWith(spec.base_url)) log.requests.push(`failed ${r.url().slice(spec.base_url.length)}`); });
  page.on('response', (r) => { if (r.url().startsWith(spec.base_url) && r.status() >= 400) log.requests.push(`${r.status()} ${r.url().slice(spec.base_url.length)}`); });
  const resp = await page.goto(spec.base_url + '/' + rel, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(150);
  if (!resp || resp.status() >= 400) throw new Error(`HTTP ${resp ? resp.status() : 'no response'}`);
  return { ctx, page, log };
}

async function renderChecks(page, log, rel, label) {
  R.G9.checked++;
  const text = await page.evaluate(() => (document.body ? document.body.innerText.trim().length : 0));
  const csp = await page.evaluate(() => window.__csp);
  const p = R.G9.problems;
  if (!text) p.push(`${rel}@${label}: 页面无可见文字`);
  for (const c of log.console) p.push(`${rel}@${label}: console ${c}`);
  for (const e of log.errors) p.push(`${rel}@${label}: pageerror ${e}`);
  for (const q of log.requests) p.push(`${rel}@${label}: 资源 ${q}`);
  for (const v of csp) p.push(`${rel}@${label}: CSP 拦截 ${v}`);
}

async function ctaChecks(page, rel, label) {
  R.T5.checked++;
  const wrapped = await page.evaluate((sel) => [...document.querySelectorAll(sel)].filter(__qaVisible).filter((el) => {
    if (el.tagName === 'INPUT') return false;
    const r = document.createRange();
    r.selectNodeContents(el);
    const tops = new Set([...r.getClientRects()].filter((x) => x.width > 0).map((x) => Math.round(x.top)));
    return tops.size > 1;
  }).map(__qaDesc), CTA);
  for (const w of wrapped) R.T5.problems.push(`${rel}@${label}: ${w} 文字折行`);
}

async function axeChecks(page, rel, label) {
  R.G16.checked++;
  await page.addScriptTag({ content: AXE_SRC });
  const res = await page.evaluate((tags) => axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations'] }), cfg.axe_tags);
  const file = path.join(spec.out_dir, `axe-${label}-${slug(rel)}.json`);
  fs.writeFileSync(file, JSON.stringify(res.violations, null, 1));
  R.G16.artifacts.push(file);
  for (const v of res.violations) R.G16.problems.push(`${rel}@${label}: ${v.id}（${v.impact}）×${v.nodes.length} ${v.nodes[0] ? v.nodes[0].target.join(' ') : ''}`);
}

async function mobileChecks(page, rel) {
  R.G3.checked++;
  const over = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const out = [];
    if (document.documentElement.scrollWidth > vw + 1) out.push(`scrollWidth=${document.documentElement.scrollWidth} > ${vw}`);
    for (const el of document.body.querySelectorAll('*')) {
      if (!__qaVisible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width <= 1 && r.height <= 1) continue; // 视觉隐藏（sr-only）
      if (r.right <= 0) continue; // 整体移到左侧屏外（跳转链接）
      if (r.right <= vw + 1 && r.left >= -1) continue;
      let p = el.parentElement, scroller = false;
      while (p && p !== document.body) {
        if (['auto', 'scroll'].includes(getComputedStyle(p).overflowX)) { scroller = true; break; }
        p = p.parentElement;
      }
      if (!scroller) out.push(`${__qaDesc(el)} 越界 left=${Math.round(r.left)} right=${Math.round(r.right)}`);
      if (out.length >= 10) break;
    }
    return out;
  });
  for (const o of over) R.G3.problems.push(`${rel}@${MW}px: ${o}`);

  R.G2.checked++;
  const small = await page.evaluate(([sel, min]) => {
    const out = { bad: [], exempt: [] };
    for (const el of new Set(document.querySelectorAll(sel))) {
      if (!__qaVisible(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.width >= min && r.height >= min) continue;
      const cs = getComputedStyle(el);
      const parentText = (el.parentElement && el.parentElement.innerText || '').trim().length;
      const ownText = (el.innerText || '').trim().length;
      if (el.tagName === 'A' && cs.display === 'inline' && parentText > ownText) { out.exempt.push(__qaDesc(el)); continue; }
      out.bad.push(`${__qaDesc(el)} ${Math.round(r.width)}×${Math.round(r.height)}`);
    }
    return out;
  }, [INTERACTIVE, cfg.min_target_px]);
  for (const b of small.bad) R.G2.problems.push(`${rel}@${MW}px: ${b} < ${cfg.min_target_px}`);
  if (small.exempt.length) R.G2.exempt = (R.G2.exempt || []).concat(small.exempt.map((e) => `${rel}: ${e}`));
}

async function keyboardChecks(page, rel) {
  R.A4.checked++;
  const n = await page.evaluate((sel) => {
    const els = [...document.querySelectorAll(sel)].filter(__qaVisible);
    els.forEach((el, i) => el.setAttribute('data-qa-focus', String(i)));
    return els.length;
  }, FOCUSABLE);
  if (!n) return;
  const reached = new Set();
  for (let i = 0; i < n + 3; i++) {
    await page.keyboard.press('Tab');
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body || !el.hasAttribute('data-qa-focus')) return null;
      const cs = getComputedStyle(el);
      const ring = (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== 'none';
      return { id: el.getAttribute('data-qa-focus'), ring, desc: __qaDesc(el) };
    });
    if (!info) continue;
    if (!reached.has(info.id) && !info.ring) R.A4.problems.push(`${rel}: ${info.desc} 聚焦时无可见焦点指示`);
    reached.add(info.id);
  }
  if (reached.size < n) {
    const missed = await page.evaluate((ids) => [...document.querySelectorAll('[data-qa-focus]')]
      .filter((el) => !ids.includes(el.getAttribute('data-qa-focus'))).map(__qaDesc).slice(0, 5), [...reached]);
    R.A4.problems.push(`${rel}: Tab 未到达 ${n - reached.size}/${n} 个元素，如 ${missed.join('、')}`);
  }
}

async function snapshot(page) {
  return page.evaluate(() => ({
    text: document.body.innerText.replace(/\s+/g, ' ').trim(),
    visible: [...document.body.querySelectorAll('*')].filter(__qaVisible).length,
  }));
}

async function reducedMotionChecks(browser, rel, normal) {
  R.M4.checked++;
  const { ctx, page } = await open(browser, { viewport: { width: DW, height: DH }, reducedMotion: 'reduce' }, rel);
  try {
    const maxMs = cfg.reduced_motion_max_ms;
    const slow = await page.evaluate((max) => {
      const ms = (v) => v.split(',').map((t) => t.trim()).map((t) => (t.endsWith('ms') ? parseFloat(t) : parseFloat(t) * 1000));
      const out = [];
      for (const el of document.querySelectorAll('*')) {
        const cs = getComputedStyle(el);
        const tr = Math.max(...ms(cs.transitionDuration));
        const an = cs.animationName !== 'none' ? Math.max(...ms(cs.animationDuration)) : 0;
        if (tr > max) out.push(`${__qaDesc(el)} transition ${tr}ms`);
        if (an > max) out.push(`${__qaDesc(el)} animation ${an}ms`);
        if (out.length >= 10) break;
      }
      for (const a of document.getAnimations()) {
        const t = a.effect && a.effect.getComputedTiming();
        if (t && (t.iterations === Infinity || t.duration > max)) out.push(`running animation ${a.animationName || a.id || ''} ${t.duration}ms ×${t.iterations}`);
      }
      return out;
    }, maxMs);
    for (const s of slow) R.M4.problems.push(`${rel}@reduce: ${s} > ${maxMs}ms`);
    const reduced = await snapshot(page);
    if (reduced.text !== normal.text) R.M4.problems.push(`${rel}@reduce: 页面文字与正常模式不一致（替代把内容藏了）`);
    if (reduced.visible !== normal.visible) R.M4.problems.push(`${rel}@reduce: 可见元素 ${reduced.visible} ≠ 正常 ${normal.visible}`);
  } finally {
    await ctx.close();
  }
}

async function shot(page, rel, label) {
  const file = path.join(spec.out_dir, `${label}-${slug(rel)}.png`);
  await page.screenshot({ path: file, fullPage: true, animations: 'disabled' });
  R.M1.artifacts.push(file);
  R.G9.artifacts.push(file);
}

async function perPage(browser, rel) {
  const steps = [
    async () => { // 桌面浅色：渲染、CTA、键盘、截图、axe
      const { ctx, page, log } = await open(browser, { viewport: { width: DW, height: DH }, colorScheme: 'light' }, rel);
      try {
        await renderChecks(page, log, rel, `${DW}px`);
        await ctaChecks(page, rel, `${DW}px`);
        const normal = await snapshot(page);
        await shot(page, rel, `desktop-${DW}`);
        await keyboardChecks(page, rel);
        await reducedMotionChecks(browser, rel, normal);
      } finally { await ctx.close(); }
    },
    async () => { // 移动：渲染、横滚、触控、CTA、截图
      const { ctx, page, log } = await open(browser, { viewport: { width: MW, height: MH }, hasTouch: true, colorScheme: 'light' }, rel);
      try {
        await renderChecks(page, log, rel, `${MW}px`);
        await mobileChecks(page, rel);
        await ctaChecks(page, rel, `${MW}px`);
        await shot(page, rel, `mobile-${MW}`);
      } finally { await ctx.close(); }
    },
    async () => { // axe 两种配色（bypassCSP 只为注入 axe；CSP 本身由 G9 在不绕过的上下文里测）
      for (const scheme of ['light', 'dark']) {
        const { ctx, page } = await open(browser, { viewport: { width: DW, height: DH }, colorScheme: scheme, bypassCSP: true }, rel);
        try { await axeChecks(page, rel, scheme); } finally { await ctx.close(); }
      }
    },
  ];
  for (const step of steps) {
    try {
      await step();
    } catch (e) {
      for (const g of ['G2', 'G3', 'G9', 'A4', 'M4', 'T5', 'G16']) R[g].problems.push(`${rel}: 页面检查失败（${String(e.message || e).split('\n')[0].slice(0, 100)}）`);
    }
  }
}

(async () => {
  const browser = await chromium.launch();
  try {
    for (const rel of spec.pages) await perPage(browser, rel);
  } finally {
    await browser.close();
  }
  const gates = {};
  for (const [g, r] of Object.entries(R)) {
    const ev = [{ type: 'cmd', ref: `${ENGINE}: ${spec.pages.length} 页` }];
    if (g === 'M1') {
      ev.push({ type: 'note', ref: `已生成关动效截图 ${r.artifacts.length} 张，待人工目检（机器不判构图）` });
      r.artifacts.forEach((a) => ev.push({ type: 'artifact', ref: a }));
      gates[g] = { verdict: 'waived', evidence: ev };
      continue;
    }
    ev.push({ type: 'output', ref: `checked=${r.checked} problems=${r.problems.length}` + (r.problems.length ? ` e.g. ${r.problems.slice(0, 3).join('; ')}` : '') });
    if (r.exempt && r.exempt.length) ev.push({ type: 'note', ref: `句中内联链接豁免 ${r.exempt.length} 个：${r.exempt.slice(0, 5).join('、')}` });
    r.artifacts.forEach((a) => ev.push({ type: 'artifact', ref: a }));
    gates[g] = { verdict: r.problems.length || !r.checked ? 'fail' : 'pass', evidence: ev, problems: r.problems };
  }
  process.stdout.write(JSON.stringify({ engine: ENGINE, gates }));
})().catch((e) => {
  process.stderr.write(String(e && e.stack || e));
  process.exit(3);
});
