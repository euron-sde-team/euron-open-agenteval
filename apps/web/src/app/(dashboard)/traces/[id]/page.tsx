import { TraceDetailScreen } from "@/features/traces/components/trace-detail-screen";

export default async function TraceDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <TraceDetailScreen traceId={id} />;
}
