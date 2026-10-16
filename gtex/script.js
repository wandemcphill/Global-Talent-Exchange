// Set this to your final hosted APK path before launch.
const APK_URL = "";

const yearNode = document.getElementById("year");
const downloadStatus = document.getElementById("download-status");
const apkUrlDisplay = document.getElementById("apk-url-display");
const revealItems = document.querySelectorAll(".reveal");
const apkButtons = document.querySelectorAll(".js-apk-button");
const installSection = document.getElementById("install");
const mediaImages = document.querySelectorAll("img[data-fallback-title]");

const isConfiguredApkUrl = APK_URL.trim().length > 0;

if (yearNode) {
  yearNode.textContent = new Date().getFullYear();
}

if (apkUrlDisplay) {
  apkUrlDisplay.textContent = isConfiguredApkUrl ? APK_URL : "Not configured";
}

if ("IntersectionObserver" in window) {
  const revealObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }

        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    {
      threshold: 0.16,
    }
  );

  revealItems.forEach((item) => revealObserver.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

apkButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (isConfiguredApkUrl) {
      window.location.href = APK_URL;
      return;
    }

    if (downloadStatus) {
      downloadStatus.textContent =
        "Add the release APK URL in script.js to enable Android downloads.";
    }

    if (installSection) {
      installSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

const showImageFallback = (image) => {
  const fallback = document.createElement("div");
  const isQrImage = image.classList.contains("qr-image");

  fallback.className = isQrImage
    ? "image-fallback image-fallback--qr"
    : "image-fallback image-fallback--shot";
  fallback.setAttribute("role", "img");
  fallback.setAttribute("aria-label", image.alt || image.dataset.fallbackTitle);

  const title = document.createElement("strong");
  title.textContent = image.dataset.fallbackTitle || "Image unavailable";

  const path = document.createElement("span");
  path.textContent = image.dataset.fallbackPath || image.getAttribute("src") || "";

  fallback.append(title, path);
  image.replaceWith(fallback);
};

mediaImages.forEach((image) => {
  image.addEventListener(
    "error",
    () => {
      showImageFallback(image);
    },
    { once: true }
  );

  if (image.complete && image.naturalWidth === 0) {
    showImageFallback(image);
  }
});

if (downloadStatus && isConfiguredApkUrl) {
  downloadStatus.textContent = "Android APK link is configured and ready to share.";
}
