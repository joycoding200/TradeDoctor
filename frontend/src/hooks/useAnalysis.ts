import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getStats, getInsight, getWhatIf, runAnalysis, linkFilesToAnalysis } from "../api/analysis";
import { generateReport, getReport, checkAnalysisReport } from "../api/report";

export function useStats(id: string | undefined) {
  return useQuery({
    queryKey: ["stats", id],
    queryFn: () => getStats(id!),
    enabled: !!id,
  });
}

export function useInsight(id: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["insight", id],
    queryFn: () => getInsight(id!),
    enabled: !!id && enabled,
  });
}

export function useWhatIf(id: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ["whatif", id],
    queryFn: () => getWhatIf(id!),
    enabled: !!id && enabled,
  });
}

export function useRunAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { ds?: string; de?: string }) => runAnalysis(params.ds || "", params.de || ""),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["stats", data.id] });
    },
  });
}

export function useGenerateReport() {
  return useMutation({
    mutationFn: (analysisId: string) => generateReport(analysisId),
  });
}

export function useReport(reportId: string | undefined) {
  return useQuery({
    queryKey: ["report", reportId],
    queryFn: () => getReport(reportId!),
    enabled: !!reportId,
  });
}

export function useCheckReport(analysisId: string | undefined) {
  return useQuery({
    queryKey: ["report-check", analysisId],
    queryFn: () => checkAnalysisReport(analysisId!),
    enabled: !!analysisId,
    staleTime: 30_000,
  });
}

export function useLinkFiles() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ analysisId, rawFileIds }: { analysisId: string; rawFileIds: string[] }) =>
      linkFilesToAnalysis(analysisId, rawFileIds),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["stats", variables.analysisId] });
      queryClient.invalidateQueries({ queryKey: ["insight", variables.analysisId] });
      queryClient.invalidateQueries({ queryKey: ["whatif", variables.analysisId] });
      queryClient.invalidateQueries({ queryKey: ["analysis-list"] });
    },
  });
}
