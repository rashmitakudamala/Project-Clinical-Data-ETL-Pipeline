// Show/hide button based on scroll position
window.addEventListener('scroll', function() {
    const backToTop = document.getElementById('backToTop');
    if (backToTop && window.pageYOffset > 300) {
        backToTop.classList.add('show');
    } else if (backToTop) {
        backToTop.classList.remove('show');
    }
});

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}