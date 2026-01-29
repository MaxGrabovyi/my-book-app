async function loadBooks() {
    try {
        const response = await fetch('/api/books');
        if (response.status === 401) return;

        const books = await response.json();
        const list = document.getElementById('book-list');
        list.innerHTML = '';

        if (books.length === 0) {
            list.innerHTML = '<p style="text-align:center">No books yet.</p>';
            return;
        }

        books.forEach(book => {
            const card = document.createElement('div');
            card.className = 'book-card';
            card.onclick = () => openBookDetails(book.id);

            let extraInfo = '';
            if (book.status === 'Reading') {
                extraInfo = `<div class="info-line">📖 Page: <strong>${book.current_page || 0}</strong></div>`;
            } else if (book.status === 'Finished') {
                extraInfo = `<div class="info-line">⭐ Rating: <strong>${book.rating || 0}/10</strong></div>`;
            }

            card.innerHTML = `
                ${book.image_url ? `<img src="${book.image_url}" class="card-img">` : '<div class="no-img">No Cover</div>'}
                <div class="card-content">
                    <h3>${book.title}</h3>
                    <p class="author">${book.author}</p>
                    <div class="status-row">
                        <span class="status-badge status-${book.status.replace(/\s+/g, '-').toLowerCase()}">${book.status}</span>
                        ${extraInfo}
                    </div>
                </div>
            `;
            list.appendChild(card);
        });
    } catch (error) {
        console.error("Error loading books:", error);
    }
}

async function openBookDetails(id) {
    const res = await fetch(`/api/books/${id}`);
    const book = await res.json();

    const modal = document.getElementById('book-modal');
    const body = document.getElementById('modal-body');

    body.innerHTML = `
        <h2>${book.title}</h2>
        <p><strong>Author:</strong> ${book.author}</p>
        
        <label>Cover Image URL:</label>
        <input type="text" id="edit-image" value="${book.image_url || ''}" placeholder="http://...">
        
        <label>Description/Notes:</label>
        <textarea id="edit-desc" rows="4">${book.description || ''}</textarea>
        
        <label>Status:</label>
        <select id="edit-status" onchange="toggleFields(this.value)">
            <option value="In plan" ${book.status === 'In plan' ? 'selected' : ''}>In plan</option>
            <option value="Reading" ${book.status === 'Reading' ? 'selected' : ''}>Reading</option>
            <option value="Finished" ${book.status === 'Finished' ? 'selected' : ''}>Finished</option>
        </select>

        <div id="page-field" style="display: ${book.status === 'Reading' ? 'block' : 'none'}">
            <label>Current Page (max 300):</label>
            <input type="number" id="edit-page" 
                    min="0" max="300" 
                    value="${book.current_page || 0}"
                    oninput="if(this.value > 300) this.value = 300;">
        </div>

        <div id="rating-field" style="display: ${book.status === 'Finished' ? 'block' : 'none'}">
            <label>Rating (1-10):</label>
            <input type="number" id="edit-rating" 
                   min="0" max="10" 
                   value="${book.rating || 0}"
                   oninput="if(this.value > 10) this.value = 10;">
        </div>

        <div style="margin-top:20px;">
            <button class="save-btn" onclick="saveDetails(${book.id})">Save Changes</button>
            <button class="delete-btn" onclick="deleteBook(${book.id}); closeModal();">Delete Book</button>
        </div>
    `;
    modal.style.display = "flex";
}

function toggleFields(status) {
    document.getElementById('page-field').style.display = (status === 'Reading') ? 'block' : 'none';
    document.getElementById('rating-field').style.display = (status === 'Finished') ? 'block' : 'none';
}

async function saveDetails(id) {
    const data = {
        image_url: document.getElementById('edit-image').value,
        description: document.getElementById('edit-desc').value,
        status: document.getElementById('edit-status').value,
        current_page: document.getElementById('edit-page').value,
        rating: document.getElementById('edit-rating').value
    };

    await fetch(`/api/books/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    closeModal();
    loadBooks();
}

function closeModal() {
    document.getElementById('book-modal').style.display = "none";
}

async function updateStatus(id, newStatus) {
    try {
        const response = await fetch(`/api/books/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: newStatus})
        });
        if (response.status === 401) window.location.href = '/api/auth/login';
    } catch (error) { console.error("Update error:", error); }
}

let bookToDelete = null;

async function deleteBook(id) {
    bookToDelete = id;
    const confirmModal = document.getElementById('confirm-modal');
    confirmModal.style.display = 'flex';

    document.getElementById('confirm-ok-btn').onclick = async function() {
        try {
            const response = await fetch(`/api/books/${bookToDelete}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                showFlashMessage("Book deleted successfully!", "success");

                closeConfirm();
                closeModal();
                loadBooks();
            } else {
                showFlashMessage("Error: Could not delete book.", "error");
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                author: author
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

async function registerUser() {
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm').value;

    if (!email.endsWith('@gmail.com')) {
        alert("Please use a valid @gmail.com address.");
        return;
    }

    const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username,
            email,
            password,
            confirm_password: confirm
        })
    });

    const data = await response.json();
    if (data.success) {
        window.location.href = '/';
    } else {
        alert(data.message);
    }
}

document.addEventListener("DOMContentLoaded", loadBooks);