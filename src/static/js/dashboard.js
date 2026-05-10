(function () {
    const inc = JSON.parse(document.getElementById('inc-data').textContent);
    const exp = JSON.parse(document.getElementById('exp-data').textContent);

    const fmt = v => Number(v).toLocaleString('ru-RU');

    function readCSS(varName) {
        return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
    }

    const isDark = matchMedia('(prefers-color-scheme:dark)').matches;
    const tickC = readCSS('--text-muted') || (isDark ? '#8A93A8' : '#64748B');
    const gridC = readCSS('--border') || (isDark ? 'rgba(255,255,255,0.07)' : 'rgba(15,23,42,0.06)');
    const surfaceC = readCSS('--bg-elevated') || (isDark ? '#1F2742' : '#FFFFFF');
    const borderC = readCSS('--border-md') || gridC;
    const textPrimary = readCSS('--text-primary') || (isDark ? '#F5F7FA' : '#0F172A');

    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.color = tickC;

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
            const ratio = d.plan > 0 ? (d.fact / d.plan) * 100 : 0;
            const widthPct = Math.min(ratio, 100);
            const cls = progressClass(ratio, isExpense);
            return `<div class="pf-row">
                <div class="pf-row-top">
                    <div class="pf-row-name">
                        <span class="cat-icon-32 ${style.color}">
                            <svg class="icon icon-sm"><use href="${style.icon}"/></svg>
                        </span>
                        <span class="name-text">${d.g}</span>
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
            const sizeClass = pickSizeClass(innerW, innerH, t.value, total);

            const tile = document.createElement('div');
            tile.className = `tile ${sizeClass}`;
            tile.style.cssText = `left:${t.x}px;top:${t.y}px;width:${innerW}px;height:${innerH}px;background:linear-gradient(135deg, ${t.color}, ${t.color}dd);`;
            tile.title = `${t.name} · ${fmt(t.value)} ₽ (${pct}%)`;

            // если плитка совсем маленькая — показываем только сумму
            if (sizeClass === 'size-xs' && innerH < 50) {
                tile.innerHTML = `<div class="tile-bottom">${fmt(t.value)} ₽</div>`;
            } else {
                tile.innerHTML = `
                    <div class="tile-top">
                        <span class="tile-name">${t.name}</span>
                        <span class="tile-pct">${pct}%</span>
                    </div>
                    <div class="tile-bottom">${fmt(t.value)} ₽</div>
                `;
            }
            container.appendChild(tile);
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
    const tooltipBase = {
        backgroundColor: surfaceC,
        titleColor: textPrimary,
        bodyColor: tickC,
        borderColor: borderC,
        borderWidth: 1,
        padding: 12,
        cornerRadius: 10,
        displayColors: false,
        titleFont: { size: 12, weight: '600' },
        bodyFont: { size: 13 }
    };

    const baseOpts = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                ...tooltipBase,
                callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.parsed.y ?? ctx.parsed)} ₽` }
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { font: { size: 11 }, color: tickC, maxRotation: 30 }
            },
            y: {
                beginAtZero: true,
                grid: { color: gridC, drawBorder: false },
                ticks: {
                    font: { size: 11 },
                    color: tickC,
                    callback: v => v >= 1000 ? Math.round(v / 1000) + 'к' : v
                }
            }
        },
        animation: { duration: 800, easing: 'easeOutQuart' }
    };

    try {
        if (inc.length) {
            new Chart(document.getElementById('incChart'), {
                type: 'bar',
                data: {
                    labels: inc.map(d => d.g),
                    datasets: [
                        { label: 'План', data: inc.map(d => d.plan), backgroundColor: '#B5D4F4', borderRadius: 6, borderSkipped: false, barPercentage: 0.7, categoryPercentage: 0.6 },
                        { label: 'Факт', data: inc.map(d => d.fact), backgroundColor: '#3D6BE6', borderRadius: 6, borderSkipped: false, barPercentage: 0.7, categoryPercentage: 0.6 }
                    ]
                },
                options: JSON.parse(JSON.stringify(baseOpts))
            });
        }

        if (exp.length) {
            const expOpts = JSON.parse(JSON.stringify(baseOpts));
            expOpts.scales.x.ticks.maxRotation = 35;
            expOpts.scales.x.ticks.font = { size: 10 };

            new Chart(document.getElementById('expChart'), {
                type: 'bar',
                data: {
                    labels: exp.map(d => d.g),
                    datasets: [
                        { label: 'План', data: exp.map(d => d.plan), backgroundColor: '#F5C4B3', borderRadius: 6, borderSkipped: false, barPercentage: 0.7, categoryPercentage: 0.6 },
                        { label: 'Факт', data: exp.map(d => d.fact), backgroundColor: '#E63E3E', borderRadius: 6, borderSkipped: false, barPercentage: 0.7, categoryPercentage: 0.6 }
                    ]
                },
                options: expOpts
            });
        }
    } catch (e) {
        console.error('Chart.js error:', e);
    }
})();
