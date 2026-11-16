// Shared quiz widget: <div class="q" data-answer="1" data-why="..."><p>question</p><button>..</button>...</div>
document.querySelectorAll('.q').forEach(q => {
  const buttons = [...q.querySelectorAll('button')];
  const why = document.createElement('div');
  why.className = 'why';
  q.appendChild(why);
  buttons.forEach((b, i) => b.addEventListener('click', () => {
    buttons.forEach(x => x.classList.remove('ok', 'bad'));
    const right = i === Number(q.dataset.answer);
    b.classList.add(right ? 'ok' : 'bad');
    why.textContent = right ? 'Right. ' + q.dataset.why : 'Not quite. Try again.';
  }));
});
