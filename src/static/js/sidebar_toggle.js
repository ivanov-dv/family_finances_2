// ============== Подтверждения и защита от двойной отправки ==============
// Делегирование на document: не зависит от инициализации страницы. Текст подтверждения лежит
// в data-confirm (HTML-атрибут), а не в inline-onsubmit — иначе данные пользователя
// (названия статей и пространств) становятся кодом.
document.addEventListener('submit', event => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    const message = form.dataset.confirm;
    if (message && !window.confirm(message)) event.preventDefault();
});

// Формы с data-once отправляются один раз: двойной клик не создаёт дубль операции.
document.addEventListener('submit', event => {
    const form = event.target;
    if (event.defaultPrevented || !(form instanceof HTMLFormElement) || !('once' in form.dataset)) return;
    if (form.dataset.submitted) {
        event.preventDefault();
        return;
    }
    form.dataset.submitted = '1';
    // Если переход не состоялся (обрыв сети), форму можно отправить повторно.
    setTimeout(() => { delete form.dataset.submitted; }, 4000);
});
// Возврат кнопкой «Назад» (bfcache) не должен оставлять форму заблокированной.
window.addEventListener('pageshow', event => {
    if (event.persisted) {
        document.querySelectorAll('form[data-submitted]').forEach(form => { delete form.dataset.submitted; });
    }
});

(function () {
    const root = document.documentElement;
    const loginForm = document.getElementById('loginForm');
    const registrationForm = document.getElementById('registrationForm');
    const profileMenu = document.getElementById('profileMenu');
    const profileMenuBtn = document.getElementById('profileMenuBtn');
    const sidebar = document.getElementById('sidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');
    const menuBtn = document.getElementById('menuBtn');

    // Хранилище может быть недоступно (приватный режим, запрет cookies): без него всё должно работать.
    const storage = {
        get(key) {
            try { return localStorage.getItem(key); } catch (e) { return null; }
        },
        set(key, value) {
            try { localStorage.setItem(key, value); } catch (e) { /* недоступно — не страшно */ }
        },
    };

    // ============== Универсальное открытие/закрытие .app-modal-backdrop ==============
    const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), '
        + 'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    function openAppModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        document.querySelectorAll('.app-modal-backdrop:not([hidden])').forEach(el => {
            if (el !== modal) closeAppModal(el);
        });
        closeSidebar();
        resetAuthModal(modal);
        modal.removeAttribute('hidden');
        modal.hidden = false;
        document.body.style.overflow = 'hidden';
        const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
        const target = firstInput || modal.querySelector('[data-close-app-modal]');
        if (target) setTimeout(() => target.focus(), 100);
    }
    function closeAppModal(modal) {
        if (!modal) return;
        modal.setAttribute('hidden', '');
        modal.hidden = true;
        document.body.style.overflow = '';
    }

    // Фокус возвращается на элемент, открывший модалку; внутри открытой модалки Tab не уходит
    // на страницу под ней. Через наблюдатель — чтобы работало и для модалки статей (add_summary.js).
    const returnFocus = new WeakMap();
    const modalObserver = new MutationObserver(records => {
        records.forEach(({ target: modal }) => {
            if (!modal.hidden && !returnFocus.has(modal)) {
                returnFocus.set(modal, document.activeElement);
            } else if (modal.hidden && returnFocus.has(modal)) {
                const previous = returnFocus.get(modal);
                returnFocus.delete(modal);
                if (previous && previous.isConnected && typeof previous.focus === 'function') previous.focus();
            }
        });
    });
    document.querySelectorAll('.app-modal-backdrop').forEach(modal => {
        modalObserver.observe(modal, { attributes: true, attributeFilter: ['hidden'] });
    });

    document.addEventListener('keydown', e => {
        if (e.key !== 'Tab') return;
        const modal = document.querySelector('.app-modal-backdrop:not([hidden])');
        if (!modal) return;
        const items = [...modal.querySelectorAll(FOCUSABLE)].filter(el => el.offsetParent !== null);
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (!modal.contains(document.activeElement)) {
            e.preventDefault();
            first.focus();
        } else if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    });

    // Клик по фону закрывает модалку, только если и нажатие началось на фоне
    // (выделение текста в поле с отпусканием над затемнением не должно закрывать).
    let pressedBackdrop = null;
    document.addEventListener('mousedown', e => {
        pressedBackdrop = e.target.classList && e.target.classList.contains('app-modal-backdrop') ? e.target : null;
    });

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
        if (e.target.classList && e.target.classList.contains('app-modal-backdrop') && pressedBackdrop === e.target) {
            closeAppModal(e.target);
        }
    });
    document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        const openModals = document.querySelectorAll('.app-modal-backdrop:not([hidden])');
        openModals.forEach(closeAppModal);
    });

    // ============== Вход и регистрация (AJAX) ==============
    const NETWORK_ERROR = 'Не удалось выполнить запрос. Проверьте соединение и попробуйте ещё раз.';

    function csrfToken(form) {
        const field = form.querySelector('[name="csrfmiddlewaretoken"]');
        if (field && field.value) return field.value;
        const cookie = document.cookie.match(/csrftoken=([^;]+)/);
        return cookie ? cookie[1] : '';
    }

    // Адрес берётся из разметки (абсолютный): относительный «users/…» ломался на любой странице не из корня.
    async function postForm(form, fields) {
        const response = await fetch(form.dataset.url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': csrfToken(form),
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams(fields)
        });
        return response.json();
    }

    function setBusy(form, busy) {
        form.dataset.busy = busy ? '1' : '';
        form.setAttribute('aria-busy', busy ? 'true' : 'false');
        form.querySelectorAll('[type="submit"]').forEach(button => { button.disabled = busy; });
    }

    // Сервер отдаёт текст или список текстов (ошибки валидации формы).
    const asText = message => (Array.isArray(message) ? message.join('\n') : String(message || ''));

    const loginError = document.getElementById('loginError');
    const registrationError = document.getElementById('registrationError');
    const registrationSuccess = document.getElementById('registrationSuccess');

    // Состояние модалок входа/регистрации не должно «залипать» между открытиями.
    function resetAuthModal(modal) {
        if (modal.id === 'loginModal' && loginForm) {
            if (loginError) loginError.textContent = '';
            setBusy(loginForm, false);
        }
        if (modal.id === 'registrationModal' && registrationForm) {
            registrationForm.style.display = '';
            if (registrationError) { registrationError.textContent = ''; registrationError.style.display = 'none'; }
            if (registrationSuccess) { registrationSuccess.textContent = ''; registrationSuccess.style.display = 'none'; }
            modal.querySelectorAll('.app-modal-title, .app-modal-subtitle').forEach(el => { el.style.display = ''; });
            setBusy(registrationForm, false);
        }
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (loginForm.dataset.busy) return;
            if (loginError) loginError.textContent = '';
            setBusy(loginForm, true);
            try {
                const data = await postForm(loginForm, {
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value,
                    // Страница входа открывается с ?next=… — после входа возвращаем пользователя туда.
                    next: new URLSearchParams(window.location.search).get('next') || ''
                });
                if (data.status === 'success') {
                    window.location.assign(data.next || '/');
                    return;
                }
                if (loginError) loginError.textContent = asText(data.message);
            } catch (e) {
                if (loginError) loginError.textContent = NETWORK_ERROR;
            }
            setBusy(loginForm, false);
        });
    }

    if (registrationForm) {
        registrationForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            if (registrationForm.dataset.busy) return;
            registrationError.style.display = 'none';
            setBusy(registrationForm, true);
            try {
                const data = await postForm(registrationForm, {
                    username: document.getElementById('registration_username').value,
                    password: document.getElementById('registration_password').value
                });
                if (data.status === 'success') {
                    registrationSuccess.textContent = 'Заявка отправлена. Аккаунт будет доступен после подтверждения администратором.';
                    registrationSuccess.style.display = 'block';
                    registrationForm.style.display = 'none';
                    const modal = registrationForm.closest('.app-modal');
                    if (modal) {
                        const title = modal.querySelector('.app-modal-title');
                        const subtitle = modal.querySelector('.app-modal-subtitle');
                        if (title) title.style.display = 'none';
                        if (subtitle) subtitle.style.display = 'none';
                    }
                    return;
                }
                registrationError.textContent = asText(data.message);
                registrationError.style.display = 'block';
            } catch (e) {
                registrationError.textContent = NETWORK_ERROR;
                registrationError.style.display = 'block';
            }
            setBusy(registrationForm, false);
        });
    }

    // ============== Меню профиля ==============
    if (profileMenu && profileMenuBtn) {
        const setMenuOpen = open => {
            profileMenu.classList.toggle('open', open);
            profileMenuBtn.setAttribute('aria-expanded', String(open));
        };
        profileMenuBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            setMenuOpen(!profileMenu.classList.contains('open'));
        });
        document.addEventListener('click', (event) => {
            if (!profileMenu.contains(event.target)) setMenuOpen(false);
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && profileMenu.classList.contains('open')) {
                setMenuOpen(false);
                profileMenuBtn.focus();
            }
        });
        // Фокус ушёл из меню (Tab) — закрываем, чтобы оно не висело поверх страницы.
        profileMenu.addEventListener('focusout', (event) => {
            if (!profileMenu.contains(event.relatedTarget)) setMenuOpen(false);
        });
    }

    // ============== Тема ==============
    // Начальную тему (без мигания) выставляет inline-скрипт в <head>; здесь — только переключатель.
    // В localStorage пишем лишь явный выбор пользователя: системная тема при первом визите
    // не должна «замораживаться».
    function syncThemeButtons() {
        document.querySelectorAll('[data-theme-set]').forEach(b => {
            b.classList.toggle('is-active', b.dataset.themeSet === root.dataset.theme);
        });
    }
    function applyTheme(theme) {
        root.dataset.theme = theme;
        root.setAttribute('data-bs-theme', theme);
        storage.set('ff-theme', theme);
        syncThemeButtons();
        document.dispatchEvent(new CustomEvent('ff:theme', { detail: { theme } }));
    }
    syncThemeButtons();

    document.addEventListener('click', e => {
        const themeBtn = e.target.closest('[data-theme-set]');
        if (themeBtn) {
            e.preventDefault();
            e.stopPropagation();
            applyTheme(themeBtn.dataset.themeSet);
        }
    });

    // ============== Сайдбар (мобильный) ==============
    function openSidebar() {
        if (!sidebar) return;
        sidebar.classList.add('is-open');
        if (sidebarBackdrop) sidebarBackdrop.classList.add('is-visible');
        document.body.classList.add('sidebar-open');
        if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
    }
    function closeSidebar() {
        if (!sidebar) return;
        sidebar.classList.remove('is-open');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('is-visible');
        document.body.classList.remove('sidebar-open');
        if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
    }
    if (sidebar && menuBtn) {
        menuBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            if (sidebar.classList.contains('is-open')) closeSidebar();
            else openSidebar();
        });
        if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);
        sidebar.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', closeSidebar);
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && sidebar.classList.contains('is-open')) {
                closeSidebar();
                menuBtn.focus();
            }
        });
        // Окно расширили до десктопа — мобильное состояние (затемнение, блокировка прокрутки) снимаем.
        const desktop = matchMedia('(min-width: 961px)');
        const onBreakpoint = event => { if (event.matches) closeSidebar(); };
        if (desktop.addEventListener) desktop.addEventListener('change', onBreakpoint);
        else desktop.addListener(onBreakpoint);
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

        // По умолчанию — месяц, следующий за ПОСЛЕДНИМ существующим периодом, а не за просматриваемым
        // (при просмотре прошлого месяца иначе предлагался бы уже существующий период).
        const lastMonth = parseInt(periodModal.dataset.lastMonth || '0', 10);
        const lastYear = parseInt(periodModal.dataset.lastYear || '0', 10);
        const hasLast = lastMonth >= 1 && lastMonth <= 12 && lastYear > 0;

        function setDefaultNextMonth() {
            if (!monthSelect || !yearSelect) return;
            const cm = hasLast ? lastMonth : (currentMonth || (new Date().getMonth() + 1));
            const cy = hasLast ? lastYear : (currentYear || new Date().getFullYear());
            const nextMonth = (cm % 12) + 1;
            const nextYear = cm === 12 ? cy + 1 : cy;
            monthSelect.value = String(nextMonth);
            yearSelect.value = String(nextYear);
        }
        setDefaultNextMonth();

        // Открытие/закрытие, Esc, клик по фону, фокус — общие, как у остальных модалок.
        document.addEventListener('click', e => {
            if (e.target.closest('[data-open-period-modal]')) {
                e.preventDefault();
                openAppModal('newPeriodModal');
                setDefaultNextMonth();
            }
        });

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
    }
})();
