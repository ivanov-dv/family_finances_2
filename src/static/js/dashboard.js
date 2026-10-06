(function () {
    const inc = JSON.parse(document.getElementById('inc-data').textContent);
    const exp = JSON.parse(document.getElementById('exp-data').textContent);

    // Копейки показываем двумя цифрами («3 500,50»), целые суммы — без дробной части.
    const fmt = v => {
        const n = Number(v);
        const hasFraction = Math.abs(n % 1) > 0.001;
        return n.toLocaleString('ru-RU', {
            minimumFractionDigits: hasFraction ? 2 : 0,
            maximumFractionDigits: 2,
        });
    };

    // Сокращённая сумма для узких плиток: 6 003,70 → «6 тыс», 1 250 000 → «1,3 млн» (полная — в title).
    const fmtCompact = v => {
        const n = Math.abs(Number(v));
        if (n >= 1e6) return (n / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 1 }) + ' млн';
        if (n >= 1e3) return Math.round(n / 1e3).toLocaleString('ru-RU') + ' тыс';
        return Math.round(n).toLocaleString('ru-RU');
    };

    // Названия статей вводят пользователи: в innerHTML их нельзя подставлять как есть (XSS).
    const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    const esc = s => String(s).replace(/[&<>"']/g, ch => HTML_ESCAPES[ch]);

    function readCSS(varName) {
        return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
    }

    // Цвета графиков берём из текущей темы приложения (data-theme), а не из системной.
    function palette() {
        const isDark = document.documentElement.dataset.theme === 'dark';
        const grid = readCSS('--border') || (isDark ? 'rgba(255,255,255,0.07)' : 'rgba(15,23,42,0.06)');
        return {
            tick: readCSS('--text-muted') || (isDark ? '#8A93A8' : '#64748B'),
            grid,
            surface: readCSS('--bg-elevated') || (isDark ? '#1F2742' : '#FFFFFF'),
            border: readCSS('--border-md') || grid,
            text: readCSS('--text-primary') || (isDark ? '#F5F7FA' : '#0F172A'),
        };
    }

    // ============== Category icon + color mapping ==============
    const catRules = [
        { keys: ['зарплат', 'оклад', 'аванс'], icon: '#i-briefcase', color: 'green', hex: '#00B884' },
        { keys: ['подработ', 'фриланс'], icon: '#i-zap', color: 'blue', hex: '#3D6BE6' },
        { keys: ['инвест', 'дивиденд', 'процент'], icon: '#i-trend-up', color: 'purple', hex: '#7C5CF0' },
        { keys: ['продукт', 'еда', 'магаз'], icon: '#i-shopping-cart', color: 'green', hex: '#00B884' },
        { keys: ['аренд', 'квартир', 'жил'], icon: '#i-home-house', color: 'orange', hex: '#F08A3D' },
        { keys: ['транспорт', 'такси', 'бенз', 'авто', 'метро'], icon: '#i-car', color: 'cyan', hex: '#0EA5E9' },
        { keys: ['развлеч', 'кино', 'театр'], icon: '#i-film', color: 'pink', hex: '#DB4F94' },
        { keys: ['коммун', 'свет', 'газ', 'вода', 'плат'], icon: '#i-zap', color: 'yellow', hex: '#EAB308' },
        { keys: ['здоров', 'медиц', 'лекарств', 'аптек'], icon: '#i-heart', color: 'red', hex: '#E63E3E' },
        { keys: ['одежд', 'обув'], icon: '#i-shirt', color: 'purple', hex: '#7C5CF0' },
        { keys: ['кафе', 'ресторан'], icon: '#i-utensils', color: 'orange', hex: '#F08A3D' },
        { keys: ['кофе'], icon: '#i-coffee', color: 'orange', hex: '#F08A3D' },
        { keys: ['образован', 'учеб', 'курс', 'книг'], icon: '#i-book', color: 'blue', hex: '#3D6BE6' },
    ];
    const fallbackColors = ['#3D6BE6', '#00B884', '#E63E3E', '#F08A3D', '#7C5CF0', '#DB4F94', '#0EA5E9', '#EAB308', '#94A3B8'];
    function getCategoryStyle(name, idx) {
        const lower = (name || '').toLowerCase();
        for (const rule of catRules) {
            if (rule.keys.some(k => lower.includes(k))) return rule;
        }
        return { icon: '#i-package', color: 'blue', hex: fallbackColors[(idx || 0) % fallbackColors.length] };
    }

    // ============== Plan vs Fact lists ==============
    function progressClass(ratio, isExpense) {
        if (isExpense) {
            if (ratio > 110) return 'is-red';
            if (ratio > 95) return 'is-yellow';
            return 'is-green';
        } else {
            if (ratio >= 100) return 'is-green';
            if (ratio >= 80) return 'is-yellow';
            return 'is-red';
        }
    }

    function renderPfList(target, data, isExpense) {
        const el = document.getElementById(target);
        if (!el) return;
        if (!data.length) {
            el.innerHTML = '<div class="pf-empty">Нет данных за этот период</div>';
            return;
        }
        el.innerHTML = data.map((d, i) => {
            const style = getCategoryStyle(d.g, i);
            // План 0 при ненулевом факте — это превышение плана, а не «ничего не сделано».
            const ratio = d.plan > 0 ? (d.fact / d.plan) * 100 : (d.fact > 0 ? Infinity : 0);
            const widthPct = Math.max(0, Math.min(ratio, 100));
            const cls = progressClass(ratio, isExpense);
            return `<div class="pf-row">
                <div class="pf-row-top">
                    <div class="pf-row-name">
                        <span class="cat-icon-32 ${style.color}">
                            <svg class="icon icon-sm"><use href="${style.icon}"/></svg>
                        </span>
                        <span class="name-text">${esc(d.g)}</span>
                    </div>
                    <div class="pf-amounts">
                        <span class="fact">${fmt(d.fact)}</span> / <span class="plan">${fmt(d.plan)}</span> ₽
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${cls}" style="width:${widthPct}%"></div>
                </div>
            </div>`;
        }).join('');
    }

    renderPfList('inc-pflist', inc, false);
    renderPfList('exp-pflist', exp, true);

    // Totals
    const incTotalsEl = document.getElementById('inc-totals');
    if (incTotalsEl) {
        const fact = inc.reduce((s, d) => s + d.fact, 0);
        const plan = inc.reduce((s, d) => s + d.plan, 0);
        incTotalsEl.textContent = `${fmt(fact)} / ${fmt(plan)} ₽`;
    }
    const expTotalsEl = document.getElementById('exp-totals');
    if (expTotalsEl) {
        const fact = exp.reduce((s, d) => s + d.fact, 0);
        const plan = exp.reduce((s, d) => s + d.plan, 0);
        expTotalsEl.textContent = `${fmt(fact)} / ${fmt(plan)} ₽`;
    }

    // ============== Squarified Treemap ==============
    function squarify(items, x, y, w, h) {
        const result = [];
        if (!items.length || w <= 0 || h <= 0) return result;

        function worstRatio(row, sum, total, x, y, w, h) {
            const area = w * h;
            const rowArea = (sum / total) * area;
            const shortSide = Math.min(w, h);
            const longSide = rowArea / shortSide;
            let worst = 1;
            for (const it of row) {
                const itArea = (it.value / total) * area;
                const itLong = itArea / longSide;
                const r = Math.max(longSide / Math.max(itLong, 0.001), itLong / Math.max(longSide, 0.001));
                if (r > worst) worst = r;
            }
            return worst;
        }

        function placeRow(row, sum, total, x, y, w, h) {
            const area = w * h;
            if (w >= h) {
                const rowW = (sum / total) * w;
                let cy = y;
                for (const it of row) {
                    const itH = (it.value / sum) * h;
                    result.push({ ...it, x, y: cy, w: rowW, h: itH });
                    cy += itH;
                }
                return { x: x + rowW, y, w: w - rowW, h };
            } else {
                const rowH = (sum / total) * h;
                let cx = x;
                for (const it of row) {
                    const itW = (it.value / sum) * w;
                    result.push({ ...it, x: cx, y, w: itW, h: rowH });
                    cx += itW;
                }
                return { x, y: y + rowH, w, h: h - rowH };
            }
        }

        function recurse(items, x, y, w, h) {
            if (!items.length) return;
            const total = items.reduce((s, it) => s + it.value, 0);
            if (total === 0) return;

            let row = [];
            let rowSum = 0;
            let bestRatio = Infinity;

            for (let i = 0; i < items.length; i++) {
                const it = items[i];
                const newRow = [...row, it];
                const newSum = rowSum + it.value;
                const ratio = worstRatio(newRow, newSum, total, x, y, w, h);

                if (row.length === 0 || ratio <= bestRatio) {
                    row = newRow;
                    rowSum = newSum;
                    bestRatio = ratio;
                } else {
                    const remainArea = placeRow(row, rowSum, total, x, y, w, h);
                    recurse(items.slice(i), remainArea.x, remainArea.y, remainArea.w, remainArea.h);
                    return;
                }
            }
            placeRow(row, rowSum, total, x, y, w, h);
        }

        recurse(items, x, y, w, h);
        return result;
    }

    function pickSizeClass(w, h, value, total) {
        const area = w * h;
        const pct = total > 0 ? value / total : 0;
        if (area >= 22000 && pct >= 0.30) return 'size-l';
        if (area >= 9000) return 'size-m';
        if (area >= 3500) return 'size-s';
        return 'size-xs';
    }

    function renderTreemap() {
        const container = document.getElementById('treemap');
        if (!container) return;

        const data = exp
            .filter(d => d.fact > 0)
            .map((d, i) => ({
                name: d.g,
                value: d.fact,
                color: getCategoryStyle(d.g, i).hex,
            }))
            .sort((a, b) => b.value - a.value);

        const totalEl = document.getElementById('treemap-total');
        const total = data.reduce((s, d) => s + d.value, 0);
        if (totalEl) totalEl.textContent = `${fmt(total)} ₽`;

        if (!data.length) {
            container.innerHTML = '<div class="treemap-empty">Нет расходов в этом периоде</div>';
            return;
        }

        const w = container.clientWidth;
        const h = container.clientHeight;
        if (w === 0 || h === 0) {
            // не успел отрендериться, попробуем чуть позже
            requestAnimationFrame(renderTreemap);
            return;
        }

        const PAD = 4;
        const tiles = squarify(data, 0, 0, w, h);

        container.innerHTML = '';
        tiles.forEach((t, i) => {
            const pct = Math.round((t.value / total) * 100);
            const innerW = Math.max(0, t.w - PAD);
            const innerH = Math.max(0, t.h - PAD);
            // Отступы плитки не должны превышать её размер: иначе border-box растягивает её
            // за пределы отведённого места (мелкие статьи выходили за границы контейнера).
            const sizeClass = (innerW < 64 || innerH < 40)
                ? 'size-xxs'
                : pickSizeClass(innerW, innerH, t.value, total);

            const tile = document.createElement('div');
            tile.className = `tile ${sizeClass}`;
            tile.style.cssText = `left:${t.x}px;top:${t.y}px;width:${innerW}px;height:${innerH}px;background:linear-gradient(135deg, ${t.color}, ${t.color}dd);`;
            tile.title = `${t.name} · ${fmt(t.value)} ₽ (${pct}%)`;

            // Узкой плитке полная сумма не помещается — показываем сокращённую.
            const amountText = innerW < 96 ? fmtCompact(t.value) : `${fmt(t.value)} ₽`;

            if (sizeClass === 'size-xxs' && innerH < 14) {
                // слишком мала для текста: остаётся плитка с подсказкой (title)
            } else if (sizeClass === 'size-xxs' || (sizeClass === 'size-xs' && innerH < 50)) {
                // если плитка совсем маленькая — показываем только сумму
                tile.innerHTML = `<div class="tile-bottom">${amountText}</div>`;
            } else {
                tile.innerHTML = `
                    <div class="tile-top">
                        <span class="tile-name">${esc(t.name)}</span>
                        <span class="tile-pct">${pct}%</span>
                    </div>
                    <div class="tile-bottom">${amountText}</div>
                `;
            }
            container.appendChild(tile);
            // Крупную сумму ужимаем по ширине плитки, чтобы многоточие её не обрезало;
            // если и минимальный размер не помогает — сокращённая запись («30 тыс»).
            const bottom = tile.querySelector('.tile-bottom');
            if (bottom) {
                let size = parseFloat(getComputedStyle(bottom).fontSize);
                while (bottom.scrollWidth > bottom.clientWidth && size > 10) {
                    size -= 1;
                    bottom.style.fontSize = size + 'px';
                }
                if (bottom.scrollWidth > bottom.clientWidth) bottom.textContent = fmtCompact(t.value);
            }
            // плавное появление
            setTimeout(() => tile.classList.add('is-visible'), 30 + i * 40);
        });
    }

    renderTreemap();
    // переотрисовка при ресайзе (с дебаунсом)
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(renderTreemap, 150);
    });

    // ============== Charts (план vs факт) ==============
    // Chart.js грузится с CDN: если библиотеки нет, остальной дашборд (списки, treemap) всё равно работает.
    const charts = [];

    function showChartMessage(canvasId, text) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !canvas.parentElement) return;
        const note = document.createElement('div');
        note.className = 'pf-empty';
        note.textContent = text;
        canvas.parentElement.replaceChildren(note);
    }

    // Настройки собираются заново на каждый график: JSON-клон терял функции
    // (подписи оси «к» и тултипы с «₽»).
    function makeBaseOpts(colors) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.surface,
                    titleColor: colors.text,
                    bodyColor: colors.tick,
                    borderColor: colors.border,
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                    displayColors: false,
                    titleFont: { size: 12, weight: '600' },
                    bodyFont: { size: 13 },
                    callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.parsed.y ?? ctx.parsed)} ₽` }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11 }, color: colors.tick, maxRotation: 30 }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: colors.grid, drawBorder: false },
                    ticks: {
                        font: { size: 11 },
                        color: colors.tick,
                        callback: v => v >= 1000 ? Math.round(v / 1000) + 'к' : v
                    }
                }
            },
            animation: { duration: 800, easing: 'easeOutQuart' }
        };
    }

    function bars(label, data, color) {
        return { label, data, backgroundColor: color, borderRadius: 6, borderSkipped: false, barPercentage: 0.7, categoryPercentage: 0.6 };
    }

    function renderCharts() {
        charts.splice(0).forEach(chart => chart.destroy());
        const colors = palette();
        Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
        Chart.defaults.color = colors.tick;
        try {
            const incCanvas = document.getElementById('incChart');
            if (incCanvas && inc.length) {
                charts.push(new Chart(incCanvas, {
                    type: 'bar',
                    data: {
                        labels: inc.map(d => d.g),
                        datasets: [bars('План', inc.map(d => d.plan), '#B5D4F4'), bars('Факт', inc.map(d => d.fact), '#3D6BE6')]
                    },
                    options: makeBaseOpts(colors)
                }));
            }
            const expCanvas = document.getElementById('expChart');
            if (expCanvas && exp.length) {
                const expOpts = makeBaseOpts(colors);
                expOpts.scales.x.ticks.maxRotation = 35;
                expOpts.scales.x.ticks.font = { size: 10 };
                charts.push(new Chart(expCanvas, {
                    type: 'bar',
                    data: {
                        labels: exp.map(d => d.g),
                        datasets: [bars('План', exp.map(d => d.plan), '#F5C4B3'), bars('Факт', exp.map(d => d.fact), '#E63E3E')]
                    },
                    options: expOpts
                }));
            }
        } catch (e) {
            console.error('Chart.js error:', e);
        }
    }

    if (typeof Chart === 'undefined') {
        showChartMessage('incChart', 'Графики недоступны: не удалось загрузить библиотеку');
        showChartMessage('expChart', 'Графики недоступны: не удалось загрузить библиотеку');
    } else {
        if (!inc.length) showChartMessage('incChart', 'Нет данных за этот период');
        if (!exp.length) showChartMessage('expChart', 'Нет данных за этот период');
        renderCharts();
        // Смена темы: цвета осей, сетки и тултипов зависят от неё.
        document.addEventListener('ff:theme', renderCharts);
    }
})();
