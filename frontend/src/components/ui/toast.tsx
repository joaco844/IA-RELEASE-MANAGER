import * as React from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastVariant = "default" | "success" | "error";

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

type Listener = (toasts: ToastItem[]) => void;

let toastId = 0;
let toasts: ToastItem[] = [];
const listeners = new Set<Listener>();

function emit() {
  for (const listener of listeners) {
    listener([...toasts]);
  }
}

function removeToast(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

function addToast(title: string, variant: ToastVariant, description?: string) {
  const id = ++toastId;
  toasts = [...toasts, { id, title, description, variant }];
  emit();
  window.setTimeout(() => removeToast(id), 5000);
}

interface ToastOptions {
  description?: string;
}

export const toast = Object.assign(
  (title: string, options?: ToastOptions) => addToast(title, "default", options?.description),
  {
    success: (title: string, options?: ToastOptions) =>
      addToast(title, "success", options?.description),
    error: (title: string, options?: ToastOptions) =>
      addToast(title, "error", options?.description),
  },
);

const icons: Record<ToastVariant, React.ReactNode> = {
  default: <Info className="h-4 w-4 text-primary" />,
  success: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  error: <XCircle className="h-4 w-4 text-red-400" />,
};

export function Toaster() {
  const [items, setItems] = React.useState<ToastItem[]>([]);

  React.useEffect(() => {
    const listener: Listener = (next) => setItems(next);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {items.map((item) => (
        <div
          key={item.id}
          className={cn(
            "pointer-events-auto flex items-start gap-3 rounded-lg border bg-popover p-4 shadow-lg animate-toast-in",
            item.variant === "error" && "border-red-500/40",
            item.variant === "success" && "border-emerald-500/40",
          )}
        >
          <div className="mt-0.5 shrink-0">{icons[item.variant]}</div>
          <div className="flex-1 space-y-0.5">
            <p className="text-sm font-medium leading-tight">{item.title}</p>
            {item.description && (
              <p className="text-xs text-muted-foreground">{item.description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => removeToast(item.id)}
            className="shrink-0 rounded-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Dismiss</span>
          </button>
        </div>
      ))}
    </div>
  );
}
