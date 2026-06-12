import * as React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CalendarDays, GitCompareArrows, History, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useRepository } from "@/hooks/use-repositories";
import { useGenerateRelease } from "@/hooks/use-releases";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import type { AiProvider, GenerateReleasePayload, ReleaseRangeType } from "@/types";

const rangeOptions: {
  value: ReleaseRangeType;
  label: string;
  description: string;
  icon: LucideIcon;
}[] = [
  {
    value: "tag_range",
    label: "Tag range",
    description: "Compare two git tags, e.g. v1.2.0 → v1.3.0",
    icon: GitCompareArrows,
  },
  {
    value: "last_days",
    label: "Last N days",
    description: "Everything merged in the last N days",
    icon: History,
  },
  {
    value: "since_date",
    label: "Since date",
    description: "Everything since a specific date",
    icon: CalendarDays,
  },
];

export function ReleaseBuilderPage() {
  const params = useParams<{ id: string }>();
  const repositoryId = Number(params.id);
  const navigate = useNavigate();

  const repositoryQuery = useRepository(repositoryId);
  const generateMutation = useGenerateRelease();

  const [title, setTitle] = React.useState("");
  const [rangeType, setRangeType] = React.useState<ReleaseRangeType>("tag_range");
  const [fromTag, setFromTag] = React.useState("");
  const [toTag, setToTag] = React.useState("");
  const [days, setDays] = React.useState("14");
  const [since, setSince] = React.useState("");
  const [provider, setProvider] = React.useState<AiProvider>("openai");
  const [temperature, setTemperature] = React.useState(0.2);

  const repository = repositoryQuery.data;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const payload: GenerateReleasePayload = {
      repository_id: repositoryId,
      range: { type: rangeType },
      ai: { provider, temperature },
    };

    if (title.trim()) payload.title = title.trim();

    if (rangeType === "tag_range") {
      if (!fromTag.trim() || !toTag.trim()) {
        toast.error("Both tags are required for a tag range.");
        return;
      }
      payload.range.from_tag = fromTag.trim();
      payload.range.to_tag = toTag.trim();
    } else if (rangeType === "last_days") {
      const parsed = Number(days);
      if (!Number.isInteger(parsed) || parsed < 1) {
        toast.error("Enter a valid number of days.");
        return;
      }
      payload.range.days = parsed;
    } else {
      if (!since) {
        toast.error("Pick a starting date.");
        return;
      }
      payload.range.since = since;
    }

    generateMutation.mutate(payload, {
      onSuccess: (release) => {
        toast.success("Release generation started", {
          description: "The AI pipeline is analyzing your changes.",
        });
        navigate(`/releases/${release.id}`);
      },
      onError: (error) => {
        toast.error("Could not start generation", {
          description: error instanceof Error ? error.message : undefined,
        });
      },
    });
  };

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        to={`/repositories/${repositoryId}`}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        {repository?.name ?? "Repository"}
      </Link>

      <PageHeader
        title="Generate release notes"
        description={
          repository
            ? `AI-generated release notes for ${repository.project_path}.`
            : "Configure the change range and AI settings."
        }
      />

      {repositoryQuery.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Release</CardTitle>
              <CardDescription>Optionally name this release.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="title">
                  Title <span className="text-muted-foreground">(optional)</span>
                </Label>
                <Input
                  id="title"
                  placeholder="e.g. v2.4.0 — Payments revamp"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Change range</CardTitle>
              <CardDescription>Which changes should be included?</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2 sm:grid-cols-3">
                {rangeOptions.map((option) => (
                  <label
                    key={option.value}
                    className={cn(
                      "flex cursor-pointer flex-col gap-1.5 rounded-lg border p-3 transition-colors",
                      rangeType === option.value
                        ? "border-primary bg-primary/10"
                        : "hover:border-muted-foreground/40",
                    )}
                  >
                    <input
                      type="radio"
                      name="range_type"
                      value={option.value}
                      checked={rangeType === option.value}
                      onChange={() => setRangeType(option.value)}
                      className="sr-only"
                    />
                    <option.icon
                      className={cn(
                        "h-4 w-4",
                        rangeType === option.value ? "text-primary" : "text-muted-foreground",
                      )}
                    />
                    <span className="text-sm font-medium">{option.label}</span>
                    <span className="text-xs leading-snug text-muted-foreground">
                      {option.description}
                    </span>
                  </label>
                ))}
              </div>

              {rangeType === "tag_range" && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="from_tag">From tag</Label>
                    <Input
                      id="from_tag"
                      placeholder="v1.2.0"
                      value={fromTag}
                      onChange={(e) => setFromTag(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="to_tag">To tag</Label>
                    <Input
                      id="to_tag"
                      placeholder="v1.3.0"
                      value={toTag}
                      onChange={(e) => setToTag(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {rangeType === "last_days" && (
                <div className="space-y-2">
                  <Label htmlFor="days">Number of days</Label>
                  <Input
                    id="days"
                    type="number"
                    min={1}
                    max={365}
                    value={days}
                    onChange={(e) => setDays(e.target.value)}
                    className="max-w-[160px]"
                  />
                </div>
              )}

              {rangeType === "since_date" && (
                <div className="space-y-2">
                  <Label htmlFor="since">Since date</Label>
                  <Input
                    id="since"
                    type="date"
                    value={since}
                    onChange={(e) => setSince(e.target.value)}
                    className="max-w-[200px]"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">AI configuration</CardTitle>
              <CardDescription>Model provider and creativity.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="provider">Provider</Label>
                <Select
                  id="provider"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as AiProvider)}
                >
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Gemini</option>
                </Select>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="temperature">Temperature</Label>
                  <span className="font-mono text-xs text-muted-foreground">
                    {temperature.toFixed(1)}
                  </span>
                </div>
                <input
                  id="temperature"
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="h-9 w-full cursor-pointer accent-[hsl(258,90%,66%)]"
                />
                <p className="text-xs text-muted-foreground">
                  Lower is more factual, higher is more creative.
                </p>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate(`/repositories/${repositoryId}`)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={generateMutation.isPending}>
              <Sparkles />
              Generate release notes
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
