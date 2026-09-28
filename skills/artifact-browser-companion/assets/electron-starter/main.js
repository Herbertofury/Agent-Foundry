const { app, BrowserWindow, WebContentsView, ipcMain, shell, clipboard, session } = require('electron');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

app.enableSandbox();

let win;
let activeTabId = null;
let nextTabId = 1;
const tabs = new Map();
const closedTabs = [];
const pendingPermissions = new Map();
let permissionCounter = 1;

function safeHttpUrl(input) {
  try {
    const url = new URL(input);
    return ['http:', 'https:'].includes(url.protocol) ? url.toString() : null;
  } catch {
    return null;
  }
}

function send(channel, payload) {
  if (win && !win.isDestroyed()) win.webContents.send(channel, payload);
}

function tabSnapshot(tab) {
  const wc = tab.view.webContents;
  return {
    id: tab.id,
    url: wc.getURL(),
    title: wc.getTitle() || tab.label || wc.getURL() || 'New Tab',
    label: tab.label || '',
    loading: wc.isLoading(),
    canGoBack: wc.navigationHistory.canGoBack(),
    canGoForward: wc.navigationHistory.canGoForward(),
    zoomFactor: wc.getZoomFactor(),
    active: tab.id === activeTabId
  };
}

function publishTabs() {
  send('browser:tabs', [...tabs.values()].map(tabSnapshot));
}

function installTabEvents(tab) {
  const wc = tab.view.webContents;
  const update = () => publishTabs();
  ['did-start-loading', 'did-stop-loading', 'page-title-updated', 'did-navigate', 'did-navigate-in-page'].forEach((eventName) => wc.on(eventName, update));
  wc.on('page-favicon-updated', (_event, favicons) => send('browser:favicon', { id: tab.id, favicon: favicons[0] || '' }));
  wc.on('did-fail-load', (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    if (isMainFrame) send('browser:error', { id: tab.id, errorCode, errorDescription, url: validatedURL });
  });
  wc.on('will-navigate', (event, url) => {
    if (!safeHttpUrl(url) && url !== 'about:blank') event.preventDefault();
  });
  wc.setWindowOpenHandler(({ url }) => {
    const safe = safeHttpUrl(url);
    if (safe) createTab(safe, '');
    return { action: 'deny' };
  });
}

function createTab(url = 'about:blank', label = '') {
  const id = `tab-${nextTabId++}`;
  const view = new WebContentsView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      partition: 'persist:artifact-browser'
    }
  });
  const tab = { id, view, label };
  tabs.set(id, tab);
  win.contentView.addChildView(view);
  installTabEvents(tab);
  activateTab(id);
  if (url === 'about:blank' || safeHttpUrl(url)) view.webContents.loadURL(url);
  publishTabs();
  return id;
}

function activateTab(id) {
  if (!tabs.has(id)) return;
  activeTabId = id;
  for (const [tabId, tab] of tabs) tab.view.setVisible(tabId === id);
  publishTabs();
}

function closeTab(id) {
  const tab = tabs.get(id);
  if (!tab) return;
  closedTabs.unshift({ url: tab.view.webContents.getURL(), label: tab.label, title: tab.view.webContents.getTitle() });
  closedTabs.splice(20);
  win.contentView.removeChildView(tab.view);
  tab.view.webContents.close();
  tabs.delete(id);
  if (activeTabId === id) {
    activeTabId = [...tabs.keys()].at(-1) || null;
    if (activeTabId) activateTab(activeTabId);
  }
  publishTabs();
}

function activeContents() {
  return activeTabId && tabs.get(activeTabId) ? tabs.get(activeTabId).view.webContents : null;
}

function createWindow() {
  win = new BrowserWindow({
    width: 1420,
    height: 900,
    minWidth: 920,
    minHeight: 640,
    title: '__APP_NAME__',
    backgroundColor: '#10121f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });
  win.loadFile('index.html');
  win.on('resize', () => send('browser:request-bounds'));
  win.on('closed', () => {
    for (const tab of tabs.values()) {
      if (!tab.view.webContents.isDestroyed()) tab.view.webContents.close();
    }
    tabs.clear();
    activeTabId = null;
    win = null;
  });
}

app.whenReady().then(() => {
  createWindow();
  const browserSession = session.fromPartition('persist:artifact-browser');
  browserSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const requestId = `permission-${permissionCounter++}`;
    pendingPermissions.set(requestId, callback);
    send('browser:permission-request', {
      requestId,
      permission,
      url: details.requestingUrl || webContents.getURL()
    });
  });
  browserSession.on('will-download', (_event, item) => {
    const id = crypto.randomUUID();
    const snapshot = () => ({
      id,
      filename: item.getFilename(),
      url: item.getURL(),
      receivedBytes: item.getReceivedBytes(),
      totalBytes: item.getTotalBytes(),
      state: item.getState()
    });
    send('browser:download', snapshot());
    item.on('updated', () => send('browser:download', snapshot()));
    item.once('done', (_e, state) => send('browser:download', { ...snapshot(), state }));
  });
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

ipcMain.handle('catalog:load', async () => {
  const file = path.join(__dirname, 'data', 'catalog.json');
  return JSON.parse(fs.readFileSync(file, 'utf8'));
});

ipcMain.handle('browser:open', (_e, url, label) => {
  const safe = safeHttpUrl(url);
  if (!safe) throw new Error('Only HTTP(S) URLs may be opened in a browser tab.');
  return createTab(safe, String(label || ''));
});
ipcMain.handle('browser:new-tab', () => createTab());
ipcMain.handle('browser:activate', (_e, id) => activateTab(String(id)));
ipcMain.handle('browser:close', (_e, id) => closeTab(String(id)));
ipcMain.handle('browser:reopen-closed', () => {
  const last = closedTabs.shift();
  return last ? createTab(last.url || 'about:blank', last.label || last.title || '') : null;
});
ipcMain.handle('browser:navigate', (_e, input) => {
  const wc = activeContents();
  if (!wc) return false;
  const safe = safeHttpUrl(input);
  if (!safe) throw new Error('Enter a full HTTP(S) URL.');
  wc.loadURL(safe);
  return true;
});
ipcMain.handle('browser:back', () => {
  const wc = activeContents();
  if (!wc) return false;
  const history = wc.navigationHistory;
  if (history.canGoBack()) history.goBack();
  return true;
});
ipcMain.handle('browser:forward', () => {
  const wc = activeContents();
  if (!wc) return false;
  const history = wc.navigationHistory;
  if (history.canGoForward()) history.goForward();
  return true;
});
ipcMain.handle('browser:reload-or-stop', () => {
  const wc = activeContents();
  if (!wc) return false;
  wc.isLoading() ? wc.stop() : wc.reload();
  return true;
});
ipcMain.handle('browser:external', async (_e, url) => {
  const safe = safeHttpUrl(url);
  if (!safe) throw new Error('Refusing to open a non-HTTP(S) URL externally.');
  await shell.openExternal(safe);
  return safe;
});
ipcMain.handle('browser:copy-url', (_e, url) => {
  const safe = safeHttpUrl(url);
  if (!safe) return false;
  clipboard.writeText(safe);
  return true;
});
ipcMain.handle('browser:find', (_e, text) => {
  const wc = activeContents();
  if (!wc || !text) return false;
  wc.findInPage(String(text));
  return true;
});
ipcMain.handle('browser:stop-find', () => {
  const wc = activeContents();
  if (wc) wc.stopFindInPage('clearSelection');
  return true;
});
ipcMain.handle('browser:zoom', (_e, delta) => {
  const wc = activeContents();
  if (!wc) return 1;
  const next = Math.max(0.5, Math.min(3, wc.getZoomFactor() + Number(delta || 0)));
  wc.setZoomFactor(next);
  publishTabs();
  return next;
});
ipcMain.handle('browser:zoom-reset', () => {
  const wc = activeContents();
  if (wc) wc.setZoomFactor(1);
  publishTabs();
  return 1;
});
ipcMain.on('browser:set-bounds', (_e, rect) => {
  if (!rect || !Number.isFinite(rect.x) || !Number.isFinite(rect.y) || !Number.isFinite(rect.width) || !Number.isFinite(rect.height)) return;
  const bounds = { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.max(1, Math.round(rect.width)), height: Math.max(1, Math.round(rect.height)) };
  for (const tab of tabs.values()) tab.view.setBounds(bounds);
});
ipcMain.handle('browser:permission-response', (_e, requestId, allow) => {
  const callback = pendingPermissions.get(String(requestId));
  if (!callback) return false;
  pendingPermissions.delete(String(requestId));
  callback(Boolean(allow));
  return true;
});
