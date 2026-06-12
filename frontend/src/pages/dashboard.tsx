import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Bug,
  Clock,
  GitBranch,
  GitCommitHorizontal,
  MessageSquare,
  Rocket,
  Timer,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useMetrics } from "@/hooks/use-metrics";
import { useReleases } from "@/hooks/use-releases";
import { useRepositories } from "@/hooks/use-repositories";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { formatRelative, formatSeconds, truncate } from "@/lib/utils";

const PIE_COLORS = ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#ec4899"];

const tooltipStyle = {
  backgroundColor: "hsl(240 8% 8%)",
  border: "1px solid hsl(240 5% 18%)",
  borderRadius: "8px",
  fontSize: "12px",
  color: "hsl(240 5% 90%)",
};

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-2 p-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className="mt-1.5 text-2xl font-semibold tabular-nums">{value}</p>
          {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/15">
          <Icon className="h-4 w-4 text-primary" />
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const metricsQuery = useMetrics();
  const releasesQuery = useReleases({ page: 1, page_size: 6 });
  const repositoriesQuery = useRepositories();

  const metrics = metricsQuery.data;
  const releases = releasesQuery.data?.items ?? [];
  const repositories = repositoriesQuery.data ?? [];

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of release activity across your connected repositories."
      />

      {/* Stat cards */}
      {metricsQuery.isLoading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-[104px]" />
          ))}
        </div>
      ) : metrics ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          <StatCard
            icon={Rocket}
            label="Releases"
            value={String(metrics.totals.releases)}
            hint={`${metrics.totals.completed} completed`}
          />
          <StatCard
            icon={GitCommitHorizontal}
            label="Commits analyzed"
            value={metrics.totals.commits_analyzed.toLocaleString()}
          />
          <StatCard
            icon={Bug}
            label="Issues analyzed"
            value={metrics.totals.issues_analyzed.toLocaleString()}
            hint={`${metrics.totals.mrs_analyzed.toLocaleString()} MRs`}
          />
          <StatCard
            icon={MessageSquare}
            label="Slack posts"
            value={String(metrics.totals.slack_publications)}
          />
          <StatCard
            icon={Clock}
            label="Hours saved"
            value={`~${Math.round(metrics.totals.hours_saved)}h`}
            hint={
              metrics.avg_generation_seconds !== null
                ? `avg gen ${formatSeconds(metrics.avg_generation_seconds)}`
                : undefined
            }
          />
        </div>
      ) : (
        <Card>
          <CardContent className="p-5 text-sm text-muted-foreground">
            Metrics are unavailable right now.
          </CardContent>
        </Card>
      )}

      {/* Charts */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Releases per week</CardTitle>
            <CardDescription>Generation volume over time</CardDescription>
          </CardHeader>
          <CardContent className="h-56">
            {metricsQuery.isLoading ? (
              <Skeleton className="h-full" />
            ) : metrics && metrics.releases_by_week.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metrics.releases_by_week}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 5% 15%)" vertical={false} />
                  <XAxis
                    dataKey="week"
                    tick={{ fill: "hsl(240 5% 58%)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fill: "hsl(240 5% 58%)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={28}
                  />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(240 5% 12%)" }} />
                  <Bar dataKey="count" name="Releases" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No data yet
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Change categories</CardTitle>
            <CardDescription>Breakdown across analyzed releases</CardDescription>
          </CardHeader>
          <CardContent className="h-56">
            {metricsQuery.isLoading ? (
              <Skeleton className="h-full" />
            ) : metrics && metrics.categories_breakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={metrics.categories_breakdown}
                    dataKey="count"
                    nameKey="category"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {metrics.categories_breakdown.map((entry, index) => (
                      <Cell key={entry.category} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No data yet
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Recent generation times</CardTitle>
            <CardDescription>Seconds per release</CardDescription>
          </CardHeader>
          <CardContent className="h-56">
            {metricsQuery.isLoading ? (
              <Skeleton className="h-full" />
            ) : metrics && metrics.recent_generation_times.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={metrics.recent_generation_times.map((t) => ({
                    ...t,
                    label: truncate(t.title, 14),
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 5% 15%)" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: "hsl(240 5% 58%)", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "hsl(240 5% 58%)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    width={32}
                  />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(240 5% 12%)" }} />
                  <Bar dataKey="seconds" name="Seconds" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="flex h-full items-center justify-center text-sm text-muted-foreground">
                No data yet
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent releases + repositories */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Recent releases</CardTitle>
            <CardDescription>Latest release note generations</CardDescription>
          </CardHeader>
          <CardContent>
            {releasesQuery.isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-12" />
                ))}
              </div>
            ) : releases.length > 0 ? (
              <ul className="divide-y">
                {releases.map((release) => (
                  <li key={release.id}>
                    <Link
                      to={`/releases/${release.id}`}
                      className="flex items-center justify-between gap-3 rounded-md px-2 py-3 transition-colors hover:bg-secondary/40"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{release.title}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {release.repository_name} · {release.range_summary} ·{" "}
                          {formatRelative(release.created_at)}
                        </p>
                      </div>
                      <StatusBadge status={release.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                icon={Timer}
                title="No releases yet"
                description="Connect a repository and generate your first release notes."
                action={
                  <Link to="/repositories" className={buttonVariants({ size: "sm" })}>
                    Go to repositories
                  </Link>
                }
              />
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Connected repositories</CardTitle>
            <CardDescription>{repositories.length} connected</CardDescription>
          </CardHeader>
          <CardContent>
            {repositoriesQuery.isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-12" />
                ))}
              </div>
            ) : repositories.length > 0 ? (
              <ul className="divide-y">
                {repositories.slice(0, 6).map((repo) => (
                  <li key={repo.id}>
                    <Link
                      to={`/repositories/${repo.id}`}
                      className="flex items-center gap-3 rounded-md px-2 py-3 transition-colors hover:bg-secondary/40"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-secondary">
                        <GitBranch className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{repo.name}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {repo.project_path}
                        </p>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                icon={GitBranch}
                title="No repositories"
                description="Connect your first GitLab repository."
                action={
                  <Link
                    to="/repositories"
                    className={buttonVariants({ size: "sm", variant: "outline" })}
                  >
                    Connect repository
                  </Link>
                }
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
