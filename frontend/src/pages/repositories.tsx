import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { GitBranch, Plus } from "lucide-react";
import { useConnectRepository, useRepositories } from "@/hooks/use-repositories";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

const initialForm = {
  name: "",
  gitlab_url: "https://gitlab.com",
  project_path: "",
  access_token: "",
};

export function RepositoriesPage() {
  const navigate = useNavigate();
  const repositoriesQuery = useRepositories();
  const connectMutation = useConnectRepository();

  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [form, setForm] = React.useState(initialForm);

  const repositories = repositoriesQuery.data ?? [];

  const updateField =
    (field: keyof typeof initialForm) => (event: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: event.target.value }));

  const handleConnect = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    connectMutation.mutate(
      {
        gitlab_url: form.gitlab_url.trim(),
        project_path: form.project_path.trim(),
        access_token: form.access_token.trim(),
        ...(form.name.trim() ? { name: form.name.trim() } : {}),
      },
      {
        onSuccess: (repository) => {
          toast.success("Repository connected", {
            description: `${repository.name} is ready for release generation.`,
          });
          setDialogOpen(false);
          setForm(initialForm);
          navigate(`/repositories/${repository.id}`);
        },
        onError: (error) => {
          toast.error("Could not connect repository", {
            description: error instanceof Error ? error.message : undefined,
          });
        },
      },
    );
  };

  return (
    <div>
      <PageHeader
        title="Repositories"
        description="GitLab projects connected to the release manager."
        actions={
          <Button onClick={() => setDialogOpen(true)}>
            <Plus />
            Connect repository
          </Button>
        }
      />

      {repositoriesQuery.isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      ) : repositories.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-5">Repository</TableHead>
                  <TableHead>Project path</TableHead>
                  <TableHead>Default branch</TableHead>
                  <TableHead>Last release</TableHead>
                  <TableHead className="pr-5 text-right">Connected</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {repositories.map((repo) => (
                  <TableRow
                    key={repo.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/repositories/${repo.id}`)}
                  >
                    <TableCell className="pl-5">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-secondary">
                          <GitBranch className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="min-w-0">
                          <Link
                            to={`/repositories/${repo.id}`}
                            className="block truncate text-sm font-medium hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {repo.name}
                          </Link>
                          {repo.description && (
                            <p className="max-w-[280px] truncate text-xs text-muted-foreground">
                              {repo.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {repo.project_path}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {repo.default_branch ?? "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {repo.last_release_at ? formatRelative(repo.last_release_at) : "Never"}
                    </TableCell>
                    <TableCell className="pr-5 text-right text-sm text-muted-foreground">
                      {formatDate(repo.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          icon={GitBranch}
          title="No repositories connected"
          description="Connect a GitLab project to start generating AI-powered release notes."
          action={
            <Button onClick={() => setDialogOpen(true)}>
              <Plus />
              Connect repository
            </Button>
          }
        />
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <form onSubmit={handleConnect} className="grid gap-4">
            <DialogHeader>
              <DialogTitle>Connect a GitLab repository</DialogTitle>
              <DialogDescription>
                Provide your GitLab instance URL, the project path and a personal access token
                with <span className="font-mono text-xs">read_api</span> scope.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              <Label htmlFor="gitlab_url">GitLab URL</Label>
              <Input
                id="gitlab_url"
                type="url"
                placeholder="https://gitlab.com"
                value={form.gitlab_url}
                onChange={updateField("gitlab_url")}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="project_path">Project path</Label>
              <Input
                id="project_path"
                placeholder="group/project"
                value={form.project_path}
                onChange={updateField("project_path")}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="access_token">Access token</Label>
              <Input
                id="access_token"
                type="password"
                placeholder="glpat-…"
                value={form.access_token}
                onChange={updateField("access_token")}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">
                Display name <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="name"
                placeholder="Defaults to the GitLab project name"
                value={form.name}
                onChange={updateField("name")}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={connectMutation.isPending}>
                Connect
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
