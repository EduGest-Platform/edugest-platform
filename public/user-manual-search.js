(() => {
  const panel = document.getElementById('manual-search')
  const input = document.getElementById('manual-query')
  const results = document.getElementById('manual-results')
  const matches = document.getElementById('manual-matches')
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  const sections = Array.from(document.querySelectorAll('main > section[id]')).map(section => ({
    id: section.id,
    title: section.querySelector('h2').textContent,
    text: normalize(section.textContent)
  }))
  function search() {
    const words = normalize(input.value).trim().split(/\s+/).filter(Boolean)
    matches.replaceChildren()
    if (!words.length) {
      results.textContent = 'Escribe una palabra para encontrar secciones del manual.'
      return
    }
    const found = sections.filter(section => words.every(word => section.text.includes(word)))
    results.textContent = found.length ? `${found.length} secciones encontradas.` : 'No hay coincidencias. Prueba con otras palabras.'
    for (const section of found) {
      const item = document.createElement('li')
      const link = document.createElement('a')
      link.href = '#' + section.id
      link.textContent = section.title
      item.append(link)
      matches.append(item)
    }
  }
  input.addEventListener('input', search)
  document.getElementById('manual-reset').addEventListener('click', () => {
    input.value = ''
    search()
    input.focus()
  })
  search()
  panel.hidden = false
})()
