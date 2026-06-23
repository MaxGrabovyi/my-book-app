// 🟢 State ---------------------------------------------------------------------
let currentTab = 'book'; // 'book' | 'movie' | 'series' | 'anime'
let currentCollectionData = []; // Глобальний масив для збереження поточної вкладки медіа

// 🟢 Tab switching --------------------------------------------------------------
function switchTab(tab) {
    currentTab = tab;

    const searchInput = document.getElementById('search-input');
    const statusFilter = document.getElementById('status-filter');
    if (searchInput) searchInput.value = '';
    if (statusFilter) statusFilter.value = 'all';

    document.querySelectorAll('.media-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    updateAddForm(tab);

    loadBooks();
}

function updateAddForm(tab) {
    const authorInput = document.getElementById('book-author');
    const mainHeader = document.getElementById('form-main-header');
    const titleInput = document.getElementById('book-title');

    const labels = {
        book: {title: 'Book Title', author: 'Author Name', header: 'Add a New Book'},
        movie: {title: 'Movie Title', author: 'Director Name', header: 'Add a New Movie'},
        series: {title: 'Series Title', author: 'Studio / Creator', header: 'Add a New Series'},
        anime: {title: 'Anime Title', author: 'Studio Name', header: 'Add a New Anime'},
    };

    const l = labels[tab] || labels.book;
    if (titleInput) titleInput.placeholder = l.title;
    if (authorInput) authorInput.placeholder = l.author;
    if (mainHeader) mainHeader.textContent = l.header;
}

// 🟢 Load list ------------------------------------------------------------------
async function loadBooks() {
    try {
        const response = await fetch(`/api/books?type=${currentTab}`);
        if (response.status === 401) return;

        currentCollectionData = await response.json();
        filterCollection();

    } catch (error) {
        console.error("Error loading items:", error);
    }
}

function filterCollection() {
    const list = document.getElementById('book-list');
    if (!list) return;
    list.innerHTML = '';

    const searchQuery = document.getElementById('search-input')?.value.toLowerCase().trim() || '';
    const statusFilter = document.getElementById('status-filter')?.value || 'all';

    const filteredBooks = currentCollectionData.filter(book => {
        const matchesSearch = book.title.toLowerCase().includes(searchQuery) ||
            (book.author && book.author.toLowerCase().includes(searchQuery));

        let matchesStatus = true;
        if (statusFilter !== 'all') {
            if (statusFilter === 'Active') {
                matchesStatus = (book.status === 'Reading' || book.status === 'Watching');
            } else {
                matchesStatus = (book.status === statusFilter);
            }
        }
        return matchesSearch && matchesStatus;
    });

    if (filteredBooks.length === 0) {
        const emptyLabels = {
            book: 'No books found.',
            movie: 'No movies found.',
            series: 'No series found.',
            anime: 'No anime found.',
        };
        list.innerHTML = `<p style="text-align:center; color: #888; width: 100%; margin-top: 15px;">${searchQuery || statusFilter !== 'all' ? 'No items match your filters.' : emptyLabels[currentTab]}</p>`;
        return;
    }

    filteredBooks.forEach(book => {
        const card = document.createElement('div');
        card.className = 'book-card';
        card.onclick = () => openBookDetails(book.id);

        let extraInfo = '';

        if (book.status === 'Reading' || book.status === 'Watching') {
            if (currentTab === 'book') {
                extraInfo = `<div class="info-line">📖 Page: <strong>${book.current_page || 0}</strong></div>`;
            } else if (currentTab === 'series' || currentTab === 'anime') {
                extraInfo = `
                    <div class="info-line">🎬 Season: <strong>${book.current_season || 1}</strong></div>
                    <div class="info-line">🎞️ Episode: <strong>${book.current_page || 0}</strong></div>`;
            } else if (currentTab === 'movie') {
                const totalMinutes = book.current_page || 0;
                const hours = Math.floor(totalMinutes / 60);
                const mins = totalMinutes % 60;
                const timeString = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
                extraInfo = `<div class="info-line">⏱️ Time: <strong>${timeString}</strong></div>`;
            }
        } else if (book.status === 'Finished') {
            extraInfo = `<div class="info-line">⭐ Rating: <strong>${book.rating || 0}/10</strong></div>`;
        } else {
            extraInfo = `<div class="info-line" style="color: #888;">⏳ Waiting</div>`;
        }

        const statusClass = book.status.replace(/\s+/g, '-').toLowerCase();

        const statusColors = {
            'in-plan': '#7f8c8d',
            'reading': '#2ecc71',
            'watching': '#2ecc71',
            'finished': '#9b59b6'
        };
        const currentBadgeColor = statusColors[statusClass] || '#007bff';

        card.innerHTML = `
    ${book.image_url ? `<img src="${book.image_url}" class="card-img">` : '<div class="no-img">No Cover</div>'}
    <div class="card-content">
        <h3>${book.title}</h3>
        <p class="author">${book.author}</p>
        <div class="status-row" style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; width: 100%;">
            <span class="status-badge status-${statusClass}" style="background-color: ${currentBadgeColor}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: bold; display: inline-block;">
                ${book.status}
            </span>
            <div class="extra-info-container">${extraInfo}</div>
        </div>
    </div>
`;
        list.appendChild(card);
    });
}

// 🟢 Open details modal ---------------------------------------------------------
async function openBookDetails(id) {
    const res = await fetch(`/api/books/${id}`);
    const book = await res.json();
    const tab = book.media_type || 'book';

    const modal = document.getElementById('book-modal');
    const body = document.getElementById('modal-body');

    const isMedia = (tab === 'movie' || tab === 'series' || tab === 'anime');
    const statusOptions = isMedia
        ? ['In plan', 'Watching', 'Finished']
        : ['In plan', 'Reading', 'Finished'];
    const currentStatus = book.status;

    const statusHTML = statusOptions.map(s =>
        `<option value="${s}" ${currentStatus === s ? 'selected' : ''}>${s}</option>`
    ).join('');

    let progressLabel = 'Current Page (max 999)';
    let progressMax = 999;

    if (tab === 'series' || tab === 'anime') {
        progressLabel = 'Current Episode';
    } else if (tab === 'movie') {
        progressLabel = 'Time Stopped (Total Minutes)';
    }

    const authorLabel = tab === 'book' ? 'Author' : tab === 'movie' ? 'Director' : 'Studio / Creator';

    const watchingStatus = isMedia ? 'Watching' : 'Reading';
    const showProgress = currentStatus === watchingStatus;
    const showSeason = (tab === 'series' || tab === 'anime') && showProgress;

    body.innerHTML = `
        <h2>${book.title}</h2>
        <p><strong>${authorLabel}:</strong> ${book.author}</p>
        
        <label>Cover Image URL:</label>
        <input type="text" id="edit-image" value="${book.image_url || ''}" placeholder="http://...">
        
        <label>Description / Notes:</label>
        <textarea id="edit-desc" rows="4">${book.description || ''}</textarea>
        
        <label>Status:</label>
        <select id="edit-status" onchange="toggleFields(this.value, '${tab}')">
            ${statusHTML}
        </select>

        ${(tab === 'series' || tab === 'anime') ? `
        <div id="season-field" style="display: ${showSeason ? 'block' : 'none'}">
            <label>Current Season:</label>
            <input type="number" id="edit-season" min="1" max="99" value="${book.current_season || 1}"
                   oninput="if(this.value < 1) this.value = 1; if(this.value > 99) this.value = 99;">
        </div>` : ''}

        <div id="page-field" style="display: ${showProgress ? 'block' : 'none'}">
            <label id="dynamic-progress-label">${progressLabel}:</label>
            <input type="number" id="edit-page" 
                    min="0" max="${progressMax}" 
                    value="${book.current_page || 0}"
                    oninput="if(this.value > ${progressMax}) this.value = ${progressMax};">
            ${tab === 'movie' ? `<small style="color: #888; display:block; margin-top:4px;">Tip: 1h 30m = 90 mins</small>` : ''}
        </div>

        <div id="rating-field" style="display: ${currentStatus === 'Finished' ? 'block' : 'none'}">
            <label>Rating (1-10):</label>
            <input type="number" id="edit-rating" 
                   min="0" max="10" 
                   value="${book.rating || 0}"
                   oninput="if(this.value > 10) this.value = 10;">
        </div>

        <div style="margin-top:20px;">
            <button class="save-btn" onclick="saveDetails(${book.id}, '${tab}')">Save Changes</button>
            <button class="delete-btn" onclick="deleteBook(${book.id}); closeModal();">Delete</button>
        </div>
    `;
    modal.style.display = "flex";
}

// 🟢 Toggle fields when status changes ----------------------------------------
function toggleFields(status, tab) {
    const isMedia = (tab === 'movie' || tab === 'series' || tab === 'anime');
    const watchingStatus = isMedia ? 'Watching' : 'Reading';
    const isWatching = status === watchingStatus;
    const isFinished = status === 'Finished';

    const pageField = document.getElementById('page-field');
    const ratingField = document.getElementById('rating-field');
    const seasonField = document.getElementById('season-field');
    const labelField = document.getElementById('dynamic-progress-label');

    if (pageField) pageField.style.display = isWatching ? 'block' : 'none';
    if (ratingField) ratingField.style.display = isFinished ? 'block' : 'none';
    if (seasonField) seasonField.style.display = (isWatching && (tab === 'series' || tab === 'anime')) ? 'block' : 'none';

    if (labelField) {
        if (tab === 'movie') labelField.textContent = 'Time Stopped (Total Minutes):';
        else if (tab === 'series' || tab === 'anime') labelField.textContent = 'Current Episode:';
        else labelField.textContent = 'Current Page (max 999):';
    }
}

// 🟢 Save changes ---------------------------------------------------------------
async function saveDetails(id, tab) {
    const seasonEl = document.getElementById('edit-season');
    const data = {
        image_url: document.getElementById('edit-image').value,
        description: document.getElementById('edit-desc').value,
        status: document.getElementById('edit-status').value,
        current_page: document.getElementById('edit-page')?.value || 0,
        rating: document.getElementById('edit-rating')?.value || 0,
        current_season: seasonEl ? (seasonEl.value || 1) : 1,
    };

    await fetch(`/api/books/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    closeModal();
    loadBooks();
}

function closeModal() {
    document.getElementById('book-modal').style.display = "none";
}

// 🟢 Update status inline -------------------------------------------------------
async function updateStatus(id, newStatus) {
    try {
        const response = await fetch(`/api/books/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: newStatus})
        });
        if (response.status === 401) window.location.href = '/api/auth/login';
    } catch (error) {
        console.error("Update error:", error);
    }
}

// 🟢 Delete ---------------------------------------------------------------------
let bookToDelete = null;

async function deleteBook(id) {
    bookToDelete = id;
    const confirmModal = document.getElementById('confirm-modal');
    confirmModal.style.display = 'flex';

    document.getElementById('confirm-ok-btn').onclick = async function () {
        try {
            const response = await fetch(`/api/books/${bookToDelete}`, {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'}
            });

            if (response.ok) {
                showFlashMessage("Deleted successfully!", "success");
                closeConfirm();
                closeModal();
                loadBooks();
            } else {
                showFlashMessage("Error: Could not delete.", "error");
            }
        } catch (error) {
            console.error("Delete error:", error);
            showFlashMessage("Network error!", "error");
        }
    };
}

function closeConfirm() {
    document.getElementById('confirm-modal').style.display = 'none';
    bookToDelete = null;
}

// 🟢 Flash message --------------------------------------------------------------
function showFlashMessage(text, type) {
    const container = document.getElementById('alert-container');
    const alertDiv = document.createElement('div');

    alertDiv.style.cssText = `
        background-color: #ff7675; 
        color: white; 
        padding: 15px; 
        border-radius: 8px; 
        text-align: center; 
        margin-bottom: 10px; 
        font-weight: bold; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: opacity 0.5s ease;
    `;
    alertDiv.innerText = text;
    container.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.style.opacity = '0';
        setTimeout(() => alertDiv.remove(), 500);
    }, 3000);
}

// 🟢 Add item -------------------------------------------------------------------
async function addBook() {
    const titleEl = document.getElementById('book-title');
    const authorEl = document.getElementById('book-author');

    const title = titleEl.value.trim();
    const author = authorEl.value.trim();

    if (!title) {
        alert("Please enter a title!");
        return;
    }

    try {
        const response = await fetch('/api/books', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                title: title,
                author: author,
                media_type: currentTab,   // send current tab as media_type
            })
        });

        if (response.status === 401) {
            window.location.href = '/api/auth/register';
            return;
        }

        if (response.ok) {
            titleEl.value = '';
            authorEl.value = '';
            loadBooks();
        } else {
            const errorData = await response.json();
            alert("Error: " + errorData.error);
        }
    } catch (error) {
        console.error("Network error:", error);
    }
}

// 🟢 Init -----------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    switchTab('book');
});