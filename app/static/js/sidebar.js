/**
 * KlasiFas - Sidebar State & Navigation Controller (Hybrid Layout)
 * Mengelola state sidebar (ciut/lebar), shortcut keyboard, drawer mobile,
 * persistensi localStorage, dan focus management untuk seluruh portal staf internal.
 */
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const sidebar = document.getElementById("kf-sidebar");
    const appLayout = document.getElementById("kf-app-layout");
    const mainWrapper = document.getElementById("kf-main-wrapper");
    const toggleBtn = document.getElementById("kf-sidebar-toggle");
    const mobileToggleBtn = document.getElementById("kf-mobile-drawer-toggle");
    const mobileCloseBtn = document.getElementById("kf-mobile-drawer-close");
    const backdrop = document.getElementById("kf-sidebar-backdrop");
    const mobileQuery = window.matchMedia("(max-width: 767.98px)");
    const STORAGE_KEY = "kf_sidebar_collapsed";
    let lastFocusedBeforeDrawer = null;

    if (!sidebar) {
        return;
    }

    // Terapkan preferensi ciut tersimpan
    const isCollapsed = localStorage.getItem(STORAGE_KEY) === "true";
    if (isCollapsed && window.innerWidth >= 768) {
        sidebar.classList.add("kf-sidebar-collapsed");
        if (appLayout) {
            appLayout.classList.add("kf-sidebar-collapsed");
        }
        if (toggleBtn) {
            toggleBtn.setAttribute("aria-expanded", "false");
            const icon = toggleBtn.querySelector("i");
            if (icon) {
                icon.className = "bi bi-chevron-bar-right";
            }
        }
    }

    function isMobileViewport() {
        return mobileQuery.matches;
    }

    function getFocusableElements() {
        return Array.from(
            sidebar.querySelectorAll(
                'a[href], button:not([disabled]), input:not([disabled]), ' +
                'select:not([disabled]), textarea:not([disabled]), ' +
                '[tabindex]:not([tabindex="-1"])'
            )
        ).filter(function (element) {
            return element.getClientRects().length > 0;
        });
    }

    function syncMobileDrawerState(options) {
        const settings = options || {};
        const isOpen = sidebar.classList.contains("is-mobile-open");

        if (!isMobileViewport()) {
            sidebar.removeAttribute("inert");
            sidebar.removeAttribute("aria-hidden");
            if (mainWrapper) {
                mainWrapper.removeAttribute("inert");
            }
            if (mobileToggleBtn) {
                mobileToggleBtn.setAttribute("aria-expanded", "false");
            }
            return;
        }

        if (isOpen) {
            sidebar.removeAttribute("inert");
            sidebar.removeAttribute("aria-hidden");
            if (mobileToggleBtn) {
                mobileToggleBtn.setAttribute("aria-expanded", "true");
            }
            if (settings.focusDrawer) {
                void sidebar.offsetWidth;
                const focusTarget = mobileCloseBtn || getFocusableElements()[0];
                if (focusTarget) {
                    focusTarget.focus({ preventScroll: true });
                }
            }
            if (mainWrapper) {
                mainWrapper.setAttribute("inert", "");
            }
        } else {
            sidebar.setAttribute("inert", "");
            sidebar.setAttribute("aria-hidden", "true");
            if (mainWrapper) {
                mainWrapper.removeAttribute("inert");
            }
            if (mobileToggleBtn) {
                mobileToggleBtn.setAttribute("aria-expanded", "false");
            }
        }
    }

    function openMobileDrawer() {
        if (!isMobileViewport()) {
            return;
        }

        if (!sidebar.classList.contains("is-mobile-open")) {
            lastFocusedBeforeDrawer = document.activeElement;
        }

        sidebar.classList.add("is-mobile-open");
        if (backdrop) {
            backdrop.classList.add("is-active");
        }
        document.body.classList.add("overflow-hidden");
        syncMobileDrawerState({ focusDrawer: true });
    }

    function closeMobileDrawer(options) {
        const settings = options || {};
        const restoreFocus = settings.restoreFocus !== false;

        if (!sidebar.classList.contains("is-mobile-open")) {
            syncMobileDrawerState();
            return;
        }

        const remembered = lastFocusedBeforeDrawer;
        const focusTarget = remembered && remembered !== document.body &&
            document.contains(remembered) && !sidebar.contains(remembered)
            ? remembered
            : mobileToggleBtn;

        sidebar.classList.remove("is-mobile-open");
        if (backdrop) {
            backdrop.classList.remove("is-active");
        }
        document.body.classList.remove("overflow-hidden");
        if (mainWrapper) {
            mainWrapper.removeAttribute("inert");
        }
        if (mobileToggleBtn) {
            mobileToggleBtn.setAttribute("aria-expanded", "false");
        }

        if (restoreFocus && focusTarget) {
            focusTarget.focus({ preventScroll: true });
        }

        sidebar.setAttribute("inert", "");
        sidebar.setAttribute("aria-hidden", "true");
        lastFocusedBeforeDrawer = null;
    }

    function toggleMobileDrawer(open) {
        if (!isMobileViewport()) {
            return;
        }

        const willOpen = typeof open === "boolean"
            ? open
            : !sidebar.classList.contains("is-mobile-open");

        if (willOpen) {
            openMobileDrawer();
        } else {
            closeMobileDrawer();
        }
    }

    function handleViewportChange() {
        if (isMobileViewport()) {
            syncMobileDrawerState();
            return;
        }

        const wasOpen = sidebar.classList.contains("is-mobile-open");
        sidebar.classList.remove("is-mobile-open");
        if (backdrop) {
            backdrop.classList.remove("is-active");
        }
        document.body.classList.remove("overflow-hidden");
        sidebar.removeAttribute("inert");
        sidebar.removeAttribute("aria-hidden");
        if (mainWrapper) {
            mainWrapper.removeAttribute("inert");
        }
        if (mobileToggleBtn) {
            mobileToggleBtn.setAttribute("aria-expanded", "false");
        }

        if (wasOpen && sidebar.contains(document.activeElement) && toggleBtn) {
            toggleBtn.focus({ preventScroll: true });
        }

        lastFocusedBeforeDrawer = null;
    }

    function toggleSidebar() {
        const willCollapse = !sidebar.classList.contains("kf-sidebar-collapsed");
        sidebar.classList.toggle("kf-sidebar-collapsed", willCollapse);
        if (appLayout) {
            appLayout.classList.toggle("kf-sidebar-collapsed", willCollapse);
        }
        localStorage.setItem(STORAGE_KEY, willCollapse ? "true" : "false");

        if (toggleBtn) {
            toggleBtn.setAttribute("aria-expanded", willCollapse ? "false" : "true");
            const icon = toggleBtn.querySelector("i");
            if (icon) {
                icon.className = willCollapse ? "bi bi-chevron-bar-right" : "bi bi-chevron-bar-left";
            }
        }

        // Picu resize event agar grafik Chart.js menyesuaikan lebar kanvas secara presisi
        window.setTimeout(function () {
            window.dispatchEvent(new Event("resize"));
        }, 220);
    }

    if (toggleBtn) {
        toggleBtn.addEventListener("click", function (e) {
            e.preventDefault();
            toggleSidebar();
        });
    }

    if (mobileToggleBtn) {
        mobileToggleBtn.addEventListener("click", function (e) {
            e.preventDefault();
            toggleMobileDrawer();
        });
    }

    if (mobileCloseBtn) {
        mobileCloseBtn.addEventListener("click", function (e) {
            e.preventDefault();
            closeMobileDrawer();
        });
    }

    if (backdrop) {
        backdrop.addEventListener("click", function () {
            closeMobileDrawer();
        });
    }

    if (mobileQuery.addEventListener) {
        mobileQuery.addEventListener("change", handleViewportChange);
    } else {
        mobileQuery.addListener(handleViewportChange);
    }

    // Pintasan Keyboard: '[' atau 'Ctrl+B' untuk toggle sidebar
    document.addEventListener("keydown", function (e) {
        if (sidebar.classList.contains("is-mobile-open")) {
            if (e.key === "Escape") {
                e.preventDefault();
                closeMobileDrawer();
                return;
            }

            if (e.key === "Tab") {
                const focusableElements = getFocusableElements();
                if (!focusableElements.length) {
                    e.preventDefault();
                    return;
                }

                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];

                if (e.shiftKey && document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus({ preventScroll: true });
                } else if (!e.shiftKey && document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus({ preventScroll: true });
                } else if (!sidebar.contains(document.activeElement)) {
                    e.preventDefault();
                    firstElement.focus({ preventScroll: true });
                }
                return;
            }
        }

        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
        if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
            return;
        }

        if (e.key === "[" || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b")) {
            e.preventDefault();
            if (window.innerWidth >= 768) {
                toggleSidebar();
            } else {
                toggleMobileDrawer();
            }
        }
    });

    syncMobileDrawerState();
});
