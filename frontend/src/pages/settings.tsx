import * as React from "react";
import { CheckCircle2, MessageSquare, Slack } from "lucide-react";
import { useConnectSlack, useSlackWorkspace } from "@/hooks/use-slack";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
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
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { formatDateTime } from "@/lib/utils";

export function SettingsPage() {
  const workspaceQuery = useSlackWorkspace();
  const connectMutation = useConnectSlack();

  const [botToken, setBotToken] = React.useState("");
  const [defaultChannel, setDefaultChannel] = React.useState("#releases");

  const workspace = workspaceQuery.data;

  const handleConnect = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    connectMutation.mutate(
      { bot_token: botToken.trim(), default_channel: defaultChannel.trim() },
      {
        onSuccess: (result) => {
          toast.success("Slack connected", {
            description: `Workspace ${result.team_name} is ready.`,
          });
          setBotToken("");
        },
        onError: (error) => {
          toast.error("Could not connect Slack", {
            description: error instanceof Error ? error.message : undefined,
          });
        },
      },
    );
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader
        title="Settings"
        description="Workspace integrations for publishing release notes."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Slack className="h-4 w-4 text-muted-foreground" />
            Slack workspace
          </CardTitle>
          <CardDescription>
            Releases are published as rich messages using a Slack bot token.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {workspaceQuery.isLoading ? (
            <Skeleton className="h-20" />
          ) : workspace ? (
            <div className="flex items-start justify-between gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
                <div>
                  <p className="text-sm font-medium">{workspace.team_name}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Default channel{" "}
                    <span className="font-mono text-foreground">{workspace.default_channel}</span>
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Connected {formatDateTime(workspace.connected_at)}
                  </p>
                </div>
              </div>
              <Badge variant="green">Connected</Badge>
            </div>
          ) : (
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-4">
              <MessageSquare className="h-5 w-5 shrink-0 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Not connected</p>
                <p className="text-xs text-muted-foreground">
                  Add a bot token below to enable publishing.
                </p>
              </div>
            </div>
          )}

          <form onSubmit={handleConnect} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="bot_token">Bot token</Label>
              <Input
                id="bot_token"
                type="password"
                placeholder="xoxb-…"
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                Create a Slack app with the{" "}
                <span className="font-mono text-foreground">chat:write</span> scope and install it
                to your workspace.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="default_channel">Default channel</Label>
              <Input
                id="default_channel"
                placeholder="#releases"
                value={defaultChannel}
                onChange={(e) => setDefaultChannel(e.target.value)}
                required
              />
            </div>
            <div className="flex justify-end">
              <Button type="submit" loading={connectMutation.isPending}>
                {workspace ? "Update connection" : "Connect Slack"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
