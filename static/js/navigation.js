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
        card.addEventListener('click', event => {
            if (event.target.closest('.btn-select')) return;
            card.classList.toggle('is-flipped');
        });
        card.addEventListener('keydown', event => {
            if (event.target !== card || !['Enter', ' '].includes(event.key)) return;
            event.preventDefault();
            card.classList.toggle('is-flipped');
        });
        card.querySelector('.btn-select').addEventListener('click', event => {
            event.stopPropagation();
            window.location.href = appUrl('configure', {}, card.dataset.method);
        });
    });
});
