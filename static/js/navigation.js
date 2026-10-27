// Navigation & Visual micro-interactions
document.addEventListener('DOMContentLoaded', () => {
    // Adding minor button click effects
    const buttons = document.querySelectorAll('.btn-primary, .btn-secondary, .btn-control');
    buttons.forEach(btn => {
        btn.addEventListener('mousedown', () => {
            btn.style.transform = 'scale(0.96)';
        });
        btn.addEventListener('mouseup', () => {
            btn.style.transform = '';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = '';
        });
    });

    document.querySelectorAll('.attack-card').forEach(card => {
        card.addEventListener('click', () => {
            window.location.href = appUrl('configure', {}, card.dataset.method);
        });
    });
});
