import { contextBridge, ipcRenderer } from "electron";

const platform = typeof process === "undefined" ? "unknown" : process.platform;

contextBridge.exposeInMainWorld("researchFlow", {
  isElectron: true,
  platform,
  openPath: (targetPath: string): Promise<{ ok: boolean; error?: string }> => ipcRenderer.invoke("research-flow:open-path", targetPath),
});
