import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { MetricsResponse } from "@/types";

export function useMetrics() {
  return useQuery({
    queryKey: ["metrics"],
    queryFn: () => api.get<MetricsResponse>("/metrics"),
  });
}
