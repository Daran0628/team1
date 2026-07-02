const API = '/api/cafeteria';
let currentYear, currentMonth;
let monthData = {};

const today = new Date();
currentYear = today.getFullYear();
currentMonth = today.getMonth() + 1;

// ── 초기 로드 ──
loadTodayMenu();
loadMonth(currentYear, currentMonth);

// ── 오늘 메뉴 ──
async function loadTodayMenu() {
    const el = document.getElementById('todayMenuText');
    try {
        const res = await apiFetch(API + '/today');
        if (!res) return;
        const data = await res.json();
        if (data.isSuccess && data.result) {
            el.textContent = data.result.menu_text.split(',').map(s => s.trim()).join('\n');
            el.classList.remove('today-empty');
        } else {
            el.textContent = '오늘 등록된 메뉴가 없습니다.';
            el.classList.add('today-empty');
        }
    } catch { el.textContent = '메뉴를 불러올 수 없습니다.'; }
}

// ── 한 달 캘린더 ──
async function loadMonth(y, m) {
    document.getElementById('calendarTitle').textContent = `${y}년 ${m}월`;
    try {
        const res = await apiFetch(`${API}/month?year=${y}&month=${m}`);
        if (!res) return;
        const data = await res.json();
        monthData = {};
        if (data.isSuccess && data.result && data.result.items) {
            data.result.items.forEach(item => { monthData[item.menu_date] = item.menu_text; });
        }
    } catch {}
    renderCalendar(y, m);
}

function renderCalendar(y, m) {
    const tbody = document.getElementById('calendarBody');
    const firstDay = new Date(y, m - 1, 1).getDay();
    const lastDate = new Date(y, m, 0).getDate();
    const prevLast = new Date(y, m - 1, 0).getDate();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;

    let html = '<tr>';
    for (let i = 0; i < firstDay; i++) {
        const d = prevLast - firstDay + 1 + i;
        html += `<td class="other-month"><div class="cal-day">${d}</div></td>`;
    }
    let cell = firstDay;
    for (let d = 1; d <= lastDate; d++) {
        const dateStr = `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
        const isToday = dateStr === todayStr;
        const menu = monthData[dateStr] || '';        
        const short = menu
          ? (() => {
              const isBrunch = menu.includes('[');

              if (isBrunch) {
                const [titlePart, rest = ''] = menu.split('] ');
                const title = titlePart + ']';

                const items = rest
                  .split(',')
                  .map(s => s.trim())
                  .filter(Boolean);

                return [title, ...items].join('\n');
              }

              // 일반 메뉴
              return menu
                .split(',')
                .map(s => s.trim())
                .filter(Boolean)
                .join('\n');
            })()
          : '';
        
        html += `<td class="${isToday ? 'today' : ''}" onclick="showDetail('${dateStr}')">
            <div class="cal-day">${d}</div>
            <div class="cal-menu">${esc(short)}</div>
        </td>`;
        cell++;
        if (cell % 7 === 0 && d < lastDate) html += '</tr><tr>';
    }
    while (cell % 7 !== 0) {
        html += `<td class="other-month"><div class="cal-day">${cell - lastDate - firstDay + 1}</div></td>`;
        cell++;
    }
    html += '</tr>';
    tbody.innerHTML = html;
}

// ── 날짜 클릭 → 상세 ──
function showDetail(dateStr) {
    const menu = monthData[dateStr];
    if (!menu) return;
    document.getElementById('detailDate').textContent = dateStr;
    document.getElementById('detailText').textContent = menu.split(',').map(s => s.trim()).join('\n');
    document.getElementById('menuDetailOverlay').classList.add('active');
}
document.getElementById('menuDetailOverlay').addEventListener('click', e => {
    if (e.target === e.currentTarget) e.currentTarget.classList.remove('active');
});
document.getElementById('detailCloseBtn').addEventListener('click', () => {
    document.getElementById('menuDetailOverlay').classList.remove('active');
});

// ── 월 이동 ──
document.getElementById('btnPrevMonth').addEventListener('click', () => {
    currentMonth--;
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    loadMonth(currentYear, currentMonth);
});
document.getElementById('btnNextMonth').addEventListener('click', () => {
    currentMonth++;
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    loadMonth(currentYear, currentMonth);
});

// ── 점심 추천 ──
document.getElementById('btnRecommend').addEventListener('click', async () => {
    const resultEl = document.getElementById('recommendResult');
    const btn = document.getElementById('btnRecommend');
    const dice = document.querySelector('.dice');

    // 🎲 애니메이션 시작
    dice.classList.add('spin');
    btn.disabled = true;

    resultEl.style.display = 'none';

    try {
        const res = await apiFetch(API + '/recommend');
        if (!res) return;

        const data = await res.json();

        if (data.isSuccess && data.result) {
            const r = data.result;

            document.getElementById('recFood').textContent = r.recommendation;
            document.getElementById('recReason').textContent = r.reason;
            document.getElementById('recWeather').textContent =
                `현재 서울 ${r.temperature}°C / 강수 ${r.precipitation}mm`;

            resultEl.style.display = 'block';
        }

    } catch (e) {
        console.error(e);
    }

    // 🎲 애니메이션 종료 (결과 뜨는 타이밍과 맞춤)
    setTimeout(() => {
        dice.classList.remove('spin');
        btn.disabled = false;
    }, 800);
});

function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
