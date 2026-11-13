import { RunDetailScreen } from "@/features/evaluations/components/run-detail-screen";

export default async function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RunDetailScreen runId={id} />;
}
