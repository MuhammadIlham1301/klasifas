/**
 * KlasiFas - Skrip Dasbor Pemantauan Manajerial dan Visualisasi (FR-07).
 * Mengelola pemanggilan data agregat asinkron, inisialisasi dan pembaruan Chart.js,
 * serta manajemen status tampilan (loading, empty, error, retry).
 */

document.addEventListener("DOMContentLoaded", function () {
    // Referensi Elemen DOM
    const filterForm = document.getElementById("dashboard-filter-form");
    const filterDays = document.getElementById("filter_days");
    const filterCategory = document.getElementById("filter_category");
    const filterFloor = document.getElementById("filter_floor");
    const btnReset = document.getElementById("btn-reset-filter");
    const filterSummaryText = document.getElementById("filter-summary-text");

    const loadingSpinner = document.getElementById("dashboard-loading-spinner");
    const errorAlert = document.getElementById("dashboard-error-alert");
    const errorMessage = document.getElementById("dashboard-error-message");
    const btnRetry = document.getElementById("btn-retry-load");
    const emptyAlert = document.getElementById("dashboard-empty-alert");
    const mainContent = document.getElementById("dashboard-main-content");

    // Elemen KPI
    const kpiTotal = document.getElementById("kpi-total-tickets");
    const kpiActive = document.getElementById("kpi-active-tickets");
    const kpiCompleted = document.getElementById("kpi-completed-tickets");
    const kpiRate = document.getElementById("kpi-completion-rate");

    // Elemen Breakdown Status
    const countBaru = document.getElementById("kpi-count-baru");
    const countVerif = document.getElementById("kpi-count-terverifikasi");
    const countDiproses = document.getElementById("kpi-count-diproses");
    const countSelesai = document.getElementById("kpi-count-selesai");

    // Elemen Persentase & Progress Bar Status
    const pctBaru = document.getElementById("kpi-pct-baru");
    const pctVerif = document.getElementById("kpi-pct-terverifikasi");
    const pctDiproses = document.getElementById("kpi-pct-diproses");
    const pctSelesai = document.getElementById("kpi-pct-selesai");
    const progressBaru = document.getElementById("kpi-progress-baru");
    const progressVerif = document.getElementById("kpi-progress-terverifikasi");
    const progressDiproses = document.getElementById("kpi-progress-diproses");
    const progressSelesai = document.getElementById("kpi-progress-selesai");

    // Elemen Ruangan & Unverified
    const topRoomsList = document.getElementById("top-rooms-list");
    const unspecifiedRoomCount = document.getElementById("unspecified-room-count");
    const categoryUnverifiedCount = document.getElementById("category-unverified-count");
    const categoryVerifiedCount = document.getElementById("category-verified-count");
    const otherFloorsNote = document.getElementById("other-floors-note");
    const otherFloorsCount = document.getElementById("other-floors-count");
    const chartSummary = document.getElementById("dashboard-chart-summary");

    // Canvas Elemen
    const trendCanvas = document.getElementById("trendChart");
    const categoryCanvas = document.getElementById("categoryChart");
    const locationCanvas = document.getElementById("locationChart");

    // Instans Grafik Chart.js
    let trendChartInstance = null;
    let categoryChartInstance = null;
    let locationChartInstance = null;

    function getDesignToken(name, fallback) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function isReducedMotionPreferred() {
        return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function applyChartFontDefaults() {
        Chart.defaults.font.family = getDesignToken(
            "--kf-font-sans-serif",
            '"Public Sans", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
        );
    }

    // Palet Warna Kategori K1 s.d. K7
    const CATEGORY_PALETTE = [
        getDesignToken("--kf-primary", "#0c356a"), // K1 - Ruang kelas dan perabot (--kf-primary)
        getDesignToken("--kf-info", "#0284c7"), // K2 - Laboratorium dan perangkat (--kf-info)
        getDesignToken("--kf-primary-dark", "#082245"), // K3 - Jaringan dan internet (--kf-primary-dark)
        getDesignToken("--kf-success", "#059669"), // K4 - Kebersihan dan sanitasi (--kf-success)
        getDesignToken("--kf-warning", "#d97706"), // K5 - Listrik, AC, dan penerangan (--kf-warning)
        getDesignToken("--kf-text-muted", "#4b5563"), // K6 - Keamanan, parkir, dan akses (--kf-text-muted)
        getDesignToken("--kf-secondary", "#ffc436")  // K7 - Lainnya (--kf-secondary)
    ];

    // Palet Warna Lantai 1 s.d. 4
    const FLOOR_PALETTE = [
        getDesignToken("--kf-primary", "#0c356a"), // Lantai 1
        getDesignToken("--kf-primary-dark", "#082245"), // Lantai 2
        getDesignToken("--kf-info", "#0284c7"), // Lantai 3
        getDesignToken("--kf-text-muted", "#4b5563")  // Lantai 4
    ];

    /**
     * Membangun query string parameter dari nilai form aktif.
     */
    function getActiveFilterParams() {
        const params = new URLSearchParams();
        if (filterDays && filterDays.value) {
            params.set("days", filterDays.value);
        }
        if (filterCategory && filterCategory.value) {
            params.set("category", filterCategory.value);
        }
        if (filterFloor && filterFloor.value) {
            params.set("floor", filterFloor.value);
        }
        return params;
    }

    /**
     * Memperbarui teks ringkasan filter aktif.
     */
    function updateFilterSummary() {
        if (!filterSummaryText) return;
        const parts = [];
        const daysVal = filterDays ? filterDays.value : "30";
        parts.push(`${daysVal} hari terakhir`);

        if (filterCategory && filterCategory.value) {
            parts.push(`Kategori ${filterCategory.value}`);
        } else {
            parts.push("Semua Kategori");
        }

        if (filterFloor && filterFloor.value) {
            parts.push(`Lantai ${filterFloor.value}`);
        } else {
            parts.push("Semua Lantai");
        }

        filterSummaryText.textContent = parts.join(", ");
    }

    /**
     * Mengambil data agregat dari API dan memperbarui visualisasi dasbor.
     */
    function loadDashboardData() {
        const params = getActiveFilterParams();
        updateFilterSummary();

        // Tampilkan loading state
        if (loadingSpinner) loadingSpinner.classList.remove("d-none");
        if (errorAlert) errorAlert.classList.add("d-none");
        if (emptyAlert) emptyAlert.classList.add("d-none");
        if (mainContent) {
            mainContent.classList.add("is-loading");
            mainContent.style.opacity = "0.7";
            mainContent.setAttribute("aria-busy", "true");
        }

        const apiUrl = "/dashboard/api/chart-data?" + params.toString();

        fetch(apiUrl, {
            method: "GET",
            headers: {
                "Accept": "application/json"
            }
        })
            .then(function (response) {
                if (!response.ok) {
                    return response.json().then(function (errBody) {
                        throw new Error(errBody.message || "Gagal mengambil data dari server (" + response.status + ")");
                    }).catch(function (parseErr) {
                        throw new Error("Gagal mengambil data dari server (" + response.status + ")");
                    });
                }
                return response.json();
            })
            .then(function (data) {
                // Sembunyikan loading
                if (loadingSpinner) loadingSpinner.classList.add("d-none");
                if (mainContent) {
                    mainContent.classList.remove("is-loading");
                    mainContent.style.opacity = "1";
                    mainContent.setAttribute("aria-busy", "false");
                }

                renderKPI(data.kpi);
                renderCharts(data);
                renderTopRooms(data.location_chart);
                updateChartSummary(data);

                if (window.KlasifasToast) {
                    window.KlasifasToast.show("Data visualisasi dasbor diperbarui.", "info", 2500);
                }

                // Cek kondisi data kosong
                if (data.kpi && data.kpi.total_tickets === 0) {
                    if (emptyAlert) emptyAlert.classList.remove("d-none");
                } else {
                    if (emptyAlert) emptyAlert.classList.add("d-none");
                }
            })
            .catch(function (error) {
                if (loadingSpinner) loadingSpinner.classList.add("d-none");
                if (mainContent) {
                    mainContent.classList.remove("is-loading");
                    mainContent.style.opacity = "1";
                    mainContent.setAttribute("aria-busy", "false");
                }
                if (errorAlert) {
                    errorAlert.classList.remove("d-none");
                    if (errorMessage) {
                        errorMessage.textContent = error.message || "Terjadi kesalahan saat memuat data.";
                    }
                }
            });
    }

    /**
     * Menggerakkan angka secara halus (count-up/down) dari nilai lama ke nilai baru.
     */
    function animateNumber(element, end, duration, isPercentage) {
        if (!element) return;
        duration = duration || 450;
        isPercentage = isPercentage || false;

        const start = Number(element.dataset.currentValue) || 0;
        if (isReducedMotionPreferred() || start === end) {
            element.textContent = isPercentage ? end.toFixed(1) + "%" : Math.round(end).toLocaleString("id-ID");
            element.dataset.currentValue = end;
            return;
        }

        let startTime = null;
        function frame(timestamp) {
            if (!startTime) startTime = timestamp;
            const elapsed = timestamp - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const ease = 1 - Math.pow(1 - progress, 4); // easeOutQuart
            const current = start + (end - start) * ease;

            element.textContent = isPercentage ? current.toFixed(1) + "%" : Math.round(current).toLocaleString("id-ID");

            if (progress < 1) {
                window.requestAnimationFrame(frame);
            } else {
                element.dataset.currentValue = end;
            }
        }
        window.requestAnimationFrame(frame);
    }

    /**
     * Memperbarui jumlah, persentase, dan lebar segmen status.
     * Total 0 menghasilkan persentase dan lebar 0 tanpa pembagian nol.
     */
    function updateStatusShare(countEl, pctEl, progressEl, count, total) {
        if (countEl) animateNumber(countEl, count, 450, false);

        const percentage = total > 0 ? (count / total) * 100 : 0;
        if (pctEl) animateNumber(pctEl, percentage, 450, true);
        if (progressEl) progressEl.style.width = percentage.toFixed(4) + "%";
    }

    /**
     * Menyusun ringkasan teks grafik untuk pembaca layar.
     */
    function updateChartSummary(payload) {
        if (!chartSummary) return;

        const kpi = payload.kpi || {};
        const counts = kpi.status_counts || {};
        const parts = [
            "Total keluhan " + (kpi.total_tickets ?? 0) + ".",
            "Baru " + (counts.Baru ?? 0) +
                ", Terverifikasi " + (counts.Terverifikasi ?? 0) +
                ", Diproses " + (counts.Diproses ?? 0) +
                ", Selesai " + (counts.Selesai ?? 0) + ".",
            "Tingkat penyelesaian " + (kpi.completion_rate ?? 0) + " persen."
        ];

        const trendValues = (((payload.trend_chart || {}).datasets || [{}])[0] || {}).data || [];
        if (trendValues.length) {
            const trendTotal = trendValues.reduce(function (sum, value) {
                return sum + value;
            }, 0);
            parts.push("Tren " + trendValues.length + " hari dengan total " + trendTotal + " keluhan.");
        }

        const categoryChart = payload.category_chart || {};
        const categoryLabels = categoryChart.labels || [];
        const categoryValues = ((categoryChart.datasets || [{}])[0] || {}).data || [];
        if (categoryLabels.length) {
            parts.push("Kategori: " + categoryLabels.map(function (label, index) {
                return label + " " + (categoryValues[index] ?? 0);
            }).join(", ") + ".");
        }

        const locationChart = payload.location_chart || {};
        const locationLabels = locationChart.labels || [];
        const locationValues = ((locationChart.datasets || [{}])[0] || {}).data || [];
        if (locationLabels.length) {
            parts.push("Lokasi: " + locationLabels.map(function (label, index) {
                return label + " " + (locationValues[index] ?? 0);
            }).join(", ") + ".");
        }

        const otherFloors = locationChart.other_floors_count ?? 0;
        if (otherFloors > 0) {
            parts.push(otherFloors + " tiket di luar Lantai 1 sampai 4.");
        }

        chartSummary.textContent = parts.join(" ");
    }

    /**
     * Merender kartu metrik ringkasan (KPI).
     */
    function renderKPI(kpi) {
        if (!kpi) return;
        const total = kpi.total_tickets ?? 0;
        const counts = kpi.status_counts || {};

        if (kpiTotal) animateNumber(kpiTotal, total, 450, false);
        if (kpiActive) animateNumber(kpiActive, kpi.active_tickets ?? 0, 450, false);
        if (kpiCompleted) animateNumber(kpiCompleted, counts.Selesai ?? 0, 450, false);
        if (kpiRate) animateNumber(kpiRate, kpi.completion_rate ?? 0.0, 450, true);

        updateStatusShare(countBaru, pctBaru, progressBaru, counts.Baru ?? 0, total);
        updateStatusShare(countVerif, pctVerif, progressVerif, counts.Terverifikasi ?? 0, total);
        updateStatusShare(countDiproses, pctDiproses, progressDiproses, counts.Diproses ?? 0, total);
        updateStatusShare(countSelesai, pctSelesai, progressSelesai, counts.Selesai ?? 0, total);
    }

    /**
     * Merender dan memperbarui ketiga grafik Chart.js.
     */
    function renderCharts(payload) {
        if (typeof Chart === "undefined") {
            console.error("Pustaka Chart.js belum dimuat.");
            return;
        }

        applyChartFontDefaults();

        renderTrendChart(payload.trend_chart);
        renderCategoryChart(payload.category_chart);
        renderLocationChart(payload.location_chart);
    }

    /**
     * Merender grafik garis tren laporan masuk harian.
     */
    function renderTrendChart(trendData) {
        if (!trendCanvas || !trendData) return;

        const labels = trendData.labels || [];
        const dataValues = (trendData.datasets && trendData.datasets[0] && trendData.datasets[0].data) || [];
        const prefersReducedMotion = isReducedMotionPreferred();

        if (trendChartInstance) {
            trendChartInstance.data.labels = labels;
            trendChartInstance.data.datasets[0].data = dataValues;
            if (trendChartInstance.options.scales && trendChartInstance.options.scales.x && trendChartInstance.options.scales.x.ticks) {
                trendChartInstance.options.scales.x.ticks.maxTicksLimit = window.innerWidth < 576 ? 6 : 12;
            }
            trendChartInstance.update(prefersReducedMotion ? "none" : undefined);
        } else {
            const ctx = trendCanvas.getContext("2d");
            let gradient = null;
            if (ctx) {
                gradient = ctx.createLinearGradient(0, 0, 0, 300);
                gradient.addColorStop(0, "rgba(12, 53, 106, 0.22)");
                gradient.addColorStop(1, "rgba(12, 53, 106, 0.01)");
            }

            trendChartInstance = new Chart(trendCanvas, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Tiket Masuk",
                        data: dataValues,
                        borderColor: getDesignToken("--kf-primary", "#0c356a"),
                        backgroundColor: gradient || getDesignToken("--kf-primary-soft", "#e6eef9"),
                        fill: true,
                        tension: 0.35,
                        pointRadius: labels.length > 60 ? 1 : 3,
                        pointHoverRadius: 6,
                        pointBackgroundColor: getDesignToken("--kf-secondary", "#ffc436"),
                        pointBorderColor: getDesignToken("--kf-primary", "#0c356a"),
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: prefersReducedMotion ? false : { duration: 500, easing: "easeOutCubic" },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    return " " + ctx.parsed.y + " keluhan";
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                maxRotation: 45,
                                autoSkip: true,
                                maxTicksLimit: window.innerWidth < 576 ? 6 : 12,
                                font: { size: 11 }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0,
                                font: { size: 11 }
                            }
                        }
                    }
                }
            });
        }
    }

    /**
     * Merender diagram batang sebaran 7 kategori fasilitas resmi.
     */
    function renderCategoryChart(catData) {
        if (!categoryCanvas || !catData) return;

        const labels = catData.labels || [];
        const catNames = catData.category_names || [];
        const dataValues = (catData.datasets && catData.datasets[0] && catData.datasets[0].data) || [];
        const percentages = catData.percentages || [];

        if (categoryUnverifiedCount) {
            categoryUnverifiedCount.textContent = catData.unverified_count ?? 0;
        }
        if (categoryVerifiedCount) {
            categoryVerifiedCount.textContent = catData.total_verified ?? 0;
        }

        const tooltipLabel = function (ctx) {
            const percentage = percentages[ctx.dataIndex];
            const percentageText = (percentage === undefined || percentage === null)
                ? ""
                : " (" + percentage + "%)";
            return " " + ctx.parsed.y + " tiket terverifikasi" + percentageText;
        };

        const prefersReducedMotion = isReducedMotionPreferred();

        if (categoryChartInstance) {
            categoryChartInstance.data.labels = labels;
            categoryChartInstance.data.datasets[0].data = dataValues;
            categoryChartInstance.options.plugins.tooltip.callbacks.title = function (items) {
                if (!items.length) return "";
                const idx = items[0].dataIndex;
                return (labels[idx] || "") + " - " + (catNames[idx] || "");
            };
            categoryChartInstance.options.plugins.tooltip.callbacks.label = tooltipLabel;
            categoryChartInstance.update(prefersReducedMotion ? "none" : undefined);
        } else {
            categoryChartInstance = new Chart(categoryCanvas, {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Jumlah Tiket",
                        data: dataValues,
                        backgroundColor: CATEGORY_PALETTE,
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: prefersReducedMotion ? false : {
                        duration: 450,
                        easing: "easeOutQuart",
                        delay: function (ctx) {
                            return (ctx.type === "data" && ctx.mode === "default") ? ctx.dataIndex * 35 : 0;
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: function (items) {
                                    if (!items.length) return "";
                                    const idx = items[0].dataIndex;
                                    return (labels[idx] || "") + " - " + (catNames[idx] || "");
                                },
                                label: tooltipLabel
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 11, weight: "bold" } }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0,
                                font: { size: 11 }
                            }
                        }
                    }
                }
            });
        }
    }

    /**
     * Merender diagram batang sebaran keluhan per lantai gedung FTII.
     */
    function renderLocationChart(locData) {
        if (!locationCanvas || !locData) return;

        const labels = locData.labels || [];
        const dataValues = (locData.datasets && locData.datasets[0] && locData.datasets[0].data) || [];
        const otherFloors = locData.other_floors_count ?? 0;

        if (otherFloorsCount) {
            otherFloorsCount.textContent = otherFloors;
        }
        if (otherFloorsNote) {
            otherFloorsNote.classList.toggle("d-none", !(otherFloors > 0));
        }

        const prefersReducedMotion = isReducedMotionPreferred();

        if (locationChartInstance) {
            locationChartInstance.data.labels = labels;
            locationChartInstance.data.datasets[0].data = dataValues;
            locationChartInstance.update(prefersReducedMotion ? "none" : undefined);
        } else {
            locationChartInstance = new Chart(locationCanvas, {
                type: "bar",
                data: {
                    labels: labels,
                    datasets: [{
                        label: "Keluhan",
                        data: dataValues,
                        backgroundColor: FLOOR_PALETTE,
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: prefersReducedMotion ? false : {
                        duration: 450,
                        easing: "easeOutQuart",
                        delay: function (ctx) {
                            return (ctx.type === "data" && ctx.mode === "default") ? ctx.dataIndex * 35 : 0;
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    return " " + ctx.parsed.y + " keluhan fasilitas";
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 11 } }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0,
                                font: { size: 11 }
                            }
                        }
                    }
                }
            });
        }
    }

    /**
     * Merender daftar peringkat 5 ruangan dengan keluhan terbanyak.
     */
    function renderTopRooms(locData) {
        if (!topRoomsList || !locData) return;

        // Bersihkan daftar sebelumnya
        while (topRoomsList.firstChild) {
            topRoomsList.removeChild(topRoomsList.firstChild);
        }

        const topRooms = locData.top_rooms || [];
        if (topRooms.length === 0) {
            const emptyItem = document.createElement("li");
            emptyItem.className = "list-group-item text-secondary small py-2 px-0";
            emptyItem.textContent = "Tidak ada rekaman keluhan spesifik ruangan.";
            topRoomsList.appendChild(emptyItem);
        } else {
            topRooms.forEach(function (item, index) {
                const li = document.createElement("li");
                li.className = "list-group-item d-flex justify-content-between align-items-center py-2 px-0 border-bottom";

                const nameSpan = document.createElement("span");
                nameSpan.className = "small text-dark text-truncate d-inline-block";
                nameSpan.style.maxWidth = "70%";

                const badgeRank = document.createElement("span");
                badgeRank.className = "badge bg-light text-secondary border me-2";
                badgeRank.textContent = "#" + (index + 1);

                nameSpan.appendChild(badgeRank);
                nameSpan.appendChild(document.createTextNode(item.room_name || "Tanpa Nama"));

                const countBadge = document.createElement("span");
                countBadge.className = "badge bg-primary-subtle text-primary border px-2 py-1 small flex-shrink-0 ms-2";
                countBadge.textContent = (item.count || 0) + " keluhan";

                li.appendChild(nameSpan);
                li.appendChild(countBadge);
                topRoomsList.appendChild(li);
            });
        }

        if (unspecifiedRoomCount) {
            unspecifiedRoomCount.textContent = locData.unspecified_room_count ?? 0;
        }

        if (window.kfMotion && typeof window.kfMotion.refresh === "function") {
            window.kfMotion.refresh(topRoomsList);
        }
    }

    // Event Listener: Form Submit Filter
    if (filterForm) {
        filterForm.addEventListener("submit", function (e) {
            e.preventDefault();
            loadDashboardData();
        });
    }

    // Segmented Control Sync (P0.2)
    const segmentedButtons = document.querySelectorAll(".kf-segmented-btn");

    function syncSegmentedButtons(days) {
        segmentedButtons.forEach(function (btn) {
            const matches = btn.dataset.days === String(days);
            btn.classList.toggle("is-active", matches);
            btn.classList.toggle("active", matches);
        });
    }

    segmentedButtons.forEach(function (btn) {
        btn.addEventListener("click", function () {
            const days = btn.dataset.days;
            if (filterDays && days) {
                filterDays.value = days;
                syncSegmentedButtons(days);
                loadDashboardData();
            }
        });
    });

    if (filterDays) {
        filterDays.addEventListener("change", function () {
            syncSegmentedButtons(filterDays.value);
        });
    }

    // Event Listener: Reset Filter Button
    if (btnReset) {
        btnReset.addEventListener("click", function () {
            if (filterDays) filterDays.value = "30";
            if (filterCategory) filterCategory.value = "";
            if (filterFloor) filterFloor.value = "";
            syncSegmentedButtons("30");
            loadDashboardData();
        });
    }

    // Event Listener: Retry Button pada Error Alert
    if (btnRetry) {
        btnRetry.addEventListener("click", function () {
            loadDashboardData();
        });
    }

    // Inisialisasi awal saat halaman selesai dimuat
    loadDashboardData();
});

