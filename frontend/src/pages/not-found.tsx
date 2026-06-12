import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={Compass}
        title="Page not found"
        description="The page you are looking for doesn't exist or has been moved."
        action={
          <Link to="/" className={buttonVariants({ variant: "outline" })}>
            Back to dashboard
          </Link>
        }
        className="w-full max-w-md border-none"
      />
    </div>
  );
}
