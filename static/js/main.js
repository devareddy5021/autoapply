/**
 * JobAutoApply - Interactive Client Features
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // Auto-dismiss alert notifications after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Animate progress meters on page load
    const meters = document.querySelectorAll('.match-meter-fill');
    meters.forEach(meter => {
        const targetWidth = meter.getAttribute('data-score') || '0';
        meter.style.width = '0%';
        setTimeout(() => {
            meter.style.width = targetWidth + '%';
        }, 150);
    });
});
