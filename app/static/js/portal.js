document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const description = document.getElementById("description");
    const counter = document.getElementById("description-counter");
    const progressFill = document.getElementById("description-progress");
    const numberFormat = new Intl.NumberFormat("id-ID");
    const NEAR_LIMIT_RATIO = 0.9;

    function updateCounter() {
        if (!description || !counter) {
            return;
        }

        const maxLength = Number(counter.dataset.maxLength) || Number(description.maxLength) || 2000;
        const length = description.value.length;

        counter.textContent = numberFormat.format(length) + " / " + numberFormat.format(maxLength) + " karakter";
        counter.classList.toggle("is-near-limit", length >= maxLength * NEAR_LIMIT_RATIO);

        if (progressFill) {
            const ratio = maxLength > 0 ? (length / maxLength) * 100 : 0;
            progressFill.style.width = Math.min(100, ratio).toFixed(2) + "%";
            progressFill.classList.toggle("is-near-limit", length >= maxLength * NEAR_LIMIT_RATIO);
        }
    }

    if (description && counter) {
        updateCounter();
        description.addEventListener("input", updateCounter);
    }

    // Umpan balik pengiriman formulir & pencegahan klik ganda (micro-interactions)
    const allForms = document.querySelectorAll("form");
    allForms.forEach(function (currentForm) {
        if (currentForm.method.toUpperCase() === "GET" || currentForm.id === "dashboard-filter-form") {
            return;
        }

        currentForm.addEventListener("submit", function (event) {
            if (!currentForm.checkValidity()) {
                return;
            }

            if (currentForm.dataset.submitting === "true") {
                event.preventDefault();
                return;
            }

            const submitBtn = currentForm.querySelector("[data-submit-button]") ||
                              currentForm.querySelector("button[type='submit']");
            if (!submitBtn) {
                return;
            }

            currentForm.dataset.submitting = "true";

            if (currentForm.hasAttribute("data-report-form")) {
                submitBtn.disabled = true;
                submitBtn.textContent = "Mengirim...";
            } else {
                window.setTimeout(function () {
                    submitBtn.disabled = true;
                }, 0);

                if (!submitBtn.querySelector(".spinner-border")) {
                    const spinner = document.createElement("span");
                    spinner.className = "spinner-border spinner-border-sm me-1";
                    spinner.setAttribute("role", "status");
                    spinner.setAttribute("aria-hidden", "true");
                    submitBtn.prepend(spinner);
                }
            }
        });
    });

    const copyButtons = document.querySelectorAll("[data-copy-target]");
    const copyTimers = new WeakMap();

    function findCopyTarget(targetId) {
        const existing = document.getElementById(targetId);
        if (existing) {
            return existing;
        }

        const selectors = {
            "ticket-code-value": ".kf-code-box--reference .font-monospace",
            "access-token-value": ".kf-code-box--secret .font-monospace"
        };
        const selector = selectors[targetId];

        if (!selector) {
            return null;
        }

        const element = document.querySelector(selector);
        if (element) {
            element.id = targetId;
        }

        return element;
    }

    function copyWithSelection(element) {
        const selection = window.getSelection();
        if (!selection) {
            return false;
        }

        const range = document.createRange();
        range.selectNodeContents(element);
        selection.removeAllRanges();
        selection.addRange(range);

        let copied = false;
        try {
            copied = document.execCommand("copy");
        } catch (_) {
            copied = false;
        }

        selection.removeAllRanges();
        return copied;
    }

    async function copyText(text, element) {
        if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (_) {
                return element ? copyWithSelection(element) : false;
            }
        }

        return element ? copyWithSelection(element) : false;
    }

    function showCopyFeedback(button, copied) {
        const label = button.querySelector("[data-copy-label]");
        if (!label) {
            return;
        }

        const previousTimer = copyTimers.get(button);
        if (previousTimer) {
            window.clearTimeout(previousTimer);
        }

        const originalLabel = button.dataset.originalLabel || label.textContent;
        button.dataset.originalLabel = originalLabel;
        label.textContent = copied ? "Tersalin!" : "Gagal menyalin";
        button.classList.toggle("is-copied", copied);
        button.classList.toggle("is-copy-error", !copied);

        const timer = window.setTimeout(function () {
            label.textContent = originalLabel;
            button.classList.remove("is-copied", "is-copy-error");
            copyTimers.delete(button);
        }, 2000);

        copyTimers.set(button, timer);
    }

    copyButtons.forEach(function (button) {
        button.addEventListener("click", async function () {
            const target = findCopyTarget(button.dataset.copyTarget);
            if (!target) {
                return;
            }

            const text = target.textContent.trim();
            if (!text) {
                return;
            }

            let copied = false;
            try {
                copied = await copyText(text, target);
            } catch (_) {
                copied = false;
            }

            showCopyFeedback(button, copied);

            if (copied && window.KlasifasToast) {
                const targetName = button.dataset.copyTarget === "ticket-code-value"
                    ? "Kode referensi tiket"
                    : (button.dataset.copyTarget === "access-token-value" ? "Token akses rahasia" : "Teks");
                window.KlasifasToast.show(targetName + " berhasil disalin ke clipboard.", "success", 3000);
            }
        });
    });

    const tokenToggle = document.querySelector("[data-token-toggle]");

    if (tokenToggle) {
        tokenToggle.addEventListener("click", function () {
            const targetId = tokenToggle.getAttribute("aria-controls");
            const tokenInput = targetId ? document.getElementById(targetId) : null;
            if (!tokenInput) {
                return;
            }

            const icon = tokenToggle.querySelector("[data-token-toggle-icon]");
            const label = tokenToggle.querySelector("[data-token-toggle-label]");
            const willShow = tokenInput.type === "password";

            tokenInput.type = willShow ? "text" : "password";
            tokenToggle.setAttribute("aria-pressed", willShow ? "true" : "false");

            if (icon) {
                icon.classList.toggle("bi-eye", !willShow);
                icon.classList.toggle("bi-eye-slash", willShow);
            }
            if (label) {
                label.textContent = willShow ? "Sembunyikan" : "Lihat";
            }
        });
    }

    const dropzone = document.querySelector("[data-photo-dropzone]");
    const fileInput = document.getElementById("photo");
    const fileName = document.querySelector("[data-photo-file-name]");
    const previewBox = document.getElementById("photo-preview-box");
    const previewImg = document.getElementById("photo-preview-img");
    const previewSize = document.getElementById("photo-preview-size");
    const removeBtn = document.getElementById("photo-remove-btn");

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
    }

    function showFile(file) {
        if (!fileName) return;

        if (file) {
            const validTypes = ["image/jpeg", "image/png", "image/jpg"];
            const isImage = (file.type && validTypes.includes(file.type)) || /\.(jpe?g|png)$/i.test(file.name);

            if (!isImage) {
                fileName.textContent = "Format file tidak didukung. Harap pilih gambar JPG atau PNG.";
                if (previewBox) previewBox.classList.remove("is-active");
                if (previewImg) previewImg.src = "";
                return;
            }

            fileName.textContent = "File dipilih: " + file.name + " (" + formatBytes(file.size) + ")";
            if (previewBox && previewImg) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    previewImg.src = e.target.result;
                    previewImg.alt = "Pratinjau " + file.name;
                    if (previewSize) {
                        previewSize.textContent = file.name + " · " + formatBytes(file.size);
                    }
                    previewBox.classList.add("is-active");
                };
                reader.onerror = function () {
                    fileName.textContent = "Gagal membaca berkas gambar.";
                    previewBox.classList.remove("is-active");
                };
                reader.readAsDataURL(file);
            }
        } else {
            fileName.textContent = "Belum ada file dipilih.";
            if (previewBox && previewImg) {
                previewImg.src = "";
                previewBox.classList.remove("is-active");
            }
        }
    }

    if (removeBtn && fileInput) {
        removeBtn.addEventListener("click", function (e) {
            e.preventDefault();
            fileInput.value = "";
            showFile(null);
            fileInput.dispatchEvent(new Event("change"));
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", function () {
            showFile(fileInput.files && fileInput.files[0]);
        });
    }

    if (dropzone && fileInput) {
        dropzone.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInput.click();
            }
        });

        ["dragenter", "dragover"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (event) {
                event.preventDefault();
                event.stopPropagation();
                dropzone.classList.add("is-dragover");
            });
        });

        ["dragleave", "dragend"].forEach(function (eventName) {
            dropzone.addEventListener(eventName, function (event) {
                event.preventDefault();
                event.stopPropagation();

                if (event.relatedTarget && dropzone.contains(event.relatedTarget)) {
                    return;
                }

                dropzone.classList.remove("is-dragover");
            });
        });

        dropzone.addEventListener("drop", function (event) {
            event.preventDefault();
            event.stopPropagation();
            dropzone.classList.remove("is-dragover");

            const files = event.dataTransfer && event.dataTransfer.files;
            if (!files || !files.length) {
                return;
            }

            try {
                const transfer = new DataTransfer();
                transfer.items.add(files[0]);
                fileInput.files = transfer.files;
            } catch (_) {
                return;
            }

            showFile(files[0]);
        });
    }

    // Sidebar Collapsible & Mobile Drawer Management (Internal Mode)
    const sidebar = document.getElementById("kf-sidebar");
    const mainWrapper = document.getElementById("kf-main-wrapper");
    const sidebarToggle = document.getElementById("kf-sidebar-toggle");
    const mobileSidebarToggle = document.getElementById("kf-mobile-sidebar-toggle");
    const sidebarBackdrop = document.getElementById("kf-sidebar-backdrop");

    if (sidebar && mainWrapper) {
        // Restore state from localStorage
        const savedState = localStorage.getItem("kf_sidebar_collapsed");
        if (savedState === "1" && window.innerWidth >= 768) {
            sidebar.classList.add("is-collapsed");
            mainWrapper.classList.add("is-collapsed");
            const icon = document.getElementById("kf-sidebar-toggle-icon");
            if (icon) {
                icon.className = "bi bi-chevron-right";
            }
        }

        if (sidebarToggle) {
            sidebarToggle.addEventListener("click", function () {
                const isCollapsed = sidebar.classList.toggle("is-collapsed");
                mainWrapper.classList.toggle("is-collapsed", isCollapsed);
                localStorage.setItem("kf_sidebar_collapsed", isCollapsed ? "1" : "0");

                const icon = document.getElementById("kf-sidebar-toggle-icon");
                if (icon) {
                    icon.className = isCollapsed ? "bi bi-chevron-right" : "bi bi-chevron-left";
                }
            });
        }

        if (mobileSidebarToggle) {
            mobileSidebarToggle.addEventListener("click", function () {
                sidebar.classList.add("is-mobile-open");
                if (sidebarBackdrop) {
                    sidebarBackdrop.classList.add("is-visible");
                }
            });
        }

        if (sidebarBackdrop) {
            sidebarBackdrop.addEventListener("click", function () {
                sidebar.classList.remove("is-mobile-open");
                sidebarBackdrop.classList.remove("is-visible");
            });
        }

        // Shortcut keyboard toggle [ or Ctrl+B
        document.addEventListener("keydown", function (e) {
            if ((e.key === "[" || (e.ctrlKey && e.key.toLowerCase() === "b")) && !["INPUT", "TEXTAREA"].includes(e.target.tagName)) {
                if (sidebarToggle && window.innerWidth >= 768) {
                    e.preventDefault();
                    sidebarToggle.click();
                }
            }
        });
    }
});

// Universal Toast Notification Manager (Academic Civic Trust)
window.KlasifasToast = window.KlasifasToast || {
    show: function (message, type, delay) {
        type = type || "info";
        delay = delay || 3500;
        const container = document.getElementById("kf-toast-container");
        if (!container) return;

        const icons = {
            success: "bi-check-circle-fill text-success",
            danger: "bi-exclamation-octagon-fill text-danger",
            warning: "bi-exclamation-triangle-fill text-warning",
            info: "bi-info-circle-fill text-primary"
        };
        const iconClass = icons[type] || icons.info;

        const toastEl = document.createElement("div");
        toastEl.className = "toast kf-toast kf-toast--" + type + " align-items-center border-0 mb-2";
        toastEl.setAttribute("role", "status");
        toastEl.setAttribute("aria-live", "polite");
        toastEl.setAttribute("aria-atomic", "true");

        toastEl.innerHTML =
            '<div class="d-flex p-2 align-items-center">' +
                '<i class="bi ' + iconClass + ' fs-5 me-2 ms-1" aria-hidden="true"></i>' +
                '<div class="toast-body small fw-semibold flex-grow-1">' + message + '</div>' +
                '<button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Tutup"></button>' +
            '</div>';

        container.appendChild(toastEl);

        if (typeof bootstrap !== "undefined" && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toastEl, { autohide: true, delay: delay });
            toastEl.addEventListener("hidden.bs.toast", function () {
                toastEl.remove();
            });
            bsToast.show();
        } else {
            toastEl.classList.add("show");
            window.setTimeout(function () {
                toastEl.classList.remove("show");
                toastEl.remove();
            }, delay);
        }
    }
};
