import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, MoreHorizontal } from "lucide-react";
import { Dialog } from "../ui/Dialog";
import { Label } from "../ui/Label";
import { ChatAvatar } from "../chat/ChatAvatar";
import { useAuth } from "../../hooks/useAuth";
import { useUserProfile } from "../../context/UserProfileContext";
import { authChangePassword } from "../../api/client";
import { fileToAvatarDataUrl, profileLabel } from "../../lib/avatarImage";
import { toast } from "sonner";

export function SidebarUserProfile() {
  const navigate = useNavigate();
  const { logout, department, username } = useAuth();
  const {
    loading,
    displayName,
    avatarUrl,
    aiDisplayName,
    aiAvatarUrl,
    saveProfile,
  } = useUserProfile();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [draftAvatar, setDraftAvatar] = useState("");
  const [draftAiName, setDraftAiName] = useState("");
  const [draftAiAvatar, setDraftAiAvatar] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const userFileRef = useRef<HTMLInputElement>(null);
  const aiFileRef = useRef<HTMLInputElement>(null);

  const openDialog = () => {
    setDraftName(displayName || username);
    setDraftAvatar(avatarUrl);
    setDraftAiName(aiDisplayName);
    setDraftAiAvatar(aiAvatarUrl);
    setCurrentPassword("");
    setNewPassword("");
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
      if (newPassword.trim()) {
        if (newPassword.trim().length < 6) {
          toast.error("新密码至少 6 位");
          return;
        }
        if (!currentPassword) {
          toast.error("修改密码需填写当前密码");
          return;
        }
        await authChangePassword(currentPassword, newPassword.trim());
        toast.success("密码已更新");
      }
      await saveProfile({
        display_name: draftName.trim(),
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

  const label = profileLabel(displayName || username);

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <>
      <div className="px-2 py-2 border-t border-border space-y-1">
        <button
          type="button"
          onClick={openDialog}
          className="w-full flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-white/80 transition-colors cursor-pointer group text-left"
          title="用户设置"
        >
          <ChatAvatar
            avatarUrl={avatarUrl}
            label={displayName || username}
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
        <button
          type="button"
          onClick={handleLogout}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm text-text-muted hover:text-brand hover:bg-white/80 transition-colors cursor-pointer"
        >
          <LogOut size={14} />
          退出登录
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
                <p className="text-xs text-text-muted mt-1">登录账号：{username}</p>
              </div>
            </div>
            <Label htmlFor="profile-name">昵称</Label>
            <input
              id="profile-name"
              type="text"
              maxLength={64}
              autoComplete="nickname"
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
            />
          </section>

          <section className="pt-1 border-t border-border-light">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3 mt-4">助手展示</p>
            <Label htmlFor="profile-ai-name">助手名称</Label>
            <input
              id="profile-ai-name"
              type="text"
              maxLength={64}
              autoComplete="off"
              placeholder="留空则对话中显示 AI"
              value={draftAiName}
              onChange={(e) => setDraftAiName(e.target.value)}
              className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand"
            />
          </section>

          <section className="pt-1 border-t border-border-light">
            <Label>所属部门</Label>
            <p className="mt-1 text-sm text-text">{department}</p>
            <p className="text-xs text-text-muted mt-1">由账号绑定，决定管理功能与知识库可见范围</p>
          </section>

          <section className="pt-1 border-t border-border-light">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-3 mt-4">修改密码</p>
            <Label htmlFor="current-pw">当前密码</Label>
            <input
              id="current-pw"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="mt-1 mb-3 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
            />
            <Label htmlFor="new-pw">新密码（至少 6 位，留空则不修改）</Label>
            <input
              id="new-pw"
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="mt-1 flex h-10 w-full rounded-lg border border-border bg-white px-3 py-2 text-sm"
            />
          </section>
        </div>
      </Dialog>
    </>
  );
}
