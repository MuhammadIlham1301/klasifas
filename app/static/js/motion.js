(function () {
    "use strict";

    var REVEAL_SELECTOR = [
        "main#main-content .kf-page-heading",
        "main#main-content .kf-kpi--status-pill",
        "main#main-content .card",
        "main#main-content .kf-form-section",
        "#top-rooms-list .list-group-item"
    ].join(",");

    var reducedMotionQuery = window.matchMedia
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : null;
    var observer = null;
    var ready = false;

    function prefersReducedMotion() {
        return !!(reducedMotionQuery && reducedMotionQuery.matches);
    }

    function reveal(element) {
        element.classList.add("is-revealed");
        if (observer) {
            observer.unobserve(element);
        }
    }

    function revealAll() {
        document.querySelectorAll(".kf-reveal").forEach(reveal);
        if (observer) {
            observer.disconnect();
        }
        document.documentElement.classList.remove("kf-motion-ready");
    }

    function mark(element, delay) {
        if (!element || !observer) {
            return;
        }

        if (delay) {
            element.style.setProperty("--kf-reveal-delay", delay + "ms");
        }

        if (element.dataset.kfReveal === "true") {
            return;
        }

        element.dataset.kfReveal = "true";
        element.classList.add("kf-reveal");
        observer.observe(element);
    }

    function markList(list) {
        if (!list) {
            return;
        }

        list.querySelectorAll(".list-group-item").forEach(function (item, index) {
            mark(item, Math.min(index, 4) * 45);
        });
    }

    function collectInitial() {
        document.querySelectorAll(REVEAL_SELECTOR).forEach(function (element) {
            if (element.matches(".kf-form-card") && element.querySelector(".kf-form-section")) {
                return;
            }
            if (element.matches(".kf-page-heading") && element.closest(".card")) {
                return;
            }
            mark(element, 0);
        });

        document.querySelectorAll("main#main-content .kf-kpi").forEach(function (card) {
            var row = card.closest(".row");
            var siblings = row
                ? Array.prototype.slice.call(row.querySelectorAll(".kf-kpi"))
                : [card];
            mark(card, Math.min(Math.max(siblings.indexOf(card), 0), 5) * 70);
        });

        document.querySelectorAll("main#main-content .kf-form-section").forEach(function (section) {
            var parent = section.closest("form") || section.parentElement;
            var siblings = parent
                ? Array.prototype.slice.call(parent.querySelectorAll(".kf-form-section"))
                : [section];
            mark(section, Math.min(Math.max(siblings.indexOf(section), 0), 4) * 60);
        });

        markList(document.getElementById("top-rooms-list"));
    }

    function refresh(root) {
        if (!ready || prefersReducedMotion() || !root) {
            return;
        }

        if (root.id === "top-rooms-list") {
            markList(root);
            return;
        }

        var list = root.querySelector ? root.querySelector("#top-rooms-list") : null;
        if (list) {
            markList(list);
        }
    }

    function init() {
        if (prefersReducedMotion() || !("IntersectionObserver" in window)) {
            return;
        }

        observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    reveal(entry.target);
                }
            });
        }, {
            rootMargin: "0px 0px -8% 0px",
            threshold: 0.08
        });

        collectInitial();
        document.documentElement.classList.add("kf-motion-ready");
        ready = true;

        if (reducedMotionQuery && reducedMotionQuery.addEventListener) {
            reducedMotionQuery.addEventListener("change", function (event) {
                if (event.matches) {
                    revealAll();
                }
            });
        }

        window.kfMotion = { refresh: refresh };
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

// Universal Toast Notification Manager (Academic Civic Trust)
window.KlasifasToast = window.KlasifasToast || {
    show: function (message, type, delay) {
        type = type || "info";
        delay = delay || 3500;
        var container = document.getElementById("kf-toast-container");
        if (!container) return;

        var icons = {
            success: "bi-check-circle-fill text-success",
            danger: "bi-exclamation-octagon-fill text-danger",
            warning: "bi-exclamation-triangle-fill text-warning",
            info: "bi-info-circle-fill text-primary"
        };
        var iconClass = icons[type] || icons.info;

        var toastEl = document.createElement("div");
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
            var bsToast = new bootstrap.Toast(toastEl, { autohide: true, delay: delay });
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
