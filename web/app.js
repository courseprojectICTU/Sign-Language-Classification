/* US-022: static Cloudflare Pages frontend for POST /predict image API. */
const apiBase = (window.VSL_API_BASE || "").replace(/\/$/, "");
const $ = (id) => document.getElementById(id);
const fileInput = $("file");
const video = $("video");
const image = $("image");
const result = $("result");
let selectedFile = null;
let stream = null;
let previewUrl = null;

function status(message, error = false) {
  $("message").textContent = message;
  $("message").classList.toggle("error", error);
}
function preview(file) {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  image.src = previewUrl;
  image.hidden = false;
  $("placeholder").hidden = true;
  selectedFile = file;
  $("predict").disabled = false;
  result.hidden = true;
  status("Ảnh đã sẵn sàng. Bấm Nhận diện ký hiệu.");
}
function stopCamera() {
  if (stream) stream.getTracks().forEach((track) => track.stop());
  stream = null;
  video.srcObject = null;
  video.hidden = true;
  $("snap").disabled = true;
  $("stop").disabled = true;
}
fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (!file) return;
  if (!["image/png", "image/jpeg"].includes(file.type)) {
    status("Chỉ hỗ trợ JPG hoặc PNG.", true);
    return;
  }
  stopCamera();
  preview(file);
});
$("camera").addEventListener("click", async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    status("Camera yêu cầu HTTPS hoặc localhost và trình duyệt được hỗ trợ.", true);
    return;
  }
  try {
    stopCamera();
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
    await video.play();
    video.hidden = false;
    image.hidden = true;
    $("placeholder").hidden = true;
    $("snap").disabled = false;
    $("stop").disabled = false;
    status("Đưa bàn tay và khuôn mặt vào khung hình, sau đó bấm Chụp ảnh.");
  } catch (error) {
    status("Không mở được camera. Kiểm tra quyền truy cập.", true);
  }
});
$("stop").addEventListener("click", () => {
  stopCamera();
  if (!selectedFile) $("placeholder").hidden = false;
  status("Đã dừng camera.");
});
$("snap").addEventListener("click", () => {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  if (!canvas.width || !canvas.height) return status("Camera chưa sẵn sàng.", true);
  canvas.getContext("2d").drawImage(video, 0, 0);
  canvas.toBlob((blob) => {
    if (!blob) return status("Không chụp được ảnh.", true);
    stopCamera();
    preview(new File([blob], "camera.jpg", { type: "image/jpeg" }));
  }, "image/jpeg", .9);
});
$("predict").addEventListener("click", async () => {
  if (!selectedFile) return;
  if (!apiBase) return status("Chưa cấu hình API. Đặt window.VSL_API_BASE trong web/config.js.", true);
  $("predict").disabled = true;
  result.hidden = true;
  status("Đang nhận diện, lần đầu có thể mất thời gian khởi động máy chủ...");
  try {
    const data = new FormData();
    data.append("file", selectedFile);
    const response = await fetch(apiBase + "/predict", { method: "POST", body: data });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "API trả lỗi " + response.status);
    if (body.status === "no_hand") return status("Không tìm thấy bàn tay. Hãy chụp lại.", true);
    if (body.status === "no_face") return status("Không tìm thấy khuôn mặt. Hãy chụp lại.", true);
    if (body.status !== "ok" || !body.letter) throw new Error("Phản hồi API không hợp lệ.");
    $("letter").textContent = body.letter;
    $("confidence").textContent = Number.isFinite(body.confidence) ? (body.confidence * 100).toFixed(1) + "%" : "—";
    $("topk").replaceChildren();
    for (const item of (Array.isArray(body.top_k) ? body.top_k : [])) {
      const p = document.createElement("p");
      p.textContent = item.letter + ": " + (Number(item.confidence) * 100).toFixed(1) + "%";
      $("topk").append(p);
    }
    $("version").textContent = "Model: " + (body.model_version || "không xác định");
    result.hidden = false;
    status("Đã nhận kết quả.");
  } catch (error) {
    status("Không thể dự đoán: " + error.message, true);
  } finally {
    $("predict").disabled = false;
  }
});
window.addEventListener("pagehide", () => {
  stopCamera();
  if (previewUrl) URL.revokeObjectURL(previewUrl);
});
// Warm-up ping without blocking the UI. Backend may scale to zero.
if (apiBase) fetch(apiBase + "/health").catch(() => {});
