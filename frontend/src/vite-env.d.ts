/// <reference types="vite/client" />

type ResearchFlowBridge = {
  isElectron?: boolean;
  platform: string;
  openPath?: (targetPath: string) => Promise<{ ok: boolean; error?: string }>;
};

interface Window {
  researchFlow?: ResearchFlowBridge;
}
