(function () {
    const typeInput = document.getElementById('type_transaction');
    const toggleBtns = document.querySelectorAll('.type-toggle-btn');
    const submitBtn = document.getElementById('submit-btn');

    if (toggleBtns.length && submitBtn && typeInput) {
        toggleBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                toggleBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const type = btn.dataset.type;
                typeInput.value = type;

                const submitText = submitBtn.querySelector('span');
                if (type === 'income') {
                    if (submitText) submitText.textContent = 'Создать статью дохода';
                    submitBtn.className = 'submit-btn submit-income';
                } else {
                    if (submitText) submitText.textContent = 'Создать статью расхода';
                    submitBtn.className = 'submit-btn submit-expense';
                }
            });
        });
    }

    // Иконки категорий и цвета
    const catRules = [
        { keys: ['зарплат', 'оклад', 'аванс'], icon: '#i-briefcase', color: 'green' },
        { keys: ['подработ', 'фриланс'], icon: '#i-zap', color: 'blue' },
        { keys: ['инвест', 'дивиденд', 'процент'], icon: '#i-trend-up', color: 'purple' },
        { keys: ['продукт', 'еда', 'магаз'], icon: '#i-shopping-cart', color: 'green' },
        { keys: ['аренд', 'квартир', 'жил'], icon: '#i-home-house', color: 'orange' },
        { keys: ['транспорт', 'такси', 'бенз', 'авто', 'метро'], icon: '#i-car', color: 'cyan' },
        { keys: ['развлеч', 'кино', 'театр'], icon: '#i-film', color: 'pink' },
        { keys: ['коммун', 'свет', 'газ', 'вода'], icon: '#i-zap', color: 'yellow' },
        { keys: ['здоров', 'медиц', 'лекарств', 'аптек'], icon: '#i-heart', color: 'red' },
        { keys: ['одежд', 'обув'], icon: '#i-shirt', color: 'purple' },
        { keys: ['кафе', 'ресторан'], icon: '#i-utensils', color: 'orange' },
        { keys: ['кофе'], icon: '#i-coffee', color: 'orange' },
        { keys: ['образован', 'учеб', 'курс', 'книг'], icon: '#i-book', color: 'blue' },
    ];

    function getCategoryStyle(name) {
        const lower = (name || '').toLowerCase();
        for (const rule of catRules) {
            if (rule.keys.some(k => lower.includes(k))) return rule;
        }
        return { icon: '#i-package', color: 'blue' };
    }

    document.querySelectorAll('[data-cat-icon]').forEach(el => {
        const group = el.dataset.group || '';
        const style = getCategoryStyle(group);
        el.classList.add(style.color);
        el.innerHTML = `<svg class="icon icon-sm"><use href="${style.icon}"/></svg>`;
    });

    // Прогресс-бары
    document.querySelectorAll('.progress-fill[data-fact]').forEach(fill => {
        const fact = parseFloat(fill.dataset.fact || '0');
        const plan = parseFloat(fill.dataset.plan || '0');
        if (plan <= 0) return;
        const ratio = (fact / plan) * 100;
        const isExpense = fill.dataset.expense === '1';

        let cls = 'is-green';
        if (isExpense) {
            if (ratio > 100) cls = 'is-red';
            else if (ratio > 90) cls = 'is-yellow';
            else cls = 'is-green';
        } else {
            if (ratio < 80) cls = 'is-yellow';
            else cls = 'is-green';
        }
        fill.classList.remove('is-green', 'is-red', 'is-yellow', 'is-purple');
        fill.classList.add(cls);
        requestAnimationFrame(() => {
            fill.style.width = Math.min(ratio, 100) + '%';
        });
    });
})();
