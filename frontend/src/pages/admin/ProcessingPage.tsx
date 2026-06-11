import { PageHeader } from "../../components/admin/PageHeader";
import { Tabs } from "../../components/ui/Tabs";
import { AgentToolsTab } from "../../components/admin/tools/AgentToolsTab";
import { IngestToolsTab } from "../../components/admin/tools/IngestToolsTab";

export default function ProcessingPage() {
  return (
    <div className="p-6 max-w-[720px]">
      <PageHeader
        title="工具"
        description="入库 processing 工具与 Chat 对话工具分开配置，互不影响。"
      />

      <Tabs
        defaultTab="ingest"
        tabs={[
          { id: "ingest", label: "入库工具", content: <IngestToolsTab /> },
          { id: "agent", label: "对话工具", content: <AgentToolsTab /> },
        ]}
      />
    </div>
  );
}
