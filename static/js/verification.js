// 🔐 verification.js - Обробка вікна верифікації коду

// Створюємо HTML-структуру для модального вікна верифікації
function injectVerificationModal() {
    if (document.getElementById('verification-modal')) return;

    const modalHtml = `
        <div id="verification-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 9999; font-family: sans-serif;">
            <div style="background: #2d2d3a; color: white; padding: 30px; border-radius: 12px; width: 90%; max-width: 400px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
                <div style="font-size: 3rem; margin-bottom: 10px;">✉️</div>
                <h3 style="margin-top: 0; font-size: 1.4rem;">Email Verification</h3>
                <p style="color: #b2bec3; font-size: 0.9rem; line-height: 1.4; margin-bottom: 20px;">
                    We have simulated sending a 6-digit code to your Gmail. <br>
                    <span style="color: #00d2d3; font-weight: bold;">Check your terminal / flask console to copy it!</span>
                </p>
                
                <input type="text" id="verification-input" placeholder="Enter 6-digit code" maxlength="6" 
                       style="width: 80%; padding: 12px; font-size: 1.2rem; text-align: center; border-radius: 8px; border: 2px solid #575766; background: #1e1e24; color: white; letter-spacing: 4px; margin-bottom: 15px; outline: none;">
                
                <div id="verify-error" style="color: #ff7675; font-size: 0.85rem; margin-bottom: 15px; display: none;"></div>
                <div id="verify-success" style="color: #2ecc71; font-size: 0.95rem; font-weight: bold; margin-bottom: 15px; display: none;"></div>

                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button onclick="closeVerificationModal()" style="background: #575766; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer;">Cancel</button>
                    <button onclick="submitVerificationCode()" id="confirm-verify-btn" style="background: #00d2d3; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold;">Verify</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function openVerificationModal() {
    injectVerificationModal();
    document.getElementById('verification-modal').style.display = 'flex';
    document.getElementById('verification-input').value = '';
    document.getElementById('verify-error').style.display = 'none';
    document.getElementById('verify-success').style.display = 'none';
}

function closeVerificationModal() {
    const modal = document.getElementById('verification-modal');
    if (modal) modal.style.display = 'none';
}

// Перевірка коду на бекенді
async function submitVerificationCode() {
    const codeInput = document.getElementById('verification-input').value.trim();
    const errorDiv = document.getElementById('verify-error');
    const successDiv = document.getElementById('verify-success');

    errorDiv.style.display = 'none';

    if (codeInput.length !== 6) {
        errorDiv.textContent = "Code must be exactly 6 digits.";
        errorDiv.style.display = 'block';
        return;
    }

    try {
        const response = await fetch('/api/auth/verify-code', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ code: codeInput })
        });

        const result = await response.json();

        if (response.ok) {
            // Повідомлення про успішне введення коду (англійською)
            successDiv.textContent = result.message; // "Correct verification code! Welcome."
            successDiv.style.display = 'block';

            // Затримка на 1.5 секунди, щоб користувач побачив напис, і редірект
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        } else {
            errorDiv.textContent = result.message;
            errorDiv.style.display = 'block';
        }
    } catch (err) {
        errorDiv.textContent = "Network error. Failed to verify.";
        errorDiv.style.display = 'block';
    }
}