/**
 * Odd 2 - Main JavaScript
 * Handles countdown timer, payment modal, and API interactions
 */

// ==========================================================================
// Countdown Timer
// ==========================================================================

class CountdownTimer {
    constructor(initialData) {
        this.totalSeconds = initialData.hours * 3600 + initialData.minutes * 60 + initialData.seconds;
        this.hoursEl = document.getElementById('hours');
        this.minutesEl = document.getElementById('minutes');
        this.secondsEl = document.getElementById('seconds');

        if (this.hoursEl && this.minutesEl && this.secondsEl) {
            this.start();
        }
    }

    start() {
        this.update();
        this.interval = setInterval(() => this.tick(), 1000);
    }

    tick() {
        if (this.totalSeconds <= 0) {
            // Refresh page when countdown ends
            location.reload();
            return;
        }

        this.totalSeconds--;
        this.update();
    }

    update() {
        const hours = Math.floor(this.totalSeconds / 3600);
        const minutes = Math.floor((this.totalSeconds % 3600) / 60);
        const seconds = this.totalSeconds % 60;

        this.hoursEl.textContent = hours.toString().padStart(2, '0');
        this.minutesEl.textContent = minutes.toString().padStart(2, '0');
        this.secondsEl.textContent = seconds.toString().padStart(2, '0');
    }

    stop() {
        if (this.interval) {
            clearInterval(this.interval);
        }
    }
}

// Initialize countdown when page loads
document.addEventListener('DOMContentLoaded', () => {
    if (window.initialCountdown) {
        new CountdownTimer(window.initialCountdown);
    }

    // Initialize social proof animations
    initSocialProof();
});


// ==========================================================================
// Social Proof Animations (Persuasion Techniques)
// ==========================================================================

function initSocialProof() {
    // Viewer count - fluctuates between 35-65
    const viewerEl = document.getElementById('viewerCount');
    const modalViewersEl = document.getElementById('modalViewers');

    if (viewerEl) {
        setInterval(() => {
            const newCount = Math.floor(Math.random() * 31) + 35; // 35-65
            viewerEl.textContent = newCount;
            if (modalViewersEl) modalViewersEl.textContent = Math.floor(newCount / 2);
        }, 3000 + Math.random() * 2000);
    }

    // Buyer count - occasionally increases
    const buyerEl = document.getElementById('buyerCount');
    if (buyerEl) {
        let buyerCount = parseInt(buyerEl.textContent) || 127;
        setInterval(() => {
            if (Math.random() > 0.7) { // 30% chance to increase
                buyerCount += Math.floor(Math.random() * 3) + 1;
                buyerEl.textContent = buyerCount;

                // Flash effect
                buyerEl.style.transition = 'color 0.3s';
                buyerEl.style.color = '#fbbf24';
                setTimeout(() => {
                    buyerEl.style.color = '';
                }, 500);
            }
        }, 8000 + Math.random() * 7000);
    }

    // Spots left - slowly decreases
    const spotsEl = document.getElementById('spotsLeft');
    if (spotsEl) {
        let spots = parseInt(spotsEl.textContent) || 12;
        setInterval(() => {
            if (spots > 3 && Math.random() > 0.6) {
                spots--;
                spotsEl.textContent = spots;

                // Shake effect when low
                if (spots <= 5) {
                    spotsEl.parentElement.classList.add('shake-urgent');
                    setTimeout(() => spotsEl.parentElement.classList.remove('shake-urgent'), 500);
                }
            }
        }, 15000 + Math.random() * 10000);
    }
}


// ==========================================================================
// Payment Modal
// ==========================================================================

function showPaymentModal() {
    const modal = document.getElementById('paymentModal');
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function hidePaymentModal() {
    const modal = document.getElementById('paymentModal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hidePaymentModal();
    }
});


// ==========================================================================
// Payment Handling
// ==========================================================================

async function submitPayment(event) {
    event.preventDefault();

    const phoneNumber = document.getElementById('phoneNumber').value;
    const payBtn = document.getElementById('payBtn');
    const btnText = payBtn.querySelector('.btn-text');
    const btnLoading = payBtn.querySelector('.btn-loading');

    if (!phoneNumber) {
        showNotification('Please enter your phone number', 'error');
        return;
    }

    // Show loading state
    payBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoading.style.display = 'inline';

    try {
        const response = await fetch('/api/initiate-payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ phone_number: phoneNumber })
        });

        const data = await response.json();

        if (data.success) {
            showNotification(data.message, 'success');

            // Start polling for payment status
            if (data.transaction_id) {
                pollPaymentStatus(data.transaction_id);
            }
        } else {
            showNotification(data.error || 'Payment failed', 'error');
            resetPayButton();
        }

    } catch (error) {
        console.error('Payment error:', error);
        showNotification('Connection error. Please try again.', 'error');
        resetPayButton();
    }
}

function resetPayButton() {
    const payBtn = document.getElementById('payBtn');
    const btnText = payBtn.querySelector('.btn-text');
    const btnLoading = payBtn.querySelector('.btn-loading');

    payBtn.disabled = false;
    btnText.style.display = 'inline';
    btnLoading.style.display = 'none';
}

async function pollPaymentStatus(transactionId) {
    const maxAttempts = 60; // 5 minutes (every 5 seconds)
    let attempts = 0;

    const poll = async () => {
        try {
            const response = await fetch(`/api/check-payment/${transactionId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                showNotification('Payment successful! Unlocking VIP prediction...', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                return;
            }

            if (data.status === 'failed') {
                showNotification('Payment failed. Please try again.', 'error');
                resetPayButton();
                return;
            }

            // Continue polling if pending
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 5000);
            } else {
                showNotification('Payment timeout. Please check your phone.', 'warning');
                resetPayButton();
            }

        } catch (error) {
            console.error('Poll error:', error);
            attempts++;
            if (attempts < maxAttempts) {
                setTimeout(poll, 5000);
            }
        }
    };

    // Start polling after 3 seconds
    setTimeout(poll, 3000);
}


// ==========================================================================
// Demo Payment (for testing)
// ==========================================================================

async function demoPayment() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Processing...';

    try {
        const response = await fetch('/api/demo-payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Demo payment successful!', 'success');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showNotification(data.error || 'Demo payment failed', 'error');
            btn.disabled = false;
            btn.textContent = '🧪 Demo Payment (Skip Real Payment)';
        }

    } catch (error) {
        console.error('Demo payment error:', error);
        showNotification('Connection error', 'error');
        btn.disabled = false;
        btn.textContent = '🧪 Demo Payment (Skip Real Payment)';
    }
}


// ==========================================================================
// Notifications
// ==========================================================================

function showNotification(message, type = 'info') {
    // Remove any existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;

    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 20px;
        border-radius: 12px;
        font-size: 14px;
        font-weight: 500;
        animation: slideIn 0.3s ease;
        max-width: 400px;
    `;

    // Type-specific styles
    const styles = {
        success: 'background: #22c55e; color: white;',
        error: 'background: #ef4444; color: white;',
        warning: 'background: #f59e0b; color: white;',
        info: 'background: #3b82f6; color: white;'
    };

    notification.style.cssText += styles[type] || styles.info;

    // Style close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: inherit;
        font-size: 20px;
        cursor: pointer;
        opacity: 0.8;
        padding: 0;
        line-height: 1;
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Add animation keyframes to document
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOut {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);


// ==========================================================================
// Utility Functions
// ==========================================================================

function formatTime(date) {
    return new Date(date).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        day: 'numeric',
        month: 'short'
    });
}


// ==========================================================================
// Admin Functions (for development)
// ==========================================================================

async function triggerPredictionGeneration() {
    try {
        const response = await fetch('/admin/generate-predictions', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Predictions generated!', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showNotification(data.error || 'Generation failed', 'error');
        }

    } catch (error) {
        console.error('Error:', error);
        showNotification('Connection error', 'error');
    }
}

// Expose to console for debugging
window.odd2 = {
    triggerPredictionGeneration,
    showNotification
};
