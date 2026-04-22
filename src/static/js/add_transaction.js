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

    function renderPills(type) {
        const groups = type === 'income' ? incomeGroups : expenseGroups;
        groupInput.value = '';
        groupError.style.display = 'none';
        pillsContainer.innerHTML = '';

        if (!groups.length) {
            pillsContainer.innerHTML = '<span style="font-size:13px;color:var(--text-secondary)">Нет статей для этого типа</span>';
            return;
        }

        groups.forEach(g => {
            const pill = document.createElement('span');
            pill.textContent = g;
            Object.assign(pill.style, {
                display: 'inline-block',
                padding: '6px 14px',
                fontSize: '13px',
                borderRadius: '20px',
                border: '1px solid #ccc',
                background: '#f0f0ee',
                color: '#6b6b67',
                cursor: 'pointer',
                userSelect: 'none',
                transition: 'background 0.15s, color 0.15s'
            });
            pill.addEventListener('mouseenter', () => {
                if (pill.dataset.selected !== '1') {
                    pill.style.background = '#e8e6e1';
                    pill.style.color = '#1a1a18';
                }
            });
            pill.addEventListener('mouseleave', () => {
                if (pill.dataset.selected !== '1') {
                    pill.style.background = '#f0f0ee';
                    pill.style.color = '#6b6b67';
                }
            });
            pill.addEventListener('click', () => {
                pillsContainer.querySelectorAll('span').forEach(p => {
                    p.dataset.selected = '';
                    p.style.background = '#f0f0ee';
                    p.style.color = '#6b6b67';
                    p.style.border = '1px solid #ccc';
                });
                pill.dataset.selected = '1';
                pill.style.background = '#2e2e2b';
                pill.style.color = '#f0ede8';
                pill.style.border = '1px solid #2e2e2b';
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
            typeInput.value = btn.dataset.type;
            renderPills(btn.dataset.type);
            submitBtn.textContent = btn.dataset.type === 'income' ? 'Добавить доход' : 'Добавить расход';
            submitBtn.className = 'submit-btn ' + (btn.dataset.type === 'income' ? 'submit-income' : 'submit-expense');
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
