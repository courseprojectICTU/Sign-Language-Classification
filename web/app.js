"use strict";

(() => {
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
    !(predictButton instanceof HTMLButtonElement)
  ) {
    throw new Error("Required image capture controls are missing from the page.");
  }

  let cameraStream = null;
  let previewUrl = null;

  function showPreview(file) {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    previewUrl = URL.createObjectURL(file);
    imagePreview.src = previewUrl;
    imagePreview.hidden = false;
    previewPlaceholder.hidden = true;
    predictButton.disabled = false;
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

  window.addEventListener("pagehide", () => {
    stopCamera();
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  });
})();
