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

    // Маппинг категорий на иконки
    const catRules = [
        { keys: ['зарплат', 'оклад', 'аванс'], icon: '#i-briefcase' },
        { keys: ['подработ', 'фриланс'], icon: '#i-zap' },
        { keys: ['инвест', 'дивиденд', 'процент'], icon: '#i-trend-up' },
        { keys: ['продукт', 'еда', 'магаз'], icon: '#i-shopping-cart' },
        { keys: ['аренд', 'квартир', 'жил'], icon: '#i-home-house' },
        { keys: ['транспорт', 'такси', 'бенз', 'авто', 'метро'], icon: '#i-car' },
        { keys: ['развлеч', 'кино', 'театр'], icon: '#i-film' },
        { keys: ['коммун', 'свет', 'газ', 'вода'], icon: '#i-zap' },
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

    function renderPills(type) {
        const groups = type === 'income' ? incomeGroups : expenseGroups;
        groupInput.value = '';
        groupError.style.display = 'none';
        pillsContainer.innerHTML = '';

        if (!groups.length) {
            const empty = document.createElement('div');
            empty.style.cssText = 'font-size:13px;color:var(--text-muted);padding:8px 0';
            empty.textContent = 'Нет статей для этого типа. Создайте статью на странице «Статьи».';
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

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            toggleBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const type = btn.dataset.type;
            typeInput.value = type;
            renderPills(type);

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
        }
    });

    renderPills('expense');
})();
