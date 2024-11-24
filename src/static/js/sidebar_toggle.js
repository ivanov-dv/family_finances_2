document.addEventListener('DOMContentLoaded', () => {
    const menuButton = document.getElementById('menuButton');
    const closeSidebar = document.getElementById('closeSidebar');
    const loginForm = document.getElementById('loginForm');
    const registrationForm = document.getElementById('registrationForm');

    function getCSRFToken() {
        const cookieValue = document.cookie.match(/csrftoken=([^;]+)/);
        return cookieValue ? cookieValue[1] : '';
    }

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        const loginError = document.getElementById('loginError');

        const response = await fetch("users/ajax-login/", {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),  // Функция для получения CSRF-токена
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });

        const data = await response.json();

        if (data.status === 'success') {
            window.location.reload();  // Перезагрузка страницы после успешного входа
        } else {
            loginError.textContent = data.message;  // Отображение ошибки
        }
    });

    registrationForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const registration_username = document.getElementById('registration_username').value;
        const registration_password = document.getElementById('registration_password').value;
        const registrationError = document.getElementById('registrationError');
        const registrationSuccess = document.getElementById('registrationSuccess');

        const response = await fetch("users/registration/", {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),  // Функция для получения CSRF-токена
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `username=${encodeURIComponent(registration_username)}&password=${encodeURIComponent(registration_password)}`
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Показываем сообщение об успешной регистрации
            registrationSuccess.textContent = 'Регистрация прошла успешно!';
            registrationSuccess.style.display = 'block';

            // Скрываем форму (по желанию)
            registrationForm.style.display = 'none';
        } else {
            // Показываем сообщение об ошибке
            registrationError.textContent = data.message;
            registrationError.style.display = 'block';
        }
    });

    // Логика для открытия и закрытия бокового меню
    if (menuButton && closeSidebar) {
        menuButton.addEventListener('click', () => {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.add('active');
            }
        });

        closeSidebar.addEventListener('click', () => {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.remove('active');
            }
        });
    }
})