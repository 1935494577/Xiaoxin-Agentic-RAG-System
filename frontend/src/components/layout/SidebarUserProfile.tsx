import { useRef, useState } from "react";
import { MoreHorizontal } from "lucide-react";
import { Dialog } from "../ui/Dialog";
import { Label } from "../ui/Label";
import { ChatAvatar } from "../chat/ChatAvatar";
import { useUserProfile } from "../../context/UserProfileContext";
import { DEPT_OPTIONS } from "../../lib/constants";
import { fileToAvatarDataUrl, profileLabel } from "../../lib/avatarImage";
import { toast } from "sonner";

export function SidebarUserProfile() {
  const {
    loading,
    displayName,
    avatarUrl,
    aiDisplayName,
    aiAvatarUrl,
    department,
    saveProfile,
  } = useUserProfile();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftDept, setDraftDept] = useState("技术部");
  const [draftAvatar, setDraftAvatar] = useState("");
  const [draftAiName, setDraftAiName] = useState("");
  const [draftAiAvatar, setDraftAiAvatar] = useState("");
  const userFileRef = useRef<HTMLInputElement>(null);
  const aiFileRef = useRef<HTMLInputElement>(null);

  const openDialog = () => {
    setDraftName(displayName);
    setDraftDept(department);
    setDraftAvatar(avatarUrl);
    setDraftAiName(aiDisplayName);
    setDraftAiAvatar(aiAvatarUrl);
    setOpen(true);
  };

  const onPickAvatar = async (file: File | undefined, target: "user" | "ai") => {
    if (!file) return;
    try {
      const url = await fileToAvatarDataUrl(file);
      if (target === "user") setDraftAvatar(url);
      else setDraftAiAvatar(url);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "头像处理失败");
    }
  };

  const onSave = async () => {
    setSaving(true);
    try {
      await saveProfile({
        display_name: draftName.trim(),
        department: draftDept,
        avatar_url: draftAvatar,
        ai_display_name: draftAiName.trim(),
        ai_avatar_url: draftAiAvatar,
      });
      toast.success("已保存");
      setOpen(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const label = profileLabel(displayName);

  return (
    <>
      <div className="px-2 py-2 border-t border-border">
        <button
          type="button"
          onClick={openDialog}
          className="w-full flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-white/80 transition-colors cursor-pointer group text-left"
          title="用户设置"
        >
          <ChatAvatar
            avatarUrl={avatarUrl}
            label={displayName}
            fallback="你"
            variant="user"
            size="sidebar"
          />
          <span className="flex-1 min-w-0 text-sm text-text truncate">
            {loading ? "加载中…" : label}
          </span>
          <MoreHorizontal
            size={16}
            className="shrink-0 text-text-muted opacity-60 group-hover:opacity-100"
          />
        </button>
      </div>

      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        title="用户设置"
        confirmLabel="保存"
        onConfirm={onSave}
        loading={saving}
      >
        <div className="space-y-5 text-text max-h-[60vh] overflow-y-auto pr-1">
          <section>
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3">我的资料</p>
            <div className="flex items-center gap-4 mb-4">
              <button
                type="button"
                onClick={() => userFileRef.current?.click()}
                className="relative rounded-full cursor-pointer hover:opacity-90 transition-opacity shrink-0"
              >
                <ChatAvatar
                  avatarUrl={draftAvatar}
                  label={draftName}
                  fallback="你"
                  variant="user"
                  size="sidebar"
                />
                <span className="absolute -bottom-1 -right-1 text-[10px] bg-brand text-white px-1.5 py-0.5 rounded-full">
                  更换
                </span>
              </button>
              <input
                ref={userFileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => onPickAvatar(e.target.files?.[0], "user")}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-text-muted">对话中你的头像</p>
                {draftAvatar && (
                  <button
                    type="button"
                    className="text-xs text-brand hover:underline cursor-pointer mt-1"
                    onClick={() => setDraftAvatar("")}
                  >
                    移除头像
                  </button>
                )}
              </div>
            </div>
            <Label htmlFor="profile-name">昵称</Label>
            <input
              id="profile-name"
              type="text"
              maxLength={64}
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              placeholder="例如：风停看雨画"
              className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
            />
          </section>

          <section className="pt-1 border-t border-border-light">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3 mt-4">助手展示</p>
            <div className="flex items-center gap-4 mb-4">
              <button
                type="button"
                onClick={() => aiFileRef.current?.click()}
                className="relative rounded-full cursor-pointer hover:opacity-90 transition-opacity shrink-0"
              >
                <ChatAvatar
                  avatarUrl={draftAiAvatar}
                  label={draftAiName}
                  fallback="AI"
                  variant="ai"
                  size="sidebar"
                />
                <span className="absolute -bottom-1 -right-1 text-[10px] bg-brand text-white px-1.5 py-0.5 rounded-full">
                  更换
                </span>
              </button>
              <input
                ref={aiFileRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => onPickAvatar(e.target.files?.[0], "ai")}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-text-muted">对话中 AI 的头像</p>
                {draftAiAvatar && (
                  <button
                    type="button"
                    className="text-xs text-brand hover:underline cursor-pointer mt-1"
                    onClick={() => setDraftAiAvatar("")}
                  >
                    移除头像
                  </button>
                )}
              </div>
            </div>
            <Label htmlFor="profile-ai-name">助手名称</Label>
            <input
              id="profile-ai-name"
              type="text"
              maxLength={64}
              value={draftAiName}
              onChange={(e) => setDraftAiName(e.target.value)}
              placeholder="留空则显示 AI"
              className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
            />
          </section>

          <section className="pt-1 border-t border-border-light">
            <Label htmlFor="profile-dept">部门权限</Label>
            <select
              id="profile-dept"
              value={draftDept}
              onChange={(e) => setDraftDept(e.target.value)}
              className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
            >
              {DEPT_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <p className="text-xs text-text-muted mt-1.5">决定可检索的知识库文档范围</p>
          </section>
        </div>
      </Dialog>
    </>
  );
}
