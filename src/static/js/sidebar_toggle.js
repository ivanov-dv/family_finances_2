document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registrationForm = document.getElementById('registrationForm');
    const profileMenu = document.getElementById('profileMenu');
    const profileMenuBtn = document.getElementById('profileMenuBtn');

    function getCSRFToken() {
        const cookieValue = document.cookie.match(/csrftoken=([^;]+)/);
        return cookieValue ? cookieValue[1] : '';
    }

    // ============== Универсальное открытие/закрытие .app-modal-backdrop ==============
    function openAppModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        modal.removeAttribute('hidden');
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
        const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
        if (firstInput) setTimeout(() => firstInput.focus(), 100);
    }
    function closeAppModal(modal) {
        if (!modal) return;
        modal.setAttribute('hidden', '');
        modal.hidden = true;
        document.body.style.overflow = '';
    }

    document.addEventListener('click', e => {
        const opener = e.target.closest('[data-open-app-modal]');
        if (opener) {
            e.preventDefault();
            openAppModal(opener.dataset.openAppModal);
            return;
        }
        const closer = e.target.closest('[data-close-app-modal]');
        if (closer) {
            e.preventDefault();
            closeAppModal(closer.closest('.app-modal-backdrop'));
            return;
        }
        // Клик по фону модалки
        if (e.target.classList && e.target.classList.contains('app-modal-backdrop')) {
            closeAppModal(e.target);
        }
    });
    document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        const openModals = document.querySelectorAll('.app-modal-backdrop:not([hidden])');
        openModals.forEach(closeAppModal);
    });

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const loginError = document.getElementById('loginError');

            const response = await fetch('users/ajax-login/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
            });

            const data = await response.json();

            if (data.status === 'success') {
                window.location.reload();
            } else {
                loginError.textContent = data.message;
            }
        });
    }

    if (registrationForm) {
        registrationForm.addEventListener('submit', async (event) => {
            event.preventDefault();

            const registration_username = document.getElementById('registration_username').value;
            const registration_password = document.getElementById('registration_password').value;
            const registrationError = document.getElementById('registrationError');
            const registrationSuccess = document.getElementById('registrationSuccess');

            const response = await fetch('users/registration/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: `username=${encodeURIComponent(registration_username)}&password=${encodeURIComponent(registration_password)}`
            });

            const data = await response.json();

            if (data.status === 'success') {
                registrationSuccess.textContent = 'Регистрация прошла успешно!';
                registrationSuccess.style.display = 'block';
                registrationForm.style.display = 'none';
            } else {
                registrationError.textContent = data.message;
                registrationError.style.display = 'block';
            }
        });
    }

    if (profileMenu && profileMenuBtn) {
        profileMenuBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            profileMenu.classList.toggle('open');
        });
        document.addEventListener('click', (event) => {
            if (!profileMenu.contains(event.target)) {
                profileMenu.classList.remove('open');
            }
        });
    }

    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const stored = localStorage.getItem('ff-theme');
        const systemDark = matchMedia('(prefers-color-scheme: dark)').matches;
        const initial = stored || (systemDark ? 'dark' : 'light');
        applyTheme(initial);

        themeToggle.querySelectorAll('[data-theme-set]').forEach(btn => {
            btn.addEventListener('click', () => {
                applyTheme(btn.dataset.themeSet);
            });
        });
    }
    function applyTheme(theme) {
        document.documentElement.dataset.theme = theme;
        localStorage.setItem('ff-theme', theme);
        document.querySelectorAll('[data-theme-set]').forEach(b => {
            b.classList.toggle('is-active', b.dataset.themeSet === theme);
        });
    }

    const sidebar = document.getElementById('sidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');
    const menuBtn = document.getElementById('menuBtn');
    if (sidebar && menuBtn) {
        const closeSidebar = () => {
            sidebar.classList.remove('is-open');
            if (sidebarBackdrop) sidebarBackdrop.classList.remove('is-visible');
        };
        menuBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            sidebar.classList.add('is-open');
            if (sidebarBackdrop) sidebarBackdrop.classList.add('is-visible');
        });
        if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
        sidebar.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', closeSidebar);
        });
    }

    // ============== Модалка «Экспорт в Excel» ==============
    const exportModal = document.getElementById('exportModal');
    if (exportModal) {
        const confirmLink = exportModal.querySelector('[data-export-confirm]');
        if (confirmLink) {
            confirmLink.addEventListener('click', () => {
                setTimeout(() => closeAppModal(exportModal), 150);
            });
        }
    }

    // ============== Модалка «Новый период» ==============
    const periodModal = document.getElementById('newPeriodModal');
    if (periodModal) {
        const monthSelect = document.getElementById('newPeriodMonth');
        const yearSelect = document.getElementById('newPeriodYear');

        const currentMonth = parseInt(periodModal.dataset.currentMonth || '0', 10);
        const currentYear = parseInt(periodModal.dataset.currentYear || '0', 10) || new Date().getFullYear();

        // Заполняем годы (от текущего − 1 до + 5)
        if (yearSelect) {
            const baseYear = currentYear || new Date().getFullYear();
            yearSelect.innerHTML = '';
            for (let y = baseYear - 1; y <= baseYear + 5; y++) {
                const opt = document.createElement('option');
                opt.value = y;
                opt.textContent = y;
                yearSelect.appendChild(opt);
            }
        }

        // По умолчанию выбираем «следующий месяц» от текущего
        function setDefaultNextMonth() {
            if (!monthSelect || !yearSelect) return;
            const cm = currentMonth || (new Date().getMonth() + 1);
            const cy = currentYear || new Date().getFullYear();
            const nextMonth = (cm % 12) + 1;
            const nextYear = cm === 12 ? cy + 1 : cy;
            monthSelect.value = String(nextMonth);
            yearSelect.value = String(nextYear);
        }
        setDefaultNextMonth();

        function openPeriodModal() {
            periodModal.removeAttribute('hidden');
            periodModal.hidden = false;
            document.body.style.overflow = 'hidden';
            setDefaultNextMonth();
        }
        function closePeriodModal() {
            periodModal.setAttribute('hidden', '');
            periodModal.hidden = true;
            document.body.style.overflow = '';
        }

        // Кнопка «Снять все / Выбрать все»
        const toggleBtn = document.getElementById('copyAllToggle');
        const checkboxes = periodModal.querySelectorAll('input[name="copy_summary_ids"]');
        function updateToggleState() {
            if (!toggleBtn || !checkboxes.length) return;
            const allChecked = [...checkboxes].every(cb => cb.checked);
            toggleBtn.dataset.state = allChecked ? 'all' : 'none';
            toggleBtn.textContent = allChecked ? 'Снять все' : 'Выбрать все';
        }
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const allChecked = [...checkboxes].every(cb => cb.checked);
                checkboxes.forEach(cb => { cb.checked = !allChecked; });
                updateToggleState();
            });
        }
        checkboxes.forEach(cb => cb.addEventListener('change', updateToggleState));
        updateToggleState();

        // Подсветка изменённых полей плана
        const planInputs = periodModal.querySelectorAll('.copy-row-input');
        planInputs.forEach(input => {
            const original = input.dataset.original || '';
            const updateChanged = () => {
                input.classList.toggle('is-changed', input.value !== original);
            };
            input.addEventListener('input', updateChanged);
            input.addEventListener('focus', () => input.select());
        });

        document.addEventListener('click', e => {
            if (e.target.closest('[data-open-period-modal]')) {
                e.preventDefault();
                openPeriodModal();
                return;
            }
            if (e.target.closest('[data-close-period-modal]')) {
                e.preventDefault();
                closePeriodModal();
                return;
            }
            if (e.target === periodModal) {
                closePeriodModal();
            }
        });
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && !periodModal.hidden) closePeriodModal();
        });
    }
});
