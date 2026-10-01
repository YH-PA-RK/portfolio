import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { chromium } from 'playwright';

const baseSource = execFileSync('git', ['show', `${process.env.BASE_SHA || 'origin/main'}:index.html`], { encoding: 'utf8' });
await writeFile('_site/baseline.html', baseSource);
await mkdir('layout-review', { recursive: true });
const browser = await chromium.launch();
const results = [];
const normalize = (text) => text.replace(/\s+/g, ' ').trim();

async function load(page, route) {
  await page.goto(`http://127.0.0.1:8000/portfolio/${route}`, { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => document.fonts.status === 'loaded' && document.querySelector('.profile img')?.naturalWidth > 0);
}

async function metrics(page) {
  return page.evaluate(() => {
    const box = (element) => {
      const rect = element.getBoundingClientRect();
      return { x: rect.x, y: rect.y, width: rect.width, height: rect.height, right: rect.right };
    };
    const sections = [...document.querySelectorAll('.folio-story > section')];
    const photo = document.querySelector('.profile img');
    return {
      width: innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      theme: document.documentElement.dataset.theme,
      intro: document.querySelector('.folio-lead').textContent,
      story: document.querySelector('.folio-story').textContent,
      interests: [...document.querySelectorAll('.folio-interests li')].map((li) => li.textContent),
      interestBox: box(document.querySelector('.folio-interests')),
      profileBox: box(document.querySelector('.profile')),
      photo: { ...box(photo), naturalWidth: photo.naturalWidth, naturalHeight: photo.naturalHeight },
      sections: sections.map((section) => ({ ...box(section), bodyTop: box(section.querySelector('p')).y })),
      contacts: [...document.querySelectorAll('.more-info p')].map((p) => ({ ...box(p), lineHeight: parseFloat(getComputedStyle(p).lineHeight) })),
    };
  });
}

try {
  const context = await browser.newContext({ viewport: { width: 1366, height: 1000 }, colorScheme: 'light' });
  await context.addInitScript(() => localStorage.setItem('theme', 'light'));
  const baselinePage = await context.newPage();
  await load(baselinePage, 'baseline.html');
  const baseline = await metrics(baselinePage);
  console.log('Baseline body alignment difference:', Math.abs(baseline.sections[0].bodyTop - baseline.sections[1].bodyTop).toFixed(2), 'px');
  await baselinePage.screenshot({ path: 'layout-review/before-1366-light.png', fullPage: true });
  await context.close();

  for (const width of [390, 820, 991, 992, 1366]) {
    for (const theme of ['light', 'dark']) {
      const context = await browser.newContext({ viewport: { width, height: 1000 }, colorScheme: theme });
      await context.addInitScript((value) => localStorage.setItem('theme', value), theme);
      const page = await context.newPage();
      await load(page, '');
      const current = await metrics(page);
      assert.equal(current.theme, theme);
      const contentUnchanged = normalize(current.intro) === normalize(baseline.intro)
        && normalize(current.story) === normalize(baseline.story)
        && JSON.stringify(current.interests) === JSON.stringify(baseline.interests);
      assert(current.scrollWidth <= width + 1, `Horizontal overflow at ${width}/${theme}`);
      const displayedRatio = current.photo.width / current.photo.height;
      const originalRatio = current.photo.naturalWidth / current.photo.naturalHeight;
      assert(Math.abs(displayedRatio - originalRatio) < 0.005, 'Profile photo aspect ratio changed');
      assert(current.photo.width <= (width >= 768 ? 220 : 200) + 1);
      for (const contact of current.contacts) {
        assert(contact.height <= contact.lineHeight + 1, `Contact wraps unexpectedly at ${width}/${theme}`);
      }
      if (width >= 768) {
        assert(current.interestBox.right < current.profileBox.x, 'Research interests divider must stay out of photo column');
      }
      if (width >= 992) {
        for (const row of [0, 2]) {
          assert(Math.abs(current.sections[row].y - current.sections[row + 1].y) <= 1, '2×2 section tops are not aligned');
          assert(Math.abs(current.sections[row].bodyTop - current.sections[row + 1].bodyTop) <= 1, 'Body text starts at different heights');
        }
      } else {
        for (let i = 1; i < current.sections.length; i++) {
          assert(current.sections[i].y > current.sections[i - 1].y, 'Narrow layout must stack sections');
        }
      }
      await page.screenshot({ path: `layout-review/about-${width}-${theme}.png`, fullPage: true });
      results.push({ width, theme, headingAlignment: 'pass', contactWrapping: 'pass', contentUnchanged, photoAspectRatio: 'pass' });
      console.log(`PASS ${width}px ${theme}: layout, contacts, photo ratio; approved text unchanged: ${contentUnchanged}`);
      await context.close();
    }
  }
  await writeFile('layout-review/results.json', JSON.stringify(results, null, 2));
  console.log('All 10 responsive/theme checks passed.');
} finally {
  await browser.close();
}
