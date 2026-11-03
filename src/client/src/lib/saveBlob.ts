/** Attach downloads before clicking and keep their URLs alive for async browsers. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  try {
    anchor.click();
  } finally {
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  }
}

export function saveText(content: string, filename: string, mime = "text/plain;charset=utf-8"): void {
  saveBlob(new Blob([content], { type: mime }), filename);
}
