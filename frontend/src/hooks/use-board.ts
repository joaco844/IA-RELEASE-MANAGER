import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Board,
  BoardIssue,
  BoardList,
  CreateBoardIssuePayload,
  MoveBoardIssuePayload,
} from "@/types";

export function useBoard(repositoryId: number) {
  return useQuery({
    queryKey: ["board", repositoryId],
    queryFn: () => api.get<Board>(`/repositories/${repositoryId}/board`),
    enabled: Number.isFinite(repositoryId) && repositoryId > 0,
  });
}

export function useAddBoardList(repositoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (label: string) =>
      api.post<BoardList>(`/repositories/${repositoryId}/board/lists`, { label }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["board", repositoryId] });
    },
  });
}

export function useRemoveBoardList(repositoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (listId: number) =>
      api.delete(`/repositories/${repositoryId}/board/lists/${listId}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["board", repositoryId] });
    },
  });
}

export function useCreateBoardIssue(repositoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateBoardIssuePayload) =>
      api.post<BoardIssue>(`/repositories/${repositoryId}/board/issues`, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["board", repositoryId] });
    },
  });
}

function applyMoveLocally(board: Board, move: MoveBoardIssuePayload): Board {
  const issue = board.columns
    .flatMap((column) => column.issues)
    .find((candidate) => candidate.iid === move.iid);
  if (!issue) return board;

  let labels = issue.labels;
  if (move.from_column.type === "label" && move.from_column.label) {
    labels = labels.filter((name) => name !== move.from_column.label);
  }
  if (move.to_column.type === "label" && move.to_column.label && !labels.includes(move.to_column.label)) {
    labels = [...labels, move.to_column.label];
  }
  const updated: BoardIssue = {
    ...issue,
    labels,
    state: move.to_column.type === "closed" ? "closed" : "opened",
  };

  return {
    ...board,
    columns: board.columns.map((column) => {
      const issues = column.issues.filter((candidate) => candidate.iid !== move.iid);
      return column.key === move.toKey ? { ...column, issues: [updated, ...issues] } : { ...column, issues };
    }),
  };
}

export function useMoveBoardIssue(repositoryId: number) {
  const queryClient = useQueryClient();
  const queryKey = ["board", repositoryId];
  return useMutation({
    mutationFn: (move: MoveBoardIssuePayload) =>
      api.post<BoardIssue>(`/repositories/${repositoryId}/board/issues/${move.iid}/move`, {
        from_column: move.from_column,
        to_column: move.to_column,
      }),
    // Optimistic: move the card immediately, roll back if GitLab rejects it.
    onMutate: async (move) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<Board>(queryKey);
      if (previous) {
        queryClient.setQueryData(queryKey, applyMoveLocally(previous, move));
      }
      return { previous };
    },
    onError: (_error, _move, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });
}
