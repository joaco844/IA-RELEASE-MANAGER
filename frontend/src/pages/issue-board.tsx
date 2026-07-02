import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDot,
  ExternalLink,
  GitBranch,
  MessageSquare,
  Plus,
  X,
} from "lucide-react";
import { useRepositories } from "@/hooks/use-repositories";
import {
  useAddBoardList,
  useBoard,
  useCreateBoardIssue,
  useMoveBoardIssue,
  useRemoveBoardList,
} from "@/hooks/use-board";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button, buttonVariants } from "@/components/ui/button";
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
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toast";
import { cn, formatRelative } from "@/lib/utils";
import type { BoardColumn, BoardColumnRef, BoardIssue, BoardLabel } from "@/types";

const DRAG_MIME = "application/x-board-issue";

interface DragPayload {
  iid: number;
  from: BoardColumnRef;
  fromKey: string;
}

function columnRef(column: BoardColumn): BoardColumnRef {
  return { type: column.type, label: column.type === "label" ? column.title : null };
}

function LabelChip({ label, name }: { label: BoardLabel | undefined; name: string }) {
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium leading-4"
      style={
        label
          ? { backgroundColor: label.color, color: label.text_color }
          : { backgroundColor: "#6699cc", color: "#ffffff" }
      }
      title={label?.description ?? undefined}
    >
      {name}
    </span>
  );
}

function IssueCard({
  issue,
  column,
  labelsByName,
}: {
  issue: BoardIssue;
  column: BoardColumn;
  labelsByName: Map<string, BoardLabel>;
}) {
  const [dragging, setDragging] = React.useState(false);

  const handleDragStart = (event: React.DragEvent) => {
    const payload: DragPayload = { iid: issue.iid, from: columnRef(column), fromKey: column.key };
    event.dataTransfer.setData(DRAG_MIME, JSON.stringify(payload));
    event.dataTransfer.effectAllowed = "move";
    setDragging(true);
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onDragEnd={() => setDragging(false)}
      className={cn(
        "cursor-grab rounded-md border bg-background p-3 shadow-sm transition-colors hover:border-primary/40 active:cursor-grabbing",
        dragging && "opacity-40",
      )}
    >
      {issue.web_url ? (
        <a
          href={issue.web_url}
          target="_blank"
          rel="noreferrer"
          className="group inline-flex items-start gap-1 text-sm font-medium leading-snug hover:text-primary"
        >
          {issue.title}
          <ExternalLink className="mt-0.5 h-3 w-3 shrink-0 opacity-0 transition-opacity group-hover:opacity-100" />
        </a>
      ) : (
        <p className="text-sm font-medium leading-snug">{issue.title}</p>
      )}

      {issue.labels.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {issue.labels.map((name) => (
            <LabelChip key={name} label={labelsByName.get(name)} name={name} />
          ))}
        </div>
      )}

      <div className="mt-2.5 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          #{issue.iid}
          {issue.author_name && <> · {issue.author_name}</>}
          {issue.created_at && <> · {formatRelative(issue.created_at)}</>}
        </span>
        {issue.user_notes_count > 0 && (
          <span className="inline-flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            {issue.user_notes_count}
          </span>
        )}
      </div>
    </div>
  );
}

function BoardColumnView({
  column,
  labelsByName,
  onRemove,
  removing,
  onDropIssue,
  onNewIssue,
}: {
  column: BoardColumn;
  labelsByName: Map<string, BoardLabel>;
  onRemove?: (listId: number) => void;
  removing: boolean;
  onDropIssue: (payload: DragPayload, target: BoardColumn) => void;
  onNewIssue?: (column: BoardColumn) => void;
}) {
  const dragDepth = React.useRef(0);
  const [isOver, setIsOver] = React.useState(false);

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    dragDepth.current = 0;
    setIsOver(false);
    const raw = event.dataTransfer.getData(DRAG_MIME);
    if (!raw) return;
    try {
      onDropIssue(JSON.parse(raw) as DragPayload, column);
    } catch {
      // Malformed drag payload; ignore.
    }
  };

  return (
    <div
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes(DRAG_MIME)) event.preventDefault();
      }}
      onDragEnter={(event) => {
        if (!event.dataTransfer.types.includes(DRAG_MIME)) return;
        dragDepth.current += 1;
        setIsOver(true);
      }}
      onDragLeave={() => {
        dragDepth.current = Math.max(0, dragDepth.current - 1);
        if (dragDepth.current === 0) setIsOver(false);
      }}
      onDrop={handleDrop}
      className={cn(
        "flex max-h-[calc(100vh-15rem)] w-80 shrink-0 flex-col rounded-lg border bg-card transition-colors",
        isOver && "border-primary/60 bg-primary/5",
      )}
    >
      <div className="flex items-center gap-2 border-b px-3 py-2.5">
        {column.type === "open" && <CircleDot className="h-3.5 w-3.5 text-emerald-400" />}
        {column.type === "closed" && <CheckCircle2 className="h-3.5 w-3.5 text-violet-400" />}
        {column.type === "label" && (
          <span
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: column.label?.color ?? "#6699cc" }}
          />
        )}
        <p className="text-sm font-medium">{column.title}</p>
        <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
          {column.issues.length}
        </span>
        <span className="ml-auto inline-flex items-center gap-0.5">
          {onNewIssue && column.type !== "closed" && (
            <button
              type="button"
              onClick={() => onNewIssue(column)}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              title={`New issue in ${column.title}`}
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          )}
          {column.type === "label" && column.list_id !== null && onRemove && (
            <button
              type="button"
              onClick={() => onRemove(column.list_id as number)}
              disabled={removing}
              className="rounded p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-50"
              title="Remove list"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-2">
        {column.issues.length > 0 ? (
          column.issues.map((issue) => (
            <IssueCard key={issue.iid} issue={issue} column={column} labelsByName={labelsByName} />
          ))
        ) : (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">
            {isOver ? "Drop here" : "No issues"}
          </p>
        )}
      </div>
    </div>
  );
}

export function IssueBoardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const repositoriesQuery = useRepositories();
  const repositories = repositoriesQuery.data ?? [];

  const repoParam = Number(searchParams.get("repo"));
  const repositoryId =
    Number.isFinite(repoParam) && repoParam > 0 ? repoParam : (repositories[0]?.id ?? 0);

  const boardQuery = useBoard(repositoryId);
  const addListMutation = useAddBoardList(repositoryId);
  const removeListMutation = useRemoveBoardList(repositoryId);
  const createIssueMutation = useCreateBoardIssue(repositoryId);
  const moveIssueMutation = useMoveBoardIssue(repositoryId);

  const [addListOpen, setAddListOpen] = React.useState(false);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [newTitle, setNewTitle] = React.useState("");
  const [newDescription, setNewDescription] = React.useState("");
  const [newLabels, setNewLabels] = React.useState<string[]>([]);

  const board = boardQuery.data;
  const labelsByName = React.useMemo(
    () => new Map((board?.labels ?? []).map((label) => [label.name, label])),
    [board?.labels],
  );
  const usedLabels = new Set(
    (board?.columns ?? []).filter((c) => c.type === "label").map((c) => c.title),
  );
  const availableLabels = (board?.labels ?? []).filter((label) => !usedLabels.has(label.name));

  const openCreateDialog = (presetLabels: string[]) => {
    setNewTitle("");
    setNewDescription("");
    setNewLabels(presetLabels);
    setCreateOpen(true);
  };

  const toggleNewLabel = (name: string) => {
    setNewLabels((current) =>
      current.includes(name) ? current.filter((l) => l !== name) : [...current, name],
    );
  };

  const handleCreateIssue = (event: React.FormEvent) => {
    event.preventDefault();
    const title = newTitle.trim();
    if (!title) return;
    createIssueMutation.mutate(
      { title, description: newDescription.trim() || undefined, labels: newLabels },
      {
        onSuccess: (issue) => {
          setCreateOpen(false);
          toast.success(`Issue #${issue.iid} created`);
        },
        onError: (error) => {
          toast.error("Could not create issue", {
            description: error instanceof Error ? error.message : undefined,
          });
        },
      },
    );
  };

  const handleAddList = (label: string) => {
    addListMutation.mutate(label, {
      onSuccess: () => {
        setAddListOpen(false);
        toast.success(`List "${label}" added`);
      },
      onError: (error) => {
        toast.error("Could not add list", {
          description: error instanceof Error ? error.message : undefined,
        });
      },
    });
  };

  const handleRemoveList = (listId: number) => {
    removeListMutation.mutate(listId, {
      onError: (error) => {
        toast.error("Could not remove list", {
          description: error instanceof Error ? error.message : undefined,
        });
      },
    });
  };

  const handleDropIssue = (payload: DragPayload, target: BoardColumn) => {
    if (payload.fromKey === target.key) return;
    moveIssueMutation.mutate(
      {
        iid: payload.iid,
        from_column: payload.from,
        to_column: columnRef(target),
        toKey: target.key,
      },
      {
        onError: (error) => {
          toast.error(`Could not move issue #${payload.iid}`, {
            description: error instanceof Error ? error.message : undefined,
          });
        },
      },
    );
  };

  if (repositoriesQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <div className="flex gap-4">
          <Skeleton className="h-96 w-80" />
          <Skeleton className="h-96 w-80" />
        </div>
      </div>
    );
  }

  if (repositories.length === 0) {
    return (
      <div>
        <PageHeader title="Issues" description="GitLab issue board for your repositories." />
        <EmptyState
          icon={GitBranch}
          title="No repositories connected"
          description="Connect a GitLab repository to see its issue board."
          action={
            <Link to="/repositories" className={buttonVariants({ variant: "default", size: "sm" })}>
              Connect repository
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Issues"
        description="Live issue board from GitLab. Drag cards between columns to update issues."
        actions={
          <>
            <Button variant="outline" onClick={() => setAddListOpen(true)} disabled={!board}>
              <Plus />
              Add list
            </Button>
            <Button onClick={() => openCreateDialog([])} disabled={!board}>
              <Plus />
              New issue
            </Button>
          </>
        }
      />

      <div className="mb-5 max-w-xs">
        <Label htmlFor="board-repo" className="mb-1.5 block text-xs text-muted-foreground">
          Repository
        </Label>
        <Select
          id="board-repo"
          value={String(repositoryId)}
          onChange={(event) => setSearchParams({ repo: event.target.value })}
        >
          {repositories.map((repo) => (
            <option key={repo.id} value={repo.id}>
              {repo.name}
            </option>
          ))}
        </Select>
      </div>

      {boardQuery.isLoading && (
        <div className="flex gap-4 overflow-x-auto pb-4">
          <Skeleton className="h-96 w-80 shrink-0" />
          <Skeleton className="h-96 w-80 shrink-0" />
          <Skeleton className="h-96 w-80 shrink-0" />
        </div>
      )}

      {boardQuery.isError && (
        <EmptyState
          icon={AlertTriangle}
          title="Could not load the board"
          description={
            boardQuery.error instanceof Error ? boardQuery.error.message : "Unexpected error."
          }
          action={
            <Button size="sm" variant="outline" onClick={() => void boardQuery.refetch()}>
              Retry
            </Button>
          }
        />
      )}

      {board && (
        <div className="flex items-start gap-4 overflow-x-auto pb-4">
          {board.columns.map((column) => (
            <BoardColumnView
              key={column.key}
              column={column}
              labelsByName={labelsByName}
              onRemove={handleRemoveList}
              removing={removeListMutation.isPending}
              onDropIssue={handleDropIssue}
              onNewIssue={(target) =>
                openCreateDialog(target.type === "label" ? [target.title] : [])
              }
            />
          ))}
        </div>
      )}

      <Dialog open={addListOpen} onOpenChange={setAddListOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add a label list</DialogTitle>
            <DialogDescription>
              Open issues with the selected label move from the Open column into their own list,
              just like GitLab boards.
            </DialogDescription>
          </DialogHeader>
          {availableLabels.length > 0 ? (
            <div className="max-h-72 space-y-1 overflow-y-auto">
              {availableLabels.map((label) => (
                <button
                  key={label.name}
                  type="button"
                  onClick={() => handleAddList(label.name)}
                  disabled={addListMutation.isPending}
                  className="flex w-full items-center gap-2.5 rounded-md border px-3 py-2 text-left text-sm transition-colors hover:border-primary/40 hover:bg-secondary disabled:opacity-50"
                >
                  <span
                    className="h-3.5 w-3.5 shrink-0 rounded-full"
                    style={{ backgroundColor: label.color }}
                  />
                  <span className="font-medium">{label.name}</span>
                  {label.description && (
                    <span className="truncate text-xs text-muted-foreground">
                      {label.description}
                    </span>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-sm text-muted-foreground">
              Every project label already has a list, or the project has no labels.
            </p>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <form onSubmit={handleCreateIssue}>
            <DialogHeader>
              <DialogTitle>New issue</DialogTitle>
              <DialogDescription>
                The issue is created directly in the GitLab project.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="issue-title">Title</Label>
                <Input
                  id="issue-title"
                  value={newTitle}
                  onChange={(event) => setNewTitle(event.target.value)}
                  placeholder="Short, descriptive title"
                  className="mt-1.5"
                  autoFocus
                  required
                  maxLength={500}
                />
              </div>
              <div>
                <Label htmlFor="issue-description">Description (optional)</Label>
                <Textarea
                  id="issue-description"
                  value={newDescription}
                  onChange={(event) => setNewDescription(event.target.value)}
                  placeholder="Steps, context, acceptance criteria…"
                  className="mt-1.5 min-h-24"
                />
              </div>
              {(board?.labels.length ?? 0) > 0 && (
                <div>
                  <Label>Labels</Label>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {board?.labels.map((label) => {
                      const selected = newLabels.includes(label.name);
                      return (
                        <button
                          key={label.name}
                          type="button"
                          onClick={() => toggleNewLabel(label.name)}
                          className={cn(
                            "rounded-full border px-2.5 py-1 text-xs font-medium transition-all",
                            selected ? "opacity-100 ring-1 ring-ring" : "opacity-50 hover:opacity-80",
                          )}
                          style={{
                            backgroundColor: label.color,
                            color: label.text_color,
                            borderColor: label.color,
                          }}
                        >
                          {label.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                loading={createIssueMutation.isPending}
                disabled={!newTitle.trim()}
              >
                Create issue
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
