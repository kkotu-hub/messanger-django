document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('user-search-input');
    const searchResults = document.getElementById('search-results');
    const roomId = document.getElementById('room-data').dataset.roomId;
    let debounceTimer;

    // Функция для поиска пользователей
    const searchUsers = async (query) => {
        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/chat/search_users/?q=${encodeURIComponent(query)}&room_id=${roomId}`);
            const data = await response.json();
            
            if (data.users && data.users.length > 0) {
                searchResults.innerHTML = data.users.map(user => `
                    <div class="search-result-item" 
                         data-user-id="${user.id}" 
                         data-username="${user.username}">
                        <div class="font-weight-bold">${user.full_name || user.username}</div>
                        <div class="text-muted small">@${user.username}</div>
                    </div>
                `).join('');
                searchResults.style.display = 'block';
            } else {
                searchResults.innerHTML = '<div class="search-result-item">Ничего не найдено</div>';
                searchResults.style.display = 'block';
            }
        } catch (error) {
            console.error('Ошибка поиска:', error);
            searchResults.style.display = 'none';
        }
    };

    // Обработчик ввода с debounce
    searchInput.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            searchUsers(e.target.value.trim());
        }, 300);
    });

    // Выбор пользователя из результатов
    searchResults.addEventListener('click', function(e) {
        const resultItem = e.target.closest('.search-result-item');
        if (resultItem) {
            searchInput.value = resultItem.dataset.username;
            searchResults.style.display = 'none';
            
            // Можно автоматически отправить форму
            document.getElementById('add-user-form').submit();
        }
    });

    // Скрытие результатов при клике вне поля
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });

    // Подтверждение удаления участника
    document.querySelectorAll('.remove-member-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Вы уверены, что хотите удалить этого участника?')) {
                e.preventDefault();
            }
        });
    });
});