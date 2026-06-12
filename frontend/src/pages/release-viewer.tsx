import * as React from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  Bug,
  CheckCircle2,
  ExternalLink,
  FileText,
  GitCommitHorizontal,
  GitPullRequest,
  Loader2,
  MessageSquare,
  Rocket,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useRelease } from "@/hooks/use-releases";
import { usePublishRelease, useSlackWorkspace } from "@/hooks/use-slack";
import { CollapsibleSection } from "@/components/collapsible-section";
import { EmptyState } from "@/components/empty-state";
import { Markdown } from "@/components/markdown";
import { PageHeader } from "@/components/page-header";
import { RiskBadge, StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";
import { cn, formatDateTime, formatRelative, formatSeconds } from "@/lib/utils";

function NoteFallback({ label }: { label: string }) {
  return (
    <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
      {label} notes are not available for this release.
    </p>
  );
}

export function ReleaseViewerPage() {
  const params = useParams<{ id: string }>();
  const releaseId = Number(params.id);

  const releaseQuery = useRelease(releaseId);
  const workspaceQuery = useSlackWorkspace();
  const publishMutation = usePublishRelease();

  const release = releaseQuery.data;
  const workspace = workspaceQuery.data;

  const [channel, setChannel] = React.useState("");
  const [channelTouched, setChannelTouched] = React.useState(false);

  React.useEffect(() => {
    if (!channelTouched && workspace?.default_channel) {
      setChannel(workspace.default_channel);
    }
  }, [workspace, channelTouched]);

  const handlePublish = () => {
    publishMutation.mutate(
      { release_id: releaseId, ...(channel.trim() ? { channel: channel.trim() } : {}) },
      {
        onSuccess: (publication) => {
          toast.success("Published to Slack", {
            description: `Posted in ${publication.channel}.`,
          });
        },
        onError: (error) => {
          toast.error("Publish failed", {
            description: error instanceof Error ? error.message : undefined,
          });
        },
      },
    );
  };

  if (releaseQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-24" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  if (!release) {
    return (
      <EmptyState
        icon={Rocket}
        title="Release not found"
        description="It may have been removed, or the link is wrong."
        action={
          <Link to="/" className={buttonVariants({ variant: "outline" })}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to dashboard
          </Link>
        }
      />
    );
  }

  const isGenerating = release.status === "pending" || release.status === "running";
  const isFailed = release.status === "failed";
  const canPublish = release.status === "completed" || release.status === "published";

  return (
    <div>
      <Link
        to={`/repositories/${release.repository_id}`}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        {release.repository_name}
      </Link>

      <PageHeader
        title={release.title}
        description={`${release.range_summary} · created ${formatRelative(release.created_at)}`}
        actions={
          <div className="flex items-center gap-2">
            <RiskBadge risk={release.risk_level} />
            <StatusBadge status={release.status} />
          </div>
        }
      />

      {/* Live generation banner */}
      {isGenerating && (
        <Card className="mb-6 border-blue-500/30 bg-blue-500/5">
          <CardContent className="flex items-center gap-4 p-5">
            <div className="relative flex h-10 w-10 items-center justify-center">
              <span className="absolute inline-flex h-9 w-9 animate-ping rounded-full bg-blue-500/30" />
              <Loader2 className="relative h-5 w-5 animate-spin text-blue-400" />
            </div>
            <div>
              <p className="text-sm font-medium">
                {release.status === "pending"
                  ? "Queued for generation…"
                  : "The AI pipeline is writing your release notes…"}
              </p>
              <p className="text-xs text-muted-foreground">
                Fetching commits, issues and merge requests, categorizing changes and drafting
                notes. This page refreshes automatically every few seconds.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Failure banner */}
      {isFailed && (
        <Card className="mb-6 border-red-500/40 bg-red-500/5">
          <CardContent className="flex items-start gap-4 p-5">
            <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
            <div>
              <p className="text-sm font-medium text-red-300">Generation failed</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {release.error_message ?? "An unexpected error occurred during generation."}
              </p>
              <Link
                to={`/repositories/${release.repository_id}/releases/new`}
                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "mt-3")}
              >
                Try again
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metrics strip */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Generation time", value: formatSeconds(release.metrics.generation_seconds) },
          { label: "Commits", value: String(release.metrics.commits_analyzed) },
          { label: "Issues", value: String(release.metrics.issues_analyzed) },
          { label: "Merge requests", value: String(release.metrics.mrs_analyzed) },
        ].map((item) => (
          <div key={item.label} className="rounded-lg border bg-card px-4 py-3">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">{item.label}</p>
            <p className="mt-1 text-lg font-semibold tabular-nums">{item.value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Notes */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="pb-0">
              <CardTitle className="text-sm">Release notes</CardTitle>
              <CardDescription>
                Audience-specific versions generated by the AI pipeline.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              <Tabs defaultValue="executive">
                <TabsList>
                  <TabsTrigger value="executive">Executive</TabsTrigger>
                  <TabsTrigger value="technical">Technical</TabsTrigger>
                  <TabsTrigger value="markdown">
                    <FileText className="h-3.5 w-3.5" />
                    Markdown
                  </TabsTrigger>
                  <TabsTrigger value="slack">
                    <MessageSquare className="h-3.5 w-3.5" />
                    Slack
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="executive">
                  {release.notes.executive ? (
                    <Markdown content={release.notes.executive} />
                  ) : (
                    <NoteFallback label="Executive" />
                  )}
                </TabsContent>
                <TabsContent value="technical">
                  {release.notes.technical ? (
                    <Markdown content={release.notes.technical} />
                  ) : (
                    <NoteFallback label="Technical" />
                  )}
                </TabsContent>
                <TabsContent value="markdown">
                  {release.notes.markdown ? (
                    <Markdown content={release.notes.markdown} />
                  ) : (
                    <NoteFallback label="Markdown" />
                  )}
                </TabsContent>
                <TabsContent value="slack">
                  {release.notes.slack ? (
                    <div className="rounded-lg border bg-secondary/30 p-4">
                      <div className="mb-3 flex items-center gap-2 border-b pb-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/20">
                          <Rocket className="h-4 w-4 text-primary" />
                        </div>
                        <div className="leading-tight">
                          <p className="text-sm font-semibold">AI Release Manager</p>
                          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                            App · preview
                          </p>
                        </div>
                      </div>
                      <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">
                        {release.notes.slack}
                      </pre>
                    </div>
                  ) : (
                    <NoteFallback label="Slack" />
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Analysis categories */}
          {release.analysis && release.analysis.categories.length > 0 && (
            <Card className="mt-6">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Change analysis</CardTitle>
                <CardDescription>Categorized impact assessment</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {release.analysis.categories.map((category) => (
                  <div key={category.category}>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      {category.category}
                    </p>
                    <div className="space-y-2">
                      {category.items.map((item, index) => (
                        <div key={index} className="rounded-lg border p-3">
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-medium">{item.summary}</p>
                            <Badge
                              variant={
                                item.risk_level === "high"
                                  ? "red"
                                  : item.risk_level === "medium"
                                    ? "amber"
                                    : "green"
                              }
                            >
                              {item.risk_level}
                            </Badge>
                          </div>
                          <p className="mt-1.5 text-xs text-muted-foreground">
                            <span className="font-medium text-foreground/80">Business:</span>{" "}
                            {item.business_impact}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            <span className="font-medium text-foreground/80">Technical:</span>{" "}
                            {item.technical_impact}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Source data */}
          <div className="mt-6 space-y-3">
            <CollapsibleSection
              icon={GitCommitHorizontal}
              title="Commits"
              count={release.commits.length}
            >
              {release.commits.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead>SHA</TableHead>
                      <TableHead>Title</TableHead>
                      <TableHead>Author</TableHead>
                      <TableHead className="text-right">Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {release.commits.map((commit) => (
                      <TableRow key={commit.sha}>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {commit.sha.slice(0, 8)}
                        </TableCell>
                        <TableCell className="max-w-[320px] truncate text-sm">
                          {commit.title}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {commit.author_name}
                        </TableCell>
                        <TableCell className="text-right text-sm text-muted-foreground">
                          {formatDateTime(commit.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="py-2 text-sm text-muted-foreground">No commits in range.</p>
              )}
            </CollapsibleSection>

            <CollapsibleSection icon={Bug} title="Issues" count={release.issues.length}>
              {release.issues.length > 0 ? (
                <ul className="divide-y">
                  {release.issues.map((issue) => (
                    <li key={issue.iid} className="flex items-center justify-between gap-3 py-2.5">
                      <div className="min-w-0">
                        <a
                          href={issue.web_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-sm font-medium hover:text-primary hover:underline"
                        >
                          #{issue.iid} {issue.title}
                          <ExternalLink className="h-3 w-3 shrink-0" />
                        </a>
                        {issue.labels.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {issue.labels.map((label) => (
                              <Badge key={label} variant="gray" className="text-[10px]">
                                {label}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                      <Badge variant={issue.state === "closed" ? "green" : "blue"}>
                        {issue.state}
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="py-2 text-sm text-muted-foreground">No linked issues.</p>
              )}
            </CollapsibleSection>

            <CollapsibleSection
              icon={GitPullRequest}
              title="Merge requests"
              count={release.merge_requests.length}
            >
              {release.merge_requests.length > 0 ? (
                <ul className="divide-y">
                  {release.merge_requests.map((mr) => (
                    <li key={mr.iid} className="flex items-center justify-between gap-3 py-2.5">
                      <div className="min-w-0">
                        <a
                          href={mr.web_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-sm font-medium hover:text-primary hover:underline"
                        >
                          !{mr.iid} {mr.title}
                          <ExternalLink className="h-3 w-3 shrink-0" />
                        </a>
                        <p className="mt-0.5 text-xs text-muted-foreground">{mr.author_name}</p>
                      </div>
                      <Badge variant={mr.state === "merged" ? "violet" : "blue"}>{mr.state}</Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="py-2 text-sm text-muted-foreground">No merge requests in range.</p>
              )}
            </CollapsibleSection>
          </div>
        </div>

        {/* Sidebar: QA + Slack publish */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                QA report
              </CardTitle>
              <CardDescription>Automated review of the generated notes</CardDescription>
            </CardHeader>
            <CardContent>
              {release.qa_report ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    {release.qa_report.approved ? (
                      <Badge variant="green">
                        <CheckCircle2 className="h-3 w-3" />
                        Approved
                      </Badge>
                    ) : (
                      <Badge variant="amber">
                        <AlertTriangle className="h-3 w-3" />
                        Needs review
                      </Badge>
                    )}
                  </div>
                  <div>
                    <div className="mb-1.5 flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Traceability score</span>
                      <span className="font-mono font-medium">
                        {Math.round(release.qa_report.traceability_score * 100)}%
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-secondary">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          release.qa_report.traceability_score >= 0.8
                            ? "bg-emerald-500"
                            : release.qa_report.traceability_score >= 0.5
                              ? "bg-amber-500"
                              : "bg-red-500",
                        )}
                        style={{
                          width: `${Math.min(100, Math.round(release.qa_report.traceability_score * 100))}%`,
                        }}
                      />
                    </div>
                  </div>
                  {release.qa_report.issues_found.length > 0 ? (
                    <div>
                      <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                        Issues found
                      </p>
                      <ul className="space-y-1.5">
                        {release.qa_report.issues_found.map((issue, index) => (
                          <li key={index} className="flex items-start gap-2 text-xs">
                            <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />
                            <span className="text-muted-foreground">{issue}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">No issues found.</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {isGenerating ? "Available once generation completes." : "No QA report."}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                Publish to Slack
              </CardTitle>
              <CardDescription>
                {workspace
                  ? `Connected to ${workspace.team_name}`
                  : "Connect a workspace in Settings first."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {release.slack_message_url && (
                <div className="rounded-lg border border-violet-500/30 bg-violet-500/10 p-3">
                  <p className="text-xs font-medium text-violet-300">Published</p>
                  <a
                    href={release.slack_message_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-1 break-all text-xs text-violet-300 underline-offset-2 hover:underline"
                  >
                    {release.slack_message_url}
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="channel">Channel</Label>
                <Input
                  id="channel"
                  placeholder="#releases"
                  value={channel}
                  onChange={(e) => {
                    setChannelTouched(true);
                    setChannel(e.target.value);
                  }}
                  disabled={!workspace}
                />
              </div>
              <Button
                className="w-full"
                onClick={handlePublish}
                disabled={!canPublish || !workspace}
                loading={publishMutation.isPending}
              >
                <MessageSquare />
                {release.status === "published" ? "Publish again" : "Publish to Slack"}
              </Button>
              {!canPublish && !isFailed && (
                <p className="text-xs text-muted-foreground">
                  Publishing becomes available once generation completes.
                </p>
              )}
              {!workspace && !workspaceQuery.isLoading && (
                <Link
                  to="/settings"
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }), "w-full")}
                >
                  Connect Slack workspace
                </Link>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-2 p-5 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>{formatDateTime(release.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Completed</span>
                <span>{formatDateTime(release.completed_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Release ID</span>
                <span className="font-mono text-xs">#{release.id}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
