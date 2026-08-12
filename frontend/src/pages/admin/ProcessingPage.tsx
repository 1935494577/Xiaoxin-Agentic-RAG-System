import { PageHeader } from "../../components/admin/PageHeader";
import { Tabs } from "../../components/ui/Tabs";
import { AgentToolsTab } from "../../components/admin/tools/AgentToolsTab";
import { IngestToolsTab } from "../../components/admin/tools/IngestToolsTab";
import { McpServersTab } from "../../components/admin/tools/McpServersTab";

export default function ProcessingPage() {
  return (
    <div className="p-6 max-w-[960px]">
      <PageHeader
        title="工具"
        description="入库 processing 工具、Chat 对话内置工具与 MCP 外部服务分开配置，互不影响。"
      />

      <Tabs
        defaultTab="ingest"
        tabs={[
          { id: "ingest", label: "入库工具", content: <IngestToolsTab /> },
          { id: "agent", label: "对话工具", content: <AgentToolsTab /> },
          { id: "mcp", label: "MCP 服务器", content: <McpServersTab /> },
        ]}
      />
    </div>
  );
}
