// --- Today: running timer ---
// Elapsed time comes from the server at page load; the browser only adds the time since then,
// so a device with a different clock or time zone still shows the right value.
const loadedAt = Date.now();

function pad(n) {
  return String(n).padStart(2, '0');
}

function hm(seconds) {
  return `${Math.floor(seconds / 3600)}h ${pad(Math.floor((seconds % 3600) / 60))}m`;
}

function hms(seconds) {
  return `${Math.floor(seconds / 3600)}:${pad(Math.floor((seconds % 3600) / 60))}:${pad(seconds % 60)}`;
}

const banner = document.querySelector('[data-elapsed]');
if (banner) {
  const card = document.querySelector('.lesson-card[data-ticking]');
  const tick = () => {
    const since = Math.floor((Date.now() - loadedAt) / 1000);
    banner.textContent = hms(Number(banner.dataset.elapsed) + since);
    if (card) {
      const seconds = Number(card.dataset.seconds) + since;
      card.querySelector('[data-studied]').textContent = hm(seconds);
      card.querySelector('[data-fill]').style.width =
        `${Math.min(100, (100 * seconds) / Number(card.dataset.target))}%`;
      card.classList.toggle('is-done', seconds >= Number(card.dataset.target));
    }
  };
  tick();
  setInterval(tick, 1000);
}

// Pick up a timer started or stopped on another device when coming back to the page.
if (document.getElementById('today')) {
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) location.reload();
  });
}

// --- Today: monthly check table ---
document.querySelectorAll('.check-box').forEach((box) => {
  box.addEventListener('change', async () => {
    let ok = false;
    try {
      const res = await fetch(`/checks/${box.dataset.lessonId}/${box.dataset.date}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: box.checked }),
      });
      ok = res.ok;
    } catch (e) {
      // offline or server unreachable
    }
    if (!ok) box.checked = !box.checked;
    const row = box.closest('tr');
    const boxes = [...row.querySelectorAll('.check-box')];
    const done = boxes.filter((b) => b.checked).length;
    row.querySelector('[data-result-days]').textContent = done;
    row.querySelector('[data-result-pct]').textContent = Math.round((100 * done) / boxes.length);
  });
});

// --- Report / Compare: grouped bar chart ---
const CHART_COLORS = {
  report: ['#2a78d6', '#9a998f'],
  compare: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300'],
};

const chartData = document.getElementById('chart-data');
if (chartData) {
  const { kind, labels, datasets } = JSON.parse(chartData.textContent);
  const css = getComputedStyle(document.documentElement);
  Chart.defaults.color = css.getPropertyValue('--muted').trim();
  datasets.forEach((ds, i) => {
    ds.backgroundColor = CHART_COLORS[kind][i];
    ds.borderRadius = 4;
  });
  new Chart(document.getElementById('chart'), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      maintainAspectRatio: false,
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, title: { display: true, text: 'Hours' }, grid: { color: css.getPropertyValue('--border').trim() } },
      },
      plugins: {
        tooltip: {
          callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)} h` },
        },
      },
    },
  });
}
