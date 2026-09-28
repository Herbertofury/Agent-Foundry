const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('companion', {
  loadCatalog: () => ipcRenderer.invoke('catalog:load'),
  browser: {
    open: (url, label) => ipcRenderer.invoke('browser:open', url, label),
    newTab: () => ipcRenderer.invoke('browser:new-tab'),
    activate: (id) => ipcRenderer.invoke('browser:activate', id),
    close: (id) => ipcRenderer.invoke('browser:close', id),
    reopenClosed: () => ipcRenderer.invoke('browser:reopen-closed'),
    navigate: (url) => ipcRenderer.invoke('browser:navigate', url),
    back: () => ipcRenderer.invoke('browser:back'),
    forward: () => ipcRenderer.invoke('browser:forward'),
    reloadOrStop: () => ipcRenderer.invoke('browser:reload-or-stop'),
    openExternal: (url) => ipcRenderer.invoke('browser:external', url),
    copyUrl: (url) => ipcRenderer.invoke('browser:copy-url', url),
    find: (text) => ipcRenderer.invoke('browser:find', text),
    stopFind: () => ipcRenderer.invoke('browser:stop-find'),
    zoom: (delta) => ipcRenderer.invoke('browser:zoom', delta),
    zoomReset: () => ipcRenderer.invoke('browser:zoom-reset'),
    setBounds: (rect) => ipcRenderer.send('browser:set-bounds', rect),
    permissionResponse: (requestId, allow) => ipcRenderer.invoke('browser:permission-response', requestId, allow),
    onTabs: (fn) => ipcRenderer.on('browser:tabs', (_e, value) => fn(value)),
    onFavicon: (fn) => ipcRenderer.on('browser:favicon', (_e, value) => fn(value)),
    onError: (fn) => ipcRenderer.on('browser:error', (_e, value) => fn(value)),
    onDownload: (fn) => ipcRenderer.on('browser:download', (_e, value) => fn(value)),
    onPermissionRequest: (fn) => ipcRenderer.on('browser:permission-request', (_e, value) => fn(value)),
    onBoundsRequest: (fn) => ipcRenderer.on('browser:request-bounds', () => fn())
  }
});
