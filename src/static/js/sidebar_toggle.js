document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registrationForm = document.getElementById('registrationForm');
    const profileMenu = document.getElementById('profileMenu');
    const profileMenuBtn = document.getElementById('profileMenuBtn');

    function getCSRFToken() {
        const cookieValue = document.cookie.match(/csrftoken=([^;]+)/);
        return cookieValue ? cookieValue[1] : '';
    }

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
});
