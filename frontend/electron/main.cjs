const { app, BrowserWindow, screen, ipcMain } = require('electron');
const path = require('path');
const isDev = !app.isPackaged;

function createWindow() {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    const mainWindow = new BrowserWindow({
        width: 450,
        height: 750,
        x: width - 470,
        y: height - 770, // Anchor to bottom with 20px padding (750 + 20)
        transparent: true,
        frame: false,
        resizable: false, // User cannot resize manually
        alwaysOnTop: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.cjs'),
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    // Handle Resize Request from Renderer
    ipcMain.on('resize-window', (event, { width, height }) => {
        const bounds = mainWindow.getBounds();
        const bottomY = bounds.y + bounds.height;
        const newY = bottomY - height;

        // animation is buggy on transparent windows sometimes, let's try direct set
        mainWindow.setBounds({ x: bounds.x, y: newY, width: width, height: height });
    });

    // Handle Always-On-Top Toggle
    ipcMain.on('set-always-on-top', (event, { enabled, level }) => {
        // level can be 'normal', 'floating', 'torn-off-menu', 'modal-panel', 'main-menu', 'status', 'pop-up-menu', 'screen-saver'
        // 'screen-saver' is highest and covers fullscreen apps.
        mainWindow.setAlwaysOnTop(enabled, level || 'normal');
    });

    ipcMain.on('quit-app', () => {
        app.quit();
    });

    ipcMain.handle('get-system-idle-time', () => {
        const { powerMonitor } = require('electron');
        return powerMonitor.getSystemIdleTime();
    });

    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
        // mainWindow.webContents.openDevTools({ mode: 'detach' });
    } else {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }
}

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Cleanup backend when app quits
// Cleanup backend when app quits
app.on('before-quit', () => {
    console.log("Stopping processes...");
    try {
        const { execSync } = require('child_process');
        // Kill Python backend
        execSync('taskkill /F /IM python.exe 2>nul', { stdio: 'ignore' });
        // Kill Ollama side-processes if any (optional)
        // execSync('taskkill /F /IM ollama.exe 2>nul', { stdio: 'ignore' });

        // Note: We don't kill node.exe because it might be running other things.
        // In dev mode, the terminal window will remain open - this is expected.
    } catch (e) {
        // Ignore
    }
});
