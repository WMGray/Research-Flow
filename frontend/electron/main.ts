import { app, BrowserWindow, ipcMain, shell } from "electron";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL ?? "http://127.0.0.1:5173";
const isDev = process.argv.includes("--dev");

ipcMain.handle("research-flow:open-path", async (_event, rawPath: unknown): Promise<{ ok: boolean; error?: string }> => {
  if (typeof rawPath !== "string" || !rawPath.trim()) {
    return { ok: false, error: "Missing local path." };
  }

  const targetPath = path.resolve(stripWrappingQuotes(rawPath.trim()));
  try {
    const stats = await fs.stat(targetPath);
    if (stats.isDirectory()) {
      const error = await shell.openPath(targetPath);
      return error ? { ok: false, error } : { ok: true };
    }
    shell.showItemInFolder(targetPath);
    return { ok: true };
  } catch (error) {
    const parentPath = path.dirname(targetPath);
    try {
      const parentStats = await fs.stat(parentPath);
      if (parentStats.isDirectory()) {
        const openError = await shell.openPath(parentPath);
        return openError ? { ok: false, error: openError } : { ok: true };
      }
    } catch {
      // Preserve the original stat error below; the parent fallback is best effort.
    }

    const message = error instanceof Error ? error.message : "Path does not exist.";
    return { ok: false, error: message };
  }
});

async function createWindow(): Promise<void> {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1100,
    minHeight: 720,
    show: false,
    title: "Research-Flow",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  if (isDev) {
    await mainWindow.loadURL(DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
    return;
  }

  await mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
}

app.whenReady().then(async () => {
  await createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      void createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

function stripWrappingQuotes(value: string): string {
  if ((value.startsWith("\"") && value.endsWith("\"")) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }
  return value;
}
