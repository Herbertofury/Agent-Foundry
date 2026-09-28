const $ = (id) => document.getElementById(id);
let catalog = { items: [] };
let tabs = [];
let activeTab = null;
let pendingPermission = null;

function storeGet(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function storeSet(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* memory-only fallback */ }
}
const favorites = new Set(storeGet('favorites', []));

function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}

function primaryUrl(item) {
  return (item.sources || []).find((source) => source.verified !== false && /^https?:/.test(source.url || ''))?.url || '';
}

function renderCatalog() {
  const q = $('search').value.trim().toLowerCase();
  const filtered = catalog.items.filter((item) => JSON.stringify(item).toLowerCase().includes(q));
  $('count').textContent = `${filtered.length} projects`;
  $('catalog').innerHTML = filtered.map((item) => {
    const url = primaryUrl(item);
    return `<article class="card" data-id="${esc(item.id)}"><h2>${esc(item.name)}</h2><p class="meta">${esc((item.categories || []).join(' / '))}</p><p>${esc(item.summary || item.why || '')}</p><div class="actions"><button data-open="${esc(url)}" ${url ? '' : 'disabled'}>Open here</button><button data-external="${esc(url)}" ${url ? '' : 'disabled'}>Open in your browser</button><button data-favorite="${esc(item.id)}">${favorites.has(item.id) ? 'Unfavorite' : 'Favorite'}</button></div></article>`;
  }).join('');
}

function showCatalog() {
  $('catalogPage').hidden = false; $('browserPage').hidden = true;
  $('catalogMode').classList.add('active'); $('browserMode').classList.remove('active');
}
function showBrowser() {
  $('catalogPage').hidden = true; $('browserPage').hidden = false;
  $('browserMode').classList.add('active'); $('catalogMode').classList.remove('active');
  requestAnimationFrame(syncBounds);
}

function syncBounds() {
  if ($('browserPage').hidden) return;
  const rect = $('browserViewport').getBoundingClientRect();
  window.companion.browser.setBounds({ x: rect.x, y: rect.y, width: rect.width, height: rect.height });
}

function renderTabs() {
  const fixed = '<button id="newTab" title="New tab">+</button><button id="reopenTab" title="Reopen closed tab">Reopen</button>';
  $('tabStrip').innerHTML = fixed + tabs.map((tab) => `<span class="tab ${tab.active ? 'active' : ''}" data-tab="${esc(tab.id)}"><button data-activate="${esc(tab.id)}">${esc(tab.title || tab.label || 'Tab')}</button><button data-close="${esc(tab.id)}" title="Close">x</button></span>`).join('');
  activeTab = tabs.find((tab) => tab.active) || null;
  $('address').value = activeTab?.url === 'about:blank' ? '' : (activeTab?.url || '');
  $('back').disabled = !activeTab?.canGoBack;
  $('forward').disabled = !activeTab?.canGoForward;
  $('reload').textContent = activeTab?.loading ? 'Stop' : 'Reload';
  $('zoomReset').textContent = `${Math.round((activeTab?.zoomFactor || 1) * 100)}%`;
  syncBounds();
}

$('search').addEventListener('input', renderCatalog);
$('catalogMode').addEventListener('click', showCatalog);
$('browserMode').addEventListener('click', showBrowser);
$('catalog').addEventListener('click', async (event) => {
  const open = event.target.closest('[data-open]');
  const external = event.target.closest('[data-external]');
  const favorite = event.target.closest('[data-favorite]');
  if (open?.dataset.open) { await window.companion.browser.open(open.dataset.open, ''); showBrowser(); }
  if (external?.dataset.external) await window.companion.browser.openExternal(external.dataset.external);
  if (favorite) {
    favorites.has(favorite.dataset.favorite) ? favorites.delete(favorite.dataset.favorite) : favorites.add(favorite.dataset.favorite);
    storeSet('favorites', [...favorites]); renderCatalog();
  }
});
$('tabStrip').addEventListener('click', async (event) => {
  if (event.target.id === 'newTab') await window.companion.browser.newTab();
  if (event.target.id === 'reopenTab') await window.companion.browser.reopenClosed();
  if (event.target.dataset.activate) await window.companion.browser.activate(event.target.dataset.activate);
  if (event.target.dataset.close) await window.companion.browser.close(event.target.dataset.close);
});
$('addressForm').addEventListener('submit', async (event) => { event.preventDefault(); await window.companion.browser.navigate($('address').value); });
$('back').addEventListener('click', () => window.companion.browser.back());
$('forward').addEventListener('click', () => window.companion.browser.forward());
$('reload').addEventListener('click', () => window.companion.browser.reloadOrStop());
$('external').addEventListener('click', () => activeTab?.url && window.companion.browser.openExternal(activeTab.url));
$('copyUrl').addEventListener('click', () => activeTab?.url && window.companion.browser.copyUrl(activeTab.url));
$('findButton').addEventListener('click', () => { const text = prompt('Find in page'); if (text) window.companion.browser.find(text); });
$('zoomIn').addEventListener('click', () => window.companion.browser.zoom(0.1));
$('zoomOut').addEventListener('click', () => window.companion.browser.zoom(-0.1));
$('zoomReset').addEventListener('click', () => window.companion.browser.zoomReset());
window.addEventListener('resize', syncBounds);

window.companion.browser.onTabs((value) => { tabs = value; renderTabs(); });
window.companion.browser.onBoundsRequest(syncBounds);
window.companion.browser.onError((value) => { $('browserStatus').textContent = `Navigation error: ${value.errorDescription} - ${value.url}`; });
window.companion.browser.onDownload((value) => { $('browserStatus').textContent = `Download ${value.state}: ${value.filename}`; });
window.companion.browser.onPermissionRequest((value) => {
  pendingPermission = value;
  $('permissionText').textContent = `${value.url} requests ${value.permission}.`;
  $('permissionDialog').showModal();
});
$('permissionDialog').addEventListener('close', async () => {
  if (!pendingPermission) return;
  await window.companion.browser.permissionResponse(pendingPermission.requestId, $('permissionDialog').returnValue === 'allow');
  pendingPermission = null;
});

(async () => { catalog = await window.companion.loadCatalog(); renderCatalog(); })();
