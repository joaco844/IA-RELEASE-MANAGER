import * as React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  GitBranch,
  Rocket,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useDeleteRepository, useRepository } from "@/hooks/use-repositories";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge, RiskBadge } from "@/components/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast";
import { formatDate, formatRelative } from "@/lib/utils";

export function RepositoryDetailPage() {
  const params = useParams<{ id: string }>();
  const repositoryId = Number(params.id);
  const navigate = useNavigate();

  const repositoryQuery = useRepository(repositoryId);
  const deleteMutation = useDeleteRepository();
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  const repository = repositoryQuery.data;

  const handleDelete = () => {
    deleteMutation.mutate(repositoryId, {
      onSuccess: () => {
        toast.success("Repository disconnected");
        navigate("/repositories");
      },
      onError: (error) => {
        toast.error("Could not disconnect repository", {
          description: error instanceof Error ? error.message : undefined,
        });
      },
    });
  };

  if (repositoryQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!repository) {
    return (
      <EmptyState
        icon={GitBranch}
        title="Repository not found"
        description="It may have been disconnected."
        action={
          <Link to="/repositories" className={buttonVariants({ variant: "outline" })}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to repositories
          </Link>
        }
      />
    );
  }

  const releases = repository.recent_releases ?? [];

  return (
    <div>
      <Link
        to="/repositories"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Repositories
      </Link>

      <PageHeader
        title={repository.name}
        description={repository.description ?? repository.project_path}
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => setConfirmDelete(true)}
              className="text-red-400 hover:text-red-300"
            >
              <Trash2 />
              Disconnect
            </Button>
            <Button onClick={() => navigate(`/repositories/${repositoryId}/releases/new`)}>
              <Sparkles />
              Generate release
            </Button>
          </>
        }
      />

      <Card>
        <CardContent className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Project path
            </p>
            <a
              href={`${repository.gitlab_url.replace(/\/$/, "")}/${repository.project_path}`}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-flex items-center gap-1 font-mono text-sm hover:text-primary hover:underline"
            >
              {repository.project_path}
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Default branch
            </p>
            <p className="mt-1 text-sm">{repository.default_branch ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Last release
            </p>
            <p className="mt-1 text-sm">
              {repository.last_release_at ? formatRelative(repository.last_release_at) : "Never"}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Connected
            </p>
            <p className="mt-1 text-sm">{formatDate(repository.created_at)}</p>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Recent releases</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {releases.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-5">Title</TableHead>
                  <TableHead>Range</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead className="pr-5 text-right">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {releases.map((release) => (
                  <TableRow
                    key={release.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/releases/${release.id}`)}
                  >
                    <TableCell className="pl-5 text-sm font-medium">{release.title}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {release.range_summary}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={release.status} />
                    </TableCell>
                    <TableCell>
                      <RiskBadge risk={release.risk_level} />
                    </TableCell>
                    <TableCell className="pr-5 text-right text-sm text-muted-foreground">
                      {formatRelative(release.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="p-5">
              <EmptyState
                icon={Rocket}
                title="No releases yet"
                description="Generate the first AI-powered release notes for this repository."
                action={
                  <Button
                    size="sm"
                    onClick={() => navigate(`/repositories/${repositoryId}/releases/new`)}
                  >
                    <Sparkles />
                    Generate release
                  </Button>
                }
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect {repository.name}?</DialogTitle>
            <DialogDescription>
              This removes the repository connection and its stored access token. Past releases
              will no longer be associated with it.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} loading={deleteMutation.isPending}>
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
