const monthId = document.currentScript.getAttribute('data-month-id');
const todayStr = document.currentScript.getAttribute('data-today');

function pct(done, total) {
  return total ? Math.round((100 * done) / total) : 0;
}

function updateHabitProgress(box) {
  const row = box.closest('[data-habit-row]');
  if (!row) return;
  const boxes = row.querySelectorAll('.toggle-box');
  const done = [...boxes].filter((b) => b.checked).length;
  const p = pct(done, boxes.length);
  const fill = row.querySelector('[data-habit-fill]');
  const label = row.querySelector('[data-habit-pct]');
  if (fill) fill.style.setProperty('--target', `${p}%`);
  if (label) label.textContent = `${p}%`;
}

function updateWeekProgress(box) {
  const week = box.getAttribute('data-week');
  const boxes = document.querySelectorAll(`.toggle-box[data-week="${week}"]`);
  const done = [...boxes].filter((b) => b.checked).length;
  const total = boxes.length;
  const p = pct(done, total);
  const fill = document.querySelector(`[data-week-fill="${week}"]`);
  const label = document.querySelector(`[data-week-pct="${week}"]`);
  if (fill) fill.style.setProperty('--target', `${p}%`);
  if (label) label.textContent = `${p}% (${done}/${total})`;
}

function updateOverallProgress() {
  const boxes = document.querySelectorAll('.toggle-box');
  const done = [...boxes].filter((b) => b.checked).length;
  const total = boxes.length;
  const p = pct(done, total);
  const ring = document.getElementById('overall-ring');
  const value = document.getElementById('overall-ring-value');
  const doneEl = document.getElementById('overall-done');
  if (ring) ring.style.setProperty('--pct', p);
  if (value) value.textContent = `${p}%`;
  if (doneEl) doneEl.textContent = done;
}

function updateTodayProgress(box) {
  const ring = document.getElementById('today-ring');
  if (!ring) return;
  const date = box.getAttribute('data-date');
  if (date !== todayStr) return;
  const sameDayBoxes = document.querySelectorAll(`.toggle-box[data-date="${date}"]`);
  const done = [...sameDayBoxes].filter((b) => b.checked).length;
  const p = pct(done, sameDayBoxes.length);
  const value = document.getElementById('today-ring-value');
  const doneEl = document.getElementById('today-done');
  ring.style.setProperty('--pct', p);
  if (value) value.textContent = `${p}%`;
  if (doneEl) doneEl.textContent = done;
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.toggle-box').forEach((box) => {
    box.addEventListener('change', async () => {
      const entryId = box.getAttribute('data-entry-id');
      const prevChecked = !box.checked;
      box.disabled = true;
      try {
        const res = await fetch(`/months/${monthId}/grid/entries/${entryId}/toggle`, {
          method: 'POST',
        });
        if (!res.ok) {
          box.checked = prevChecked;
        }
      } catch (e) {
        box.checked = prevChecked;
      } finally {
        box.disabled = false;
        updateHabitProgress(box);
        updateWeekProgress(box);
        updateOverallProgress();
        updateTodayProgress(box);
      }
    });
  });

  document.querySelectorAll('.note-input').forEach((input) => {
    let lastSaved = input.value;
    input.addEventListener('blur', async () => {
      if (input.value === lastSaved) return;
      const date = input.getAttribute('data-date');
      try {
        const res = await fetch(`/months/${monthId}/notes/${date}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ note: input.value }),
        });
        if (res.ok) {
          lastSaved = input.value;
          input.classList.add('saved-flash');
          setTimeout(() => input.classList.remove('saved-flash'), 600);
        }
      } catch (e) {
        // leave value as-is; user can retry
      }
    });
  });
});
