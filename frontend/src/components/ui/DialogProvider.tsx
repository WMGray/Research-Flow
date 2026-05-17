import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { buildPlaceholderMessage, registerPlaceholderHandler } from "@/lib/placeholder";
import { useEffect } from "react";

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
      confirmLabel: options.confirmLabel ?? "知道了",
      danger: options.danger ?? false,
    });
  }, []);

  const confirm = useCallback((options: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setDialog({
        kind: "confirm",
        title: options.title,
        message: options.message,
        confirmLabel: options.confirmLabel ?? "确认",
        cancelLabel: options.cancelLabel ?? "取消",
        danger: options.danger ?? false,
        resolve,
      });
    });
  }, []);

  useEffect(() => {
    return registerPlaceholderHandler((action) => {
      notify({
        title: `已点击「${action}」`,
        message: buildPlaceholderMessage(action),
      });
    });
  }, [notify]);

  const value = useMemo<DialogController>(() => ({ confirm, notify }), [confirm, notify]);

  return (
    <DialogContext.Provider value={value}>
      {props.children}
      <Dialog open={Boolean(dialog)} onOpenChange={(open) => {
        if (!open) {
          closeDialog();
        }
      }}>
        {dialog ? (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{dialog.title}</DialogTitle>
              <DialogDescription>{dialog.message}</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              {dialog.kind === "confirm" ? (
                <Button variant="outline" onClick={closeDialog}>
                  {dialog.cancelLabel}
                </Button>
              ) : null}
              <Button
                variant={dialog.danger ? "destructive" : "default"}
                onClick={() => {
                  if (dialog.kind === "confirm") {
                    dialog.resolve(true);
                  }
                  setDialog(null);
                }}
              >
                {dialog.confirmLabel}
              </Button>
            </DialogFooter>
          </DialogContent>
        ) : null}
      </Dialog>
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
