const pages = document.querySelectorAll('.book-page');
const totalPages = pages.length;
let currentPage = 0;

// Build dots
const dotsContainer = document.getElementById('pageDots');
pages.forEach((_, i) => {
  const dot = document.createElement('div');
  dot.className = 'dot' + (i === 0 ? ' active' : '');
  dot.addEventListener('click', () => goToPage(i));
  dotsContainer.appendChild(dot);
});

function updateDots() {
  document.querySelectorAll('.dot').forEach((d, i) => {
    d.classList.toggle('active', i === currentPage);
  });
}

function updateButtons() {
  document.getElementById('prevBtn').disabled = currentPage === 0;
  document.getElementById('nextBtn').disabled = currentPage === totalPages - 1;
}

function goToPage(target) {
  if (target < 0 || target >= totalPages) return;
  if (target > currentPage) {
    for (let i = currentPage; i < target; i++) {
      pages[i].classList.add('is-flipped');
      pages[i].style.zIndex = totalPages - i;
    }
  } else {
    for (let i = currentPage - 1; i >= target; i--) {
      pages[i].classList.remove('is-flipped');
      pages[i].style.zIndex = totalPages - i;
    }
  }
  currentPage = target;
  updateDots();
  updateButtons();
}

function nextPage() { goToPage(currentPage + 1); }
function prevPage() { goToPage(currentPage - 1); }

pages.forEach((p, i) => { p.style.zIndex = totalPages - i; });
updateButtons();

document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextPage();
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') prevPage();
});

function handleSubmit(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  btn.textContent = 'Message envoyé ✓';
  btn.style.background = '#10b981';
  setTimeout(() => {
    btn.textContent = 'Send Message';
    btn.style.background = '';
    e.target.reset();
  }, 3000);
}
