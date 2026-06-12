import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  GenerateReleasePayload,
  PaginatedReleases,
  Release,
  ReleaseDetail,
  ReleaseListParams,
} from "@/types";

const POLL_INTERVAL_MS = 3000;

export function useReleases(params: ReleaseListParams = {}) {
  const search = new URLSearchParams();
  if (params.repository_id !== undefined) search.set("repository_id", String(params.repository_id));
  if (params.status) search.set("status", params.status);
  if (params.page !== undefined) search.set("page", String(params.page));
  if (params.page_size !== undefined) search.set("page_size", String(params.page_size));
  const query = search.toString();

  return useQuery({
    queryKey: ["releases", "list", params],
    queryFn: () => api.get<PaginatedReleases>(`/releases${query ? `?${query}` : ""}`),
  });
}

export function useRelease(id: number) {
  return useQuery({
    queryKey: ["releases", "detail", id],
    queryFn: () => api.get<ReleaseDetail>(`/releases/${id}`),
    enabled: Number.isFinite(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? POLL_INTERVAL_MS : false;
    },
  });
}

export function useGenerateRelease() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateReleasePayload) =>
      api.post<Release>("/releases/generate", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["releases"] });
      void queryClient.invalidateQueries({ queryKey: ["repositories"] });
      void queryClient.invalidateQueries({ queryKey: ["metrics"] });
    },
  });
}
