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

    const form = document.querySelector("[data-report-form]");
    const submitButton = document.querySelector("[data-submit-button]");

    if (form && submitButton) {
        form.addEventListener("submit", function () {
            if (!form.checkValidity()) {
                return;
            }

            submitButton.disabled = true;
            submitButton.textContent = "Mengirim...";
        });
    }

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

    if (!dropzone || !fileInput || !fileName) {
        return;
    }

    function showFile(file) {
        fileName.textContent = file ? "File dipilih: " + file.name : "Belum ada file dipilih.";
    }

    fileInput.addEventListener("change", function () {
        showFile(fileInput.files && fileInput.files[0]);
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
});
