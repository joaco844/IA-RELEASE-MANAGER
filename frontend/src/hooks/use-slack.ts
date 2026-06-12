import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type {
  ConnectSlackPayload,
  PublishReleasePayload,
  SlackPublication,
  SlackWorkspace,
} from "@/types";

export function useSlackWorkspace() {
  return useQuery({
    queryKey: ["slack", "workspace"],
    queryFn: async (): Promise<SlackWorkspace | null> => {
      try {
        return await api.get<SlackWorkspace>("/slack/workspace");
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });
}

export function useConnectSlack() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ConnectSlackPayload) =>
      api.post<SlackWorkspace>("/slack/connect", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["slack"] });
    },
  });
}

export function usePublishRelease() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PublishReleasePayload) =>
      api.post<SlackPublication>("/slack/publish", payload),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["releases", "detail", variables.release_id],
      });
      void queryClient.invalidateQueries({ queryKey: ["releases", "list"] });
      void queryClient.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}
