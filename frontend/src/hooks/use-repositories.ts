import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { ConnectRepositoryPayload, Repository, RepositoryDetail } from "@/types";

export function useRepositories() {
  return useQuery({
    queryKey: ["repositories"],
    queryFn: () => api.get<Repository[]>("/repositories"),
  });
}

export function useRepository(id: number) {
  return useQuery({
    queryKey: ["repositories", id],
    queryFn: () => api.get<RepositoryDetail>(`/repositories/${id}`),
    enabled: Number.isFinite(id),
  });
}

export function useConnectRepository() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ConnectRepositoryPayload) =>
      api.post<Repository>("/repositories/connect", payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["repositories"] });
    },
  });
}

export function useDeleteRepository() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.delete(`/repositories/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["repositories"] });
      void queryClient.invalidateQueries({ queryKey: ["releases"] });
    },
  });
}
