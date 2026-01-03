const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    sendMessage: (message) => ipcRenderer.send('message', message),
    resizeWindow: (dimensions) => ipcRenderer.send('resize-window', dimensions),
    setAlwaysOnTop: (enabled, level) => ipcRenderer.send('set-always-on-top', { enabled, level }),
    quitApp: () => ipcRenderer.send('quit-app'),
    getSystemIdleTime: () => ipcRenderer.invoke('get-system-idle-time'),

});
