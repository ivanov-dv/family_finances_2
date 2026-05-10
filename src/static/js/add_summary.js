(function () {
    const fmt = v => Number(v).toLocaleString('ru-RU');

    // ============== Type toggle (внутри модалки) ==============
    const typeInput = document.getElementById('type_transaction');
    const toggleBtns = document.querySelectorAll('.type-toggle-btn');
    const submitBtn = document.getElementById('submit-btn');

    function setType(type) {
        toggleBtns.forEach(b => b.classList.toggle('active', b.dataset.type === type));
        if (typeInput) typeInput.value = type;
        const submitText = submitBtn ? submitBtn.querySelector('span') : null;
        if (submitText) {
            submitText.textContent = type === 'income' ? 'Создать статью дохода' : 'Создать статью расхода';
        }
        if (submitBtn) {
            submitBtn.className = 'submit-btn ' + (type === 'income' ? 'submit-income' : 'submit-expense');
        }
    }
    toggleBtns.forEach(btn => btn.addEventListener('click', () => setType(btn.dataset.type)));

    // ============== Category icons + colors ==============
    const catRules = [
        { keys: ['зарплат', 'оклад', 'аванс'], icon: '#i-briefcase', color: 'green' },
        { keys: ['подработ', 'фриланс'], icon: '#i-zap', color: 'blue' },
        { keys: ['инвест', 'дивиденд', 'процент'], icon: '#i-trend-up', color: 'purple' },
        { keys: ['продукт', 'еда', 'магаз'], icon: '#i-shopping-cart', color: 'green' },
        { keys: ['аренд', 'квартир', 'жил'], icon: '#i-home-house', color: 'orange' },
        { keys: ['транспорт', 'такси', 'бенз', 'авто', 'метро'], icon: '#i-car', color: 'cyan' },
        { keys: ['развлеч', 'кино', 'театр'], icon: '#i-film', color: 'pink' },
        { keys: ['коммун', 'свет', 'газ', 'вода', 'плат'], icon: '#i-zap', color: 'yellow' },
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

    // ============== Прогресс-бары на карточках ==============
    document.querySelectorAll('.progress-fill[data-fact]').forEach(fill => {
        const fact = parseFloat(fill.dataset.fact || '0');
        const plan = parseFloat(fill.dataset.plan || '0');
        if (plan <= 0) return;
        const ratio = (fact / plan) * 100;
        const isExpense = fill.dataset.expense === '1';

        let cls = 'is-green';
        if (isExpense) {
            if (ratio > 110) cls = 'is-red';
            else if (ratio > 95) cls = 'is-yellow';
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

    // ============== Подсчёт количества и сумм для шапок колонок ==============
    function pluralize(n, forms) {
        // forms: ['статья', 'статьи', 'статей']
        const n10 = n % 10, n100 = n % 100;
        if (n10 === 1 && n100 !== 11) return forms[0];
        if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return forms[1];
        return forms[2];
    }

    function summarizeColumn(listSelector, countEl, totalsEl) {
        const cards = document.querySelectorAll(`${listSelector} .cat-card[data-fact]`);
        let factSum = 0, planSum = 0;
        cards.forEach(c => {
            factSum += parseFloat(c.dataset.fact || '0');
            planSum += parseFloat(c.dataset.plan || '0');
        });
        const n = cards.length;
        if (countEl) {
            countEl.textContent = n
                ? `${n} ${pluralize(n, ['статья', 'статьи', 'статей'])}`
                : 'нет статей';
        }
        if (totalsEl) {
            totalsEl.textContent = n ? `${fmt(factSum)} / ${fmt(planSum)} ₽` : '';
        }
    }
    summarizeColumn('#inc-cats', document.getElementById('inc-count'), document.getElementById('inc-totals'));
    summarizeColumn('#exp-cats', document.getElementById('exp-count'), document.getElementById('exp-totals'));

    // ============== Модалка ==============
    const modal = document.getElementById('newSummaryModal');
    const groupNameInput = document.getElementById('group_name');

    function openModal(typeOverride) {
        if (!modal) return;
        if (typeOverride) setType(typeOverride);
        modal.removeAttribute('hidden');
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
        setTimeout(() => groupNameInput && groupNameInput.focus(), 100);
    }
    function closeModal() {
        if (!modal) return;
        modal.setAttribute('hidden', '');
        modal.hidden = true;
        document.body.style.overflow = '';
    }

    // Делегированный обработчик на document — работает даже если клик
    // случился по дочернему svg/span внутри кнопки.
    document.addEventListener('click', e => {
        const opener = e.target.closest('[data-open-modal]');
        if (opener) {
            e.preventDefault();
            openModal(opener.dataset.addType || null);
            return;
        }
        if (e.target.closest('#modalCloseBtn')) {
            e.preventDefault();
            closeModal();
            return;
        }
        // клик по фону модалки (но не по самой карточке внутри)
        if (e.target === modal) {
            closeModal();
        }
    });

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && modal && !modal.hidden) closeModal();
    });
})();
