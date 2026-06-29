import { LoadingSpinner, ErrorBox } from "../../components/ui";
import StatsCards from "../../components/StatsCards";

interface StatsTabProps {
  stats: {
    isLoading: boolean;
    error: Error | null;
    data: any;
  };
  analysisId?: string;
  /**
   * Open the in-page AddFileModal (preferred for adding files to an
   * existing analysis — keeps the user on this page and invalidates
   * React Query automatically). If not provided, StatsCards falls back
   * to /upload?attach_to=... navigation.
   */
  onAddFile?: () => void;
}

export default function StatsTab({ stats, analysisId, onAddFile }: StatsTabProps) {
  if (stats.isLoading) return <LoadingSpinner text="加载统计数据..." />;
  if (stats.error) return <ErrorBox message="加载失败" />;
  if (stats.data)
    return (
      <StatsCards
        stats={stats.data}
        analysisId={analysisId}
        onAddFile={onAddFile}
      />
    );
  return null;
}
