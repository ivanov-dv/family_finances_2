(function () {
    const inc = JSON.parse(document.getElementById('inc-data').textContent);
    const exp = JSON.parse(document.getElementById('exp-data').textContent);

    const fmt = v => Number(v).toLocaleString('ru-RU');
    const isDark = matchMedia('(prefers-color-scheme:dark)').matches;
    const gridC = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.06)';
    const tickC = isDark ? '#9a9a94' : '#888';

    const baseOpts = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: ctx => ' ' + fmt(ctx.parsed.y ?? ctx.parsed) } }
        },
        scales: {
            x: { ticks: { font: { size: 11 }, color: tickC }, grid: { color: gridC } },
            y: {
                ticks: {
                    font: { size: 11 },
                    color: tickC,
                    callback: v => v >= 1000 ? Math.round(v / 1000) + 'к' : v
                },
                grid: { color: gridC }
            }
        }
    };

    const pieColors = ['#378ADD', '#1D9E75', '#D85A30', '#BA7517', '#534AB7', '#D4537E', '#639922', '#0F6E56', '#888780'];
    const totalExp = exp.reduce((s, d) => s + d.fact, 0);

    try {
        if (inc.length) {
            new Chart(document.getElementById('incChart'), {
                type: 'bar',
                data: {
                    labels: inc.map(d => d.g),
                    datasets: [
                        { label: 'план', data: inc.map(d => d.plan), backgroundColor: '#B5D4F4', borderRadius: 4 },
                        { label: 'факт', data: inc.map(d => d.fact), backgroundColor: '#378ADD', borderRadius: 4 }
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
                        { label: 'план', data: exp.map(d => d.plan), backgroundColor: '#F5C4B3', borderRadius: 4 },
                        { label: 'факт', data: exp.map(d => d.fact), backgroundColor: '#D85A30', borderRadius: 4 }
                    ]
                },
                options: expOpts
            });
        }

        if (exp.length && totalExp > 0) {
            new Chart(document.getElementById('pieChart'), {
                type: 'doughnut',
                data: {
                    labels: exp.map(d => d.g),
                    datasets: [{
                        data: exp.map(d => d.fact),
                        backgroundColor: pieColors,
                        borderWidth: 1,
                        borderColor: isDark ? '#1c1c1a' : '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: ctx => {
                                    const pct = totalExp > 0 ? Math.round(ctx.parsed / totalExp * 100) : 0;
                                    return ' ' + fmt(ctx.parsed) + ' (' + pct + '%)';
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (e) {
        console.error('Chart.js error:', e);
    }

    const leg = document.getElementById('pie-legend');
    if (leg) {
        exp.forEach((d, i) => {
            if (d.fact === 0) return;
            const pct = totalExp > 0 ? Math.round(d.fact / totalExp * 100) : 0;
            leg.innerHTML += `<div style="display:flex;align-items:center;gap:5px">
                <span style="width:10px;height:10px;border-radius:2px;background:${pieColors[i % pieColors.length]};flex-shrink:0"></span>
                <span style="color:var(--text-secondary)">${d.g}</span>
                <span style="font-weight:500">${pct}%</span>
            </div>`;
        });
    }

    const iBody = document.getElementById('inc-table');
    if (iBody) {
        if (!inc.length) {
            iBody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-secondary)">Нет данных</td></tr>';
        } else {
            inc.forEach(d => {
                const diff = d.fact - d.plan;
                const cls = diff >= 0 ? 'pos' : 'neg';
                const sign = diff >= 0 ? '+' : '';
                iBody.innerHTML += `<tr>
                    <td>${d.g}</td>
                    <td class="num" style="color:var(--text-secondary)">${fmt(d.plan)}</td>
                    <td class="num">${fmt(d.fact)}<br><span class="${cls}" style="font-size:11px">${sign}${fmt(diff)}</span></td>
                </tr>`;
            });
        }
    }

    const eBody = document.getElementById('exp-table');
    if (eBody) {
        if (!exp.length) {
            eBody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--text-secondary)">Нет данных</td></tr>';
        } else {
            exp.forEach(d => {
                const ratio = d.plan > 0 ? Math.round(d.fact / d.plan * 100) : 0;
                const over = d.fact > d.plan;
                eBody.innerHTML += `<tr>
                    <td>${d.g}</td>
                    <td class="num">${fmt(d.fact)}</td>
                    <td class="num" style="min-width:56px">
                        <span style="color:${over ? 'var(--red)' : 'var(--green)'}">${ratio}%</span>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width:${Math.min(ratio, 100)}%;background:${over ? 'var(--red)' : 'var(--green)'}"></div>
                        </div>
                    </td>
                </tr>`;
            });
        }
    }
})();
