import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { AppIcon } from "@/components/ui/AppIcon";
import { buildPlaceholderMessage, registerPlaceholderHandler } from "@/lib/placeholder";

type NoticeOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
};

type ConfirmOptions = NoticeOptions & {
  cancelLabel?: string;
};

type DialogController = {
  notify: (options: NoticeOptions) => void;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
};

type NoticeDialogState = Required<NoticeOptions> & {
  kind: "notice";
};

type ConfirmDialogState = Required<ConfirmOptions> & {
  kind: "confirm";
  resolve: (value: boolean) => void;
};

type DialogState = NoticeDialogState | ConfirmDialogState;

const DialogContext = createContext<DialogController | null>(null);

export function DialogProvider(props: { children: ReactNode }) {
  const [dialog, setDialog] = useState<DialogState | null>(null);

  const closeDialog = useCallback(() => {
    setDialog((current) => {
      if (current?.kind === "confirm") {
        current.resolve(false);
      }
      return null;
    });
  }, []);

  const notify = useCallback((options: NoticeOptions) => {
    setDialog({
      kind: "notice",
      title: options.title,
      message: options.message,
      confirmLabel: options.confirmLabel ?? "我知道了",
      danger: options.danger ?? false,
    });
  }, []);

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setDialog({
        kind: "confirm",
        title: options.title,
        message: options.message,
        confirmLabel: options.confirmLabel ?? "确认删除",
        cancelLabel: options.cancelLabel ?? "取消",
        danger: options.danger ?? false,
        resolve,
      });
    });
  }, []);

  useEffect(() => {
    return registerPlaceholderHandler((action) => {
      notify({
        title: `已点击 ${action}`,
        message: buildPlaceholderMessage(action),
      });
    });
  }, [notify]);

  useEffect(() => {
    if (!dialog) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeDialog();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closeDialog, dialog]);

  const value = useMemo<DialogController>(
    () => ({
      notify,
      confirm,
    }),
    [confirm, notify],
  );

  return (
    <DialogContext.Provider value={value}>
      {props.children}
      {dialog ? (
        <div aria-modal="true" className="dialog-overlay" role="dialog" onClick={closeDialog}>
          <div className={`dialog-panel${dialog.danger ? " danger" : ""}`} onClick={(event) => event.stopPropagation()}>
            <button aria-label="关闭弹窗" className="dialog-close" type="button" onClick={closeDialog}>
              <AppIcon name="close" size={18} />
            </button>
            <div className="dialog-kicker">{dialog.kind === "confirm" ? "请确认操作" : "功能提示"}</div>
            <h2>{dialog.title}</h2>
            <p>{dialog.message}</p>
            <div className="dialog-actions">
              {dialog.kind === "confirm" ? (
                <button className="dialog-secondary-button" type="button" onClick={closeDialog}>
                  {dialog.cancelLabel}
                </button>
              ) : null}
              <button
                className={dialog.danger ? "dialog-danger-button" : "dialog-primary-button"}
                type="button"
                onClick={() => {
                  if (dialog.kind === "confirm") {
                    dialog.resolve(true);
                  }
                  setDialog(null);
                }}
              >
                {dialog.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </DialogContext.Provider>
  );
}

export function useDialog(): DialogController {
  const context = useContext(DialogContext);
  if (!context) {
    throw new Error("useDialog must be used within DialogProvider");
  }
  return context;
}
