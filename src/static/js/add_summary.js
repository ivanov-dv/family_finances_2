(function () {
    const typeInput = document.getElementById('type_transaction');
    const toggleBtns = document.querySelectorAll('.type-toggle-btn');
    const submitBtn = document.getElementById('submit-btn');

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            toggleBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            typeInput.value = btn.dataset.type;
            if (btn.dataset.type === 'income') {
                submitBtn.textContent = 'Создать статью дохода';
                submitBtn.className = 'submit-btn submit-income';
            } else {
                submitBtn.textContent = 'Создать статью расхода';
                submitBtn.className = 'submit-btn submit-expense';
            }
        });
    });
})();
