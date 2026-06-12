import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-destructive text-destructive-foreground",
        outline: "text-foreground",
        gray: "border-zinc-700/60 bg-zinc-800/60 text-zinc-300",
        blue: "border-blue-500/30 bg-blue-500/15 text-blue-400",
        green: "border-emerald-500/30 bg-emerald-500/15 text-emerald-400",
        red: "border-red-500/30 bg-red-500/15 text-red-400",
        violet: "border-violet-500/30 bg-violet-500/15 text-violet-400",
        amber: "border-amber-500/30 bg-amber-500/15 text-amber-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
