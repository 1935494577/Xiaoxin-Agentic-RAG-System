/** Resize image file to a square data URL for avatar storage. */
export async function fileToAvatarDataUrl(
  file: File,
  maxSize = 128,
  maxBytes = 180_000
): Promise<string> {
  if (!file.type.startsWith("image/")) {
    throw new Error("请选择图片文件");
  }
  const bitmap = await createImageBitmap(file);
  const side = Math.min(bitmap.width, bitmap.height);
  const sx = (bitmap.width - side) / 2;
  const sy = (bitmap.height - side) / 2;
  const canvas = document.createElement("canvas");
  canvas.width = maxSize;
  canvas.height = maxSize;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("无法处理图片");
  ctx.drawImage(bitmap, sx, sy, side, side, 0, 0, maxSize, maxSize);
  bitmap.close();

  let quality = 0.88;
  let dataUrl = canvas.toDataURL("image/jpeg", quality);
  while (dataUrl.length > maxBytes && quality > 0.35) {
    quality -= 0.12;
    dataUrl = canvas.toDataURL("image/jpeg", quality);
  }
  if (dataUrl.length > maxBytes) {
    throw new Error("图片过大，请换一张更小的图片");
  }
  return dataUrl;
}

export function profileInitial(name: string, fallback = "你"): string {
  const trimmed = name.trim();
  if (!trimmed) return fallback;
  return trimmed.slice(0, 1);
}

export function profileLabel(name: string, fallback = "用户"): string {
  const trimmed = name.trim();
  return trimmed || fallback;
}
