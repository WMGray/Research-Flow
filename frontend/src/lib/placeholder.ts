type PlaceholderHandler = (action: string) => void;

function defaultPlaceholderHandler(action: string): void {
  if (typeof window === "undefined") {
    return;
  }

  window.alert(buildPlaceholderMessage(action));
}

let placeholderHandler: PlaceholderHandler = defaultPlaceholderHandler;

export function buildPlaceholderMessage(action: string): string {
  return `已点击 ${action}，当前按钮已经绑定交互，后续可以继续接入对应功能。`;
}

export function registerPlaceholderHandler(handler: PlaceholderHandler): () => void {
  placeholderHandler = handler;
  return () => {
    if (placeholderHandler === handler) {
      placeholderHandler = defaultPlaceholderHandler;
    }
  };
}

export function showPlaceholderAction(action: string): void {
  placeholderHandler(action);
}
