import { AgentDetailScreen } from "@/features/agents/components/agent-detail-screen";

export default async function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AgentDetailScreen agentId={id} />;
}
