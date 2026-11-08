// Renderiza o vídeo quadro a quadro no Chromium headless.
// Uso: node render.js [saida/frames] [workers]      (prévia: node render.js --at 12.5,41.7)
// Se THREE_DIR apontar para node_modules/three local, o three.js é servido offline.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');

const args = process.argv.slice(2);
const atIdx = args.indexOf('--at');
const outDir = path.resolve(__dirname, atIdx >= 0 ? 'saida/previa' : (args[0] || 'saida/frames'));
const workers = parseInt(args[1] || '3', 10);
const THREE_DIR = process.env.THREE_DIR;
fs.mkdirSync(outDir, { recursive: true });
const TL = JSON.parse(fs.readFileSync(path.join(__dirname, 'timeline.js'), 'utf8').replace(/^[^=]*=/, '').trim().replace(/;$/, ''));

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 720, height: 1280 } });
  if (THREE_DIR) await page.route('https://unpkg.com/**', (r) => {
    const rel = r.request().url().replace(/^https:\/\/unpkg\.com\/three@[^/]+\//, '');
    r.fulfill({ body: fs.readFileSync(path.join(THREE_DIR, rel)), contentType: 'application/javascript' });
  });
  page.on('pageerror', (e) => console.error('pageerror:', e.message));
  await page.addInitScript(() => { window.RENDER_MODE = true; });
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
  return page;
}
async function grab(page, t, file) {
  const data = await page.evaluate((tt) => window.frameJPEG(tt), t);
  fs.writeFileSync(file, Buffer.from(data.split(',')[1], 'base64'));
}

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  if (atIdx >= 0) {
    const page = await openPage(browser);
    for (const t of args[atIdx + 1].split(',').map(Number)) await grab(page, t, path.join(outDir, `t_${t.toFixed(2)}.jpg`));
    await browser.close(); return;
  }
  const total = Math.round(TL.duration * TL.fps);
  let next = 0, done = 0; const t0 = Date.now();
  await Promise.all(Array.from({ length: workers }, async () => {
    const page = await openPage(browser);
    while (next < total) {
      const f = next++;
      await grab(page, f / TL.fps, path.join(outDir, `f_${String(f).padStart(5, '0')}.jpg`));
      if (++done % 150 === 0) console.log(`${done}/${total} quadros (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    }
  }));
  await browser.close();
  console.log('ok', total, 'quadros');
})();
