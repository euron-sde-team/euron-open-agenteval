import { DatasetDetailScreen } from "@/features/datasets/components/dataset-detail-screen";

export default async function DatasetDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DatasetDetailScreen datasetId={id} />;
}
