(function () {
    const incomeGroups = JSON.parse(document.getElementById('income-groups-data').textContent);
    const expenseGroups = JSON.parse(document.getElementById('expense-groups-data').textContent);

    const typeInput = document.getElementById('type_transaction');
    const groupInput = document.getElementById('group_name');
    const pillsContainer = document.getElementById('group-pills');
    const groupError = document.getElementById('group-error');
    const toggleBtns = document.querySelectorAll('.type-toggle-btn');
    const submitBtn = document.getElementById('submit-btn');
    const form = document.getElementById('add-form');

    const amountDisplay = document.getElementById('amountDisplay');
    const amountIntEl = document.getElementById('amountIntegerPart');
    const amountValueInput = document.getElementById('value_transaction');
    const numpad = document.getElementById('numpad');

    // ============== Category icon mapping ==============
    const catRules = [
        { keys: ['зарплат', 'оклад', 'аванс'], icon: '#i-briefcase' },
        { keys: ['подработ', 'фриланс'], icon: '#i-zap' },
        { keys: ['инвест', 'дивиденд', 'процент'], icon: '#i-trend-up' },
        { keys: ['продукт', 'еда', 'магаз'], icon: '#i-shopping-cart' },
        { keys: ['аренд', 'квартир', 'жил'], icon: '#i-home-house' },
        { keys: ['транспорт', 'такси', 'бенз', 'авто', 'метро'], icon: '#i-car' },
        { keys: ['развлеч', 'кино', 'театр'], icon: '#i-film' },
        { keys: ['коммун', 'свет', 'газ', 'вода', 'плат'], icon: '#i-zap' },
        { keys: ['здоров', 'медиц', 'лекарств', 'аптек'], icon: '#i-heart' },
        { keys: ['одежд', 'обув'], icon: '#i-shirt' },
        { keys: ['кафе', 'ресторан'], icon: '#i-utensils' },
        { keys: ['кофе'], icon: '#i-coffee' },
        { keys: ['образован', 'учеб', 'курс', 'книг'], icon: '#i-book' },
    ];
    function getIcon(name) {
        const lower = (name || '').toLowerCase();
        for (const rule of catRules) {
            if (rule.keys.some(k => lower.includes(k))) return rule.icon;
        }
        return '#i-package';
    }

    // ============== NUMPAD ==============
    let intPart = '0';
    let fracPart = '';
    let inFraction = false;

    function updateAmountDisplay() {
        const intFmt = parseInt(intPart || '0', 10).toLocaleString('ru-RU');
        const fracStr = inFraction
            ? ',' + (fracPart.padEnd(2, '0').slice(0, 2))
            : ',00';
        amountIntEl.textContent = intFmt;
        // обновим dec-часть (она следует за integer part в HTML)
        const decEl = amountDisplay.querySelector('.dec');
        if (decEl) decEl.textContent = fracStr;

        // обновим hidden-input значением для отправки
        const fracForVal = fracPart ? '.' + fracPart : '';
        amountValueInput.value = (parseFloat(intPart || '0') + (fracPart ? parseFloat('0.' + fracPart) : 0)).toFixed(2);
    }

    if (numpad) {
        numpad.addEventListener('click', e => {
            const btn = e.target.closest('button');
            if (!btn) return;
            const action = btn.dataset.np;
            if (action === 'back') {
                if (inFraction && fracPart.length) {
                    fracPart = fracPart.slice(0, -1);
                    if (!fracPart.length) inFraction = false;
                } else if (intPart.length > 1) {
                    intPart = intPart.slice(0, -1);
                } else {
                    intPart = '0';
                    fracPart = '';
                    inFraction = false;
                }
            } else if (action === 'comma') {
                inFraction = true;
            } else if (action === 'digit') {
                const d = btn.dataset.d;
                if (inFraction) {
                    if (fracPart.length < 2) fracPart += d;
                } else {
                    // запретим бесконечно длинные числа (макс 9 цифр)
                    if (intPart.length >= 9) return;
                    if (intPart === '0') intPart = d;
                    else intPart += d;
                }
            }
            updateAmountDisplay();
        });
    }

    // Поддержка ввода с физической клавиатуры
    document.addEventListener('keydown', e => {
        if (!amountDisplay) return;
        // не перехватываем когда фокус в текстовом input/textarea
        const tag = (document.activeElement && document.activeElement.tagName) || '';
        if (tag === 'INPUT' && document.activeElement.type !== 'hidden') return;
        if (tag === 'TEXTAREA') return;

        if (/^[0-9]$/.test(e.key)) {
            const btn = numpad.querySelector(`button[data-d="${e.key}"]`);
            if (btn) btn.click();
        } else if (e.key === ',' || e.key === '.') {
            const btn = numpad.querySelector('button[data-np="comma"]');
            if (btn) btn.click();
        } else if (e.key === 'Backspace') {
            const btn = numpad.querySelector('button[data-np="back"]');
            if (btn) btn.click();
            e.preventDefault();
        }
    });

    updateAmountDisplay();

    // ============== Group pills ==============
    function renderPills(type) {
        const groups = type === 'income' ? incomeGroups : expenseGroups;
        groupInput.value = '';
        groupError.style.display = 'none';
        pillsContainer.innerHTML = '';

        if (!groups.length) {
            const empty = document.createElement('div');
            empty.style.cssText = 'font-size:13px;color:var(--text-muted);padding:8px 0';
            empty.textContent = 'Нет статей для этого типа. Создайте статью на странице «Статьи бюджета».';
            pillsContainer.appendChild(empty);
            return;
        }

        groups.forEach(g => {
            const pill = document.createElement('button');
            pill.type = 'button';
            pill.className = 'group-pill';
            pill.dataset.type = type;
            pill.innerHTML = `<svg class="icon"><use href="${getIcon(g)}"/></svg><span>${g}</span>`;
            pill.addEventListener('click', () => {
                pillsContainer.querySelectorAll('.group-pill').forEach(p => {
                    p.classList.remove('selected');
                    p.removeAttribute('data-type');
                });
                pill.classList.add('selected');
                pill.dataset.type = type;
                groupInput.value = g;
                groupError.style.display = 'none';
            });
            pillsContainer.appendChild(pill);
        });
    }

    // ============== Type toggle ==============
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            toggleBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const type = btn.dataset.type;
            typeInput.value = type;
            renderPills(type);

            // обновить цвет суммы
            amountDisplay.classList.toggle('expense', type === 'expense');
            amountDisplay.classList.toggle('income', type === 'income');

            // обновить submit-кнопку
            const submitText = submitBtn.querySelector('span');
            if (submitText) {
                submitText.textContent = type === 'income' ? 'Добавить доход' : 'Добавить расход';
            }
            submitBtn.className = 'submit-btn ' + (type === 'income' ? 'submit-income' : 'submit-expense');
        });
    });

    form.addEventListener('submit', e => {
        if (!groupInput.value) {
            e.preventDefault();
            groupError.style.display = 'block';
            pillsContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
        const numeric = parseFloat(amountValueInput.value);
        if (!numeric || numeric <= 0) {
            e.preventDefault();
            amountDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });
            amountDisplay.animate(
                [{ transform: 'translateX(-6px)' }, { transform: 'translateX(6px)' }, { transform: 'translateX(0)' }],
                { duration: 240, iterations: 2 }
            );
        }
    });

    renderPills('expense');
})();
