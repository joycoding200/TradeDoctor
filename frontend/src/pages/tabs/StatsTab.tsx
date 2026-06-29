import { LoadingSpinner, ErrorBox } from "../../components/ui";
import StatsCards from "../../components/StatsCards";

interface StatsTabProps {
  stats: {
    isLoading: boolean;
    error: Error | null;
    data: any;
  };
  analysisId?: string;
}

export default function StatsTab({ stats, analysisId }: StatsTabProps) {
  if (stats.isLoading) return <LoadingSpinner text="加载统计数据..." />;
  if (stats.error) return <ErrorBox message="加载失败" />;
  if (stats.data)
    return <StatsCards stats={stats.data} analysisId={analysisId} />;
  return null;
}
