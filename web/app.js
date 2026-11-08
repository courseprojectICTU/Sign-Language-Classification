"use strict";

(() => {
  const apiBaseUrl = window.VSL_CONFIG?.apiBaseUrl;
  if (typeof apiBaseUrl === "string" && apiBaseUrl.trim() !== "") {
    try {
      void fetch(`${apiBaseUrl.replace(/\/+$/, "")}/health`).catch(() => {});
    } catch {}
  }

  const fileInput = document.querySelector("#image-input");
  const imagePreview = document.querySelector("#image-preview");
  const previewPlaceholder = document.querySelector("#preview-placeholder");
  const openCameraButton = document.querySelector("#open-camera");
  const closeCameraButton = document.querySelector("#close-camera");
  const captureButton = document.querySelector("#capture-image");
  const cameraPanel = document.querySelector("#camera-panel");
  const cameraVideo = document.querySelector("#camera-video");
  const cameraMessage = document.querySelector("#camera-message");
  const captureCanvas = document.querySelector("#capture-canvas");
  const predictButton = document.querySelector("#predict-button");
  const loadingStatus = document.querySelector("#loading-status");
  const errorMessage = document.querySelector("#error-message");
  const resultRegion = document.querySelector("#result-region");
  const resultLetter = document.querySelector("#result-letter");
  const resultConfidence = document.querySelector("#result-confidence");
  const resultMessage = document.querySelector("#result-message");
  const supportedLettersList = document.querySelector("#supported-letters");
  const supportedError = document.querySelector("#supported-error");

  if (
    !(fileInput instanceof HTMLInputElement) ||
    !(imagePreview instanceof HTMLImageElement) ||
    !(previewPlaceholder instanceof HTMLElement) ||
    !(openCameraButton instanceof HTMLButtonElement) ||
    !(closeCameraButton instanceof HTMLButtonElement) ||
    !(captureButton instanceof HTMLButtonElement) ||
    !(cameraPanel instanceof HTMLElement) ||
    !(cameraVideo instanceof HTMLVideoElement) ||
    !(cameraMessage instanceof HTMLElement) ||
    !(captureCanvas instanceof HTMLCanvasElement) ||
    !(predictButton instanceof HTMLButtonElement) ||
    !(loadingStatus instanceof HTMLElement) ||
    !(errorMessage instanceof HTMLElement) ||
    !(resultRegion instanceof HTMLElement) ||
    !(resultLetter instanceof HTMLElement) ||
    !(resultConfidence instanceof HTMLElement) ||
    !(resultMessage instanceof HTMLElement) ||
    !(supportedLettersList instanceof HTMLUListElement) ||
    !(supportedError instanceof HTMLElement)
  ) {
    throw new Error("Required image or prediction controls are missing from the page.");
  }

  let cameraStream = null;
  let previewUrl = null;
  let selectedImage = null;

  function showPreview(file) {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    selectedImage = file;
    previewUrl = URL.createObjectURL(file);
    imagePreview.src = previewUrl;
    imagePreview.hidden = false;
    previewPlaceholder.hidden = true;
    predictButton.disabled = false;
    errorMessage.hidden = true;
    resultRegion.hidden = true;
  }

  function showCameraMessage(message) {
    cameraMessage.textContent = message;
    cameraMessage.hidden = false;
  }

  function stopCamera() {
    if (cameraStream) {
      for (const track of cameraStream.getTracks()) {
        track.stop();
      }
      cameraStream = null;
    }

    cameraVideo.srcObject = null;
    cameraPanel.hidden = true;
    captureButton.disabled = true;
    openCameraButton.disabled = false;
  }

  async function requestPrediction(file) {
    const apiBaseUrl = window.VSL_CONFIG?.apiBaseUrl;
    if (typeof apiBaseUrl !== "string" || apiBaseUrl.trim() === "") {
      throw new Error("Địa chỉ dịch vụ dự đoán chưa được cấu hình.");
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(
      `${apiBaseUrl.replace(/\/+$/, "")}/predict`,
      {
        method: "POST",
        body: formData,
      }
    );

    let payload;
    try {
      payload = await response.json();
    } catch (error) {
      console.error("Prediction API returned invalid JSON:", error);
      throw new Error("Dịch vụ trả về phản hồi không hợp lệ. Vui lòng thử lại.");
    }

    if (!response.ok) {
      const detail =
        typeof payload.detail === "string"
          ? payload.detail
          : `Dịch vụ chưa thể xử lý ảnh (HTTP ${response.status}).`;
      throw new Error(detail);
    }

    return payload;
  }

  async function loadSupportedLetters() {
    const response = await fetch("labels.json");
    if (!response.ok) {
      throw new Error(`Could not load label list (HTTP ${response.status}).`);
    }

    const labels = await response.json();
    if (
      !Array.isArray(labels) ||
      labels.length === 0 ||
      !labels.every((label) => typeof label === "string" && label.length > 0) ||
      new Set(labels).size !== labels.length
    ) {
      throw new Error("The generated label list is invalid.");
    }

    const items = labels.map((label) => {
      const item = document.createElement("li");
      item.textContent = label;
      return item;
    });
    supportedLettersList.replaceChildren(...items);
  }

  function displayPrediction(payload) {
    if (
      payload.status === "ok" &&
      payload.detected === true &&
      typeof payload.letter === "string" &&
      typeof payload.confidence === "number" &&
      Number.isFinite(payload.confidence) &&
      payload.confidence >= 0 &&
      payload.confidence <= 1
    ) {
      resultLetter.textContent = payload.letter;
      resultLetter.hidden = false;
      resultConfidence.textContent = `Độ tin cậy: ${(
        payload.confidence * 100
      ).toLocaleString("vi-VN", { maximumFractionDigits: 2 })}%`;
      resultConfidence.hidden = false;
      resultMessage.hidden = true;
      resultRegion.hidden = false;
      return;
    }

    if (
      payload.detected === false &&
      (payload.status === "no_hand" || payload.status === "no_face")
    ) {
      resultLetter.textContent = "";
      resultLetter.hidden = true;
      resultConfidence.textContent = "";
      resultConfidence.hidden = true;
      resultMessage.textContent =
        typeof payload.message === "string"
          ? payload.message
          : "Không thể nhận diện ảnh. Vui lòng thử ảnh khác.";
      resultMessage.hidden = false;
      resultRegion.hidden = false;
      return;
    }

    throw new Error("Dịch vụ trả về dữ liệu dự đoán không hợp lệ.");
  }

  fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0];
    if (file) {
      showPreview(file);
    }
  });

  cameraVideo.addEventListener("loadedmetadata", () => {
    captureButton.disabled = cameraVideo.videoWidth === 0;
  });

  openCameraButton.addEventListener("click", async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      showCameraMessage(
        "Trình duyệt không hỗ trợ camera tại địa chỉ này. Vui lòng chọn ảnh từ thiết bị."
      );
      return;
    }

    openCameraButton.disabled = true;
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user" },
      });
      cameraVideo.srcObject = cameraStream;
      cameraPanel.hidden = false;
      cameraMessage.hidden = true;
      await cameraVideo.play();
      captureButton.disabled = cameraVideo.videoWidth === 0;
    } catch (error) {
      stopCamera();
      if (error instanceof DOMException && error.name === "NotAllowedError") {
        showCameraMessage(
          "Bạn chưa cấp quyền camera. Hãy cho phép truy cập hoặc chọn ảnh từ thiết bị."
        );
      } else {
        console.error("Unable to start the camera:", error);
        showCameraMessage(
          "Không thể mở camera. Vui lòng thử lại hoặc chọn ảnh từ thiết bị."
        );
      }
    }
  });

  closeCameraButton.addEventListener("click", stopCamera);

  captureButton.addEventListener("click", () => {
    const context = captureCanvas.getContext("2d");
    if (!context || cameraVideo.videoWidth === 0 || cameraVideo.videoHeight === 0) {
      showCameraMessage("Camera chưa sẵn sàng. Vui lòng thử lại.");
      return;
    }

    captureCanvas.width = cameraVideo.videoWidth;
    captureCanvas.height = cameraVideo.videoHeight;
    context.drawImage(cameraVideo, 0, 0);
    captureCanvas.toBlob((blob) => {
      if (!blob) {
        showCameraMessage("Không thể chụp ảnh. Vui lòng thử lại.");
        return;
      }

      showPreview(new File([blob], "capture.jpg", { type: "image/jpeg" }));
      cameraMessage.hidden = true;
    }, "image/jpeg");
  });

  predictButton.addEventListener("click", async () => {
    if (!selectedImage) {
      return;
    }

    predictButton.disabled = true;
    loadingStatus.hidden = false;
    errorMessage.hidden = true;
    resultRegion.hidden = true;

    try {
      const payload = await requestPrediction(selectedImage);
      displayPrediction(payload);
    } catch (error) {
      console.error("Image prediction failed:", error);
      errorMessage.textContent =
        error instanceof TypeError
          ? "Không thể kết nối đến dịch vụ. Vui lòng kiểm tra kết nối và thử lại."
          : error instanceof Error
            ? error.message
            : "Không thể dự đoán ảnh. Vui lòng thử lại.";
      errorMessage.hidden = false;
    } finally {
      loadingStatus.hidden = true;
      predictButton.disabled = selectedImage === null;
    }
  });

  loadSupportedLetters().catch((error) => {
    console.error("Unable to load supported letters:", error);
    supportedError.textContent =
      "Không tải được danh sách ký tự. Vui lòng tải lại trang.";
    supportedError.hidden = false;
  });

  window.addEventListener("pagehide", () => {
    stopCamera();
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  });
})();
