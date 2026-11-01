/**
 * PhishGuard Dashboard Interactions
 * Modals, live simulation triggers, SMTP tester, real-time funnel updates.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Modal Dialog Controller
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    function closeModal(modal) {
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    document.querySelectorAll('[data-modal-target]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-modal-target');
            openModal(targetId);
        });
    });

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay || e.target.classList.contains('modal-close-btn') || e.target.closest('.modal-close-btn')) {
                closeModal(overlay);
            }
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(closeModal);
        }
    });

    // 2. Interactive Simulation Live Action Triggers
    // Allows administrators and testers to simulate participant actions with instant visual feedback
    document.querySelectorAll('.btn-trigger-action').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const targetId = btn.getAttribute('data-target-id');
            const action = btn.getAttribute('data-action');
            const campaignId = btn.getAttribute('data-campaign-id');
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

            btn.disabled = true;
            const originalText = btn.innerHTML;
            btn.innerHTML = '...';

            try {
                const response = await fetch(`/api/campaigns/${campaignId}/trigger-action`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    },
                    body: JSON.stringify({ target_id: targetId, action: action })
                });

                const data = await response.json();
                if (data.success) {
                    // Update status badge on this target row
                    const row = document.getElementById(`target-row-${targetId}`);
                    if (row) {
                        const statusBadge = row.querySelector('.target-status-badge');
                        if (statusBadge) {
                            statusBadge.className = `badge target-status-badge badge-${getStatusBadgeType(action)}`;
                            statusBadge.textContent = action.charAt(0).toUpperCase() + action.slice(1);
                        }
                    }
                    showToast(`Simulated event '${action}' logged successfully.`, 'success');
                } else {
                    showToast(`Simulation error: ${data.error}`, 'danger');
                }
            } catch (err) {
                showToast(`Request failed: ${err.message}`, 'danger');
            } finally {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    });

    function getStatusBadgeType(action) {
        if (action === 'open') return 'info';
        if (action === 'click') return 'danger';
        if (action === 'report') return 'success';
        if (action === 'train') return 'primary';
        return 'subtle';
    }

    // 3. SMTP Server Reachability Tester
    const smtpTestBtn = document.getElementById('btnTestSmtp');
    if (smtpTestBtn) {
        smtpTestBtn.addEventListener('click', async () => {
            const host = document.getElementById('smtp_host')?.value || 'localhost';
            const port = document.getElementById('smtp_port')?.value || '1025';
            const useTls = document.getElementById('smtp_tls')?.checked || false;
            const resultBox = document.getElementById('smtpTestResult');
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

            smtpTestBtn.disabled = true;
            smtpTestBtn.textContent = 'Testing connection...';
            if (resultBox) {
                resultBox.style.display = 'block';
                resultBox.className = 'alert alert-info';
                resultBox.textContent = `Attempting socket connection to ${host}:${port}...`;
            }

            try {
                const res = await fetch('/api/smtp/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    },
                    body: JSON.stringify({ host, port, use_tls: useTls })
                });
                const data = await res.json();
                if (resultBox) {
                    resultBox.className = `alert alert-${data.success ? 'success' : 'danger'}`;
                    resultBox.textContent = data.message;
                }
            } catch (err) {
                if (resultBox) {
                    resultBox.className = 'alert alert-danger';
                    resultBox.textContent = `Error: ${err.message}`;
                }
            } finally {
                smtpTestBtn.disabled = false;
                smtpTestBtn.textContent = 'Test SMTP Reachability';
            }
        });
    }

    // Simple toast notification helper
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type}`;
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 9999;
            box-shadow: var(--shadow-lg);
            animation: modalIn 200ms ease;
            max-width: 380px;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 300ms ease';
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }
    window.showToast = showToast;
});
