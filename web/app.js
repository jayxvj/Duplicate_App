// IADCS Web UI Controller - Connected to Live Python Backend API
document.addEventListener('DOMContentLoaded', () => {
    // Application State
    const state = {
        totalApps: 0,
        totalSize: 0,
        reclaimableSize: 0,
        duplicateGroups: [],
        categories: [],
        quarantined: [],
        selectedAppIds: new Set(),
        isScanning: false
    };

    // Tab Navigation
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');

    const titles = {
        dashboard: { title: "System Overview", subtitle: "Content-based application discovery & deterministic SHA-256 deduplication" },
        scan: { title: "Scan Manager", subtitle: "Configure target directories, safety exclusions, and run multi-stage pipeline" },
        duplicates: { title: "Duplicate Applications Review", subtitle: "Compare content-matched groups and reclaim storage with 100% safety" },
        categories: { title: "Application Categories", subtitle: "Organized domains classified by deterministic rule engine" },
        quarantine: { title: "Safe Quarantine Vault", subtitle: "Isolated copies with complete one-click restoration manifests" },
        reports: { title: "Audit Reports & Verification", subtitle: "Machine-readable compliance records and SHA-256 hash logs" }
    };

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            navButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(t => t.classList.remove('active'));

            btn.classList.add('active');
            const targetEl = document.getElementById(`tab-${targetTab}`);
            if (targetEl) targetEl.classList.add('active');

            if (titles[targetTab]) {
                pageTitle.textContent = titles[targetTab].title;
                pageSubtitle.textContent = titles[targetTab].subtitle;
            }

            // Refresh tab-specific data
            if (targetTab === 'quarantine') loadQuarantine();
            if (targetTab === 'reports') loadReport();
            if (targetTab === 'duplicates') loadDuplicates();
            if (targetTab === 'dashboard') loadDashboard();
        });
    });

    // Helper: Format Bytes
    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return "0.0 B";
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // Helper: Toast Message
    function showToast(msg) {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3500);
    }

    // ── API: Load Dashboard Stats ──────────────────────────────
    async function loadDashboard() {
        try {
            const res = await fetch('/api/dashboard');
            if (!res.ok) throw new Error("API error");
            const data = await res.json();

            state.totalApps = data.totalApps || 0;
            state.totalSize = data.totalSize || 0;
            state.reclaimableSize = data.reclaimableSize || 0;
            state.categories = data.categories || [];

            // Update stats cards in UI if present
            const totalAppsEl = document.getElementById('stat-total-apps');
            if (totalAppsEl) totalAppsEl.textContent = state.totalApps;

            const reclaimEl = document.getElementById('stat-reclaimable');
            if (reclaimEl) reclaimEl.textContent = formatBytes(state.reclaimableSize);

            const dupCountEl = document.getElementById('stat-dup-groups');
            if (dupCountEl) dupCountEl.textContent = data.duplicateGroupsCount || 0;

            renderCategories();
        } catch (e) {
            console.warn("Backend API not reachable or empty, loading fallback data", e);
        }
    }

    // ── API: Load Duplicate Groups ─────────────────────────────
    async function loadDuplicates(filterText = "") {
        try {
            const res = await fetch('/api/duplicates');
            if (!res.ok) throw new Error("API error");
            const data = await res.json();
            state.duplicateGroups = data || [];
            renderDuplicates(filterText);
        } catch (e) {
            console.warn("Failed to fetch live duplicates", e);
            renderDuplicates(filterText);
        }
    }

    // ── API: Load Quarantine Vault ─────────────────────────────
    async function loadQuarantine() {
        try {
            const res = await fetch('/api/quarantine');
            if (!res.ok) throw new Error("API error");
            const data = await res.json();
            state.quarantined = data || [];
            renderQuarantine();
        } catch (e) {
            console.warn("Failed to fetch quarantine list", e);
            renderQuarantine();
        }
    }

    // ── API: Load Full Audit Report ────────────────────────────
    async function loadReport() {
        try {
            const res = await fetch('/api/report');
            if (!res.ok) throw new Error("API error");
            const data = await res.json();
            const viewer = document.getElementById('json-report-viewer');
            if (viewer) viewer.textContent = JSON.stringify(data, null, 2);
        } catch (e) {
            renderReport();
        }
    }

    // Render Categories
    function renderCategories() {
        const listEl = document.getElementById('category-list');
        if (listEl && state.categories.length > 0) {
            listEl.innerHTML = state.categories.map(c => `
                <div class="category-item">
                    <span>${c.name}</span>
                    <span class="badge badge-indigo">${c.count} applications</span>
                </div>
            `).join('');
        }

        const fullGrid = document.getElementById('full-categories-grid');
        if (fullGrid && state.categories.length > 0) {
            fullGrid.innerHTML = state.categories.map(c => `
                <div class="category-item" style="padding: 16px; margin-bottom: 8px;">
                    <div>
                        <strong style="font-size: 15px; color: #fff;">${c.name}</strong>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 2px;">Rule-based domain classification</p>
                    </div>
                    <span class="badge badge-indigo" style="font-size: 13px;">${c.count} apps</span>
                </div>
            `).join('');
        }
    }

    // Render Duplicate Groups
    function renderDuplicates(filterText = "") {
        const container = document.getElementById('duplicate-groups-list');
        if (!container) return;

        const filtered = state.duplicateGroups.filter(g => {
            if (!filterText) return true;
            return (g.name && g.name.toLowerCase().includes(filterText)) ||
                   (g.category && g.category.toLowerCase().includes(filterText));
        });

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="card" style="text-align: center; padding: 48px;">
                    <h3 style="color: #10b981; font-size: 18px; margin-bottom: 8px;">✓ No Duplicate Applications Found</h3>
                    <p style="color: #94a3b8;">Click "Start Full Pipeline Scan" to analyze target folders and discover content matches.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(grp => `
            <div class="dup-group-card">
                <div class="dup-header">
                    <div class="dup-title-row">
                        <span class="dup-app-title">📦 ${grp.name}</span>
                        <span class="badge badge-indigo">${grp.category || 'General'}</span>
                        <span class="badge badge-emerald">🔒 100% SHA-256 Match</span>
                    </div>
                    <div class="dup-meta-info">
                        <span>Total: ${formatBytes(grp.totalSize)}</span>
                        <span style="color: #10b981; font-weight: 700;">Reclaimable: ${formatBytes(grp.reclaimableSize)}</span>
                    </div>
                </div>
                <div class="dup-instances-table">
                    ${grp.instances.map(inst => `
                        <div class="instance-row">
                            <input type="checkbox" class="inst-checkbox" data-id="${inst.id}" data-path="${inst.path}" ${state.selectedAppIds.has(inst.id) ? 'checked' : ''}>
                            <span class="badge ${inst.isOriginal ? 'badge-emerald' : 'badge-amber'}">
                                ${inst.isOriginal ? 'ORIGINAL (KEEP)' : 'DUPLICATE (REMOVE)'}
                            </span>
                            <span class="instance-path" title="${inst.path}">${inst.path}</span>
                            <span class="instance-meta">${inst.size} • ${inst.date}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        // Reattach Checkbox Listeners
        document.querySelectorAll('.inst-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = parseInt(e.target.getAttribute('data-id'), 10) || e.target.getAttribute('data-id');
                if (e.target.checked) {
                    state.selectedAppIds.add(id);
                } else {
                    state.selectedAppIds.delete(id);
                }
                updateSummary();
            });
        });

        updateSummary();
    }

    function updateSummary() {
        const count = state.selectedAppIds.size;
        const summaryEl = document.getElementById('selection-summary');
        if (summaryEl) {
            summaryEl.innerHTML = `Selected: <strong>${count} redundant copies</strong>`;
        }
    }

    // Smart Selection Handlers
    document.getElementById('btn-auto-select')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        state.duplicateGroups.forEach(g => {
            g.instances.forEach((inst, idx) => {
                if (!inst.isOriginal || idx > 0) state.selectedAppIds.add(inst.id);
            });
        });
        renderDuplicates();
        showToast("Auto-selected all redundant duplicate instances while preserving originals!");
    });

    document.getElementById('btn-keep-newest')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        state.duplicateGroups.forEach(g => {
            const sorted = [...g.instances].sort((a,b) => (b.date || "").localeCompare(a.date || ""));
            sorted.forEach((inst, idx) => {
                if (idx > 0) state.selectedAppIds.add(inst.id);
            });
        });
        renderDuplicates();
        showToast("Selected older copies to keep the newest original!");
    });

    document.getElementById('btn-keep-oldest')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        state.duplicateGroups.forEach(g => {
            const sorted = [...g.instances].sort((a,b) => (a.date || "").localeCompare(b.date || ""));
            sorted.forEach((inst, idx) => {
                if (idx > 0) state.selectedAppIds.add(inst.id);
            });
        });
        renderDuplicates();
        showToast("Selected newer copies to keep the oldest original!");
    });

    document.getElementById('btn-deselect-all')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        renderDuplicates();
        showToast("Deselected all copies.");
    });

    document.getElementById('search-duplicates')?.addEventListener('input', (e) => {
        renderDuplicates(e.target.value.toLowerCase().trim());
    });

    // ── Live Backend Scan Execution ────────────────────────────
    const btnStartScan = document.getElementById('btn-start-scan');
    const scanStatusText = document.getElementById('scan-live-status');
    const progressFill = document.getElementById('progress-fill');

    async function triggerRealScan(targetPath = "") {
        if (state.isScanning) return;
        state.isScanning = true;
        if (btnStartScan) btnStartScan.disabled = true;

        if (scanStatusText) scanStatusText.textContent = "Connecting to backend scanner pipeline...";
        if (progressFill) progressFill.style.width = "15%";

        try {
            const scanResponse = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: targetPath })
            });

            if (!scanResponse.ok && scanResponse.status !== 409) {
                throw new Error("Failed to start scan");
            }

            // Poll backend scan status
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch('/api/scan/status');
                    const statusData = await statusRes.json();

                    if (scanStatusText) scanStatusText.textContent = statusData.stage || "Processing...";
                    if (progressFill) progressFill.style.width = `${statusData.progress || 25}%`;

                    if (!statusData.is_scanning) {
                        clearInterval(pollInterval);
                        state.isScanning = false;
                        if (btnStartScan) btnStartScan.disabled = false;
                        if (progressFill) progressFill.style.width = "100%";

                        showToast("✓ Scan completed! Database updated with latest results.");
                        await loadDashboard();
                        await loadDuplicates();
                    }
                } catch (err) {
                    console.error("Poll error", err);
                }
            }, 500);

        } catch (e) {
            console.error("Scan error", e);
            if (scanStatusText) scanStatusText.textContent = "Scan failed: " + e.message;
            state.isScanning = false;
            if (btnStartScan) btnStartScan.disabled = false;
        }
    }

    btnStartScan?.addEventListener('click', () => {
        const pathInput = document.getElementById('scan-path-input');
        const customPath = pathInput ? pathInput.value.trim() : "";
        triggerRealScan(customPath);
    });

    document.getElementById('btn-hero-scan')?.addEventListener('click', () => {
        document.querySelector('[data-tab="scan"]')?.click();
        triggerRealScan();
    });

    document.getElementById('btn-quick-scan-top')?.addEventListener('click', () => {
        document.querySelector('[data-tab="scan"]')?.click();
        triggerRealScan();
    });

    // Preset Chips
    document.querySelectorAll('.chip-btn').forEach(chip => {
        chip.addEventListener('click', () => {
            const preset = chip.getAttribute('data-preset');
            showToast(`Selected preset: ${preset}. Starting real scan...`);
            document.querySelector('[data-tab="scan"]')?.click();
            triggerRealScan();
        });
    });

    // ── Safe Quarantine Action via Backend ─────────────────────
    document.getElementById('btn-action-quarantine')?.addEventListener('click', async () => {
        if (state.selectedAppIds.size === 0) {
            showToast("Please select at least 1 duplicate copy first.");
            return;
        }

        const ids = Array.from(state.selectedAppIds);
        showToast("Sending quarantine request to backend...");

        try {
            const res = await fetch('/api/quarantine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_ids: ids })
            });
            const data = await res.json();

            showToast(`🛡️ Successfully quarantined ${data.quarantined_count || ids.length} applications safely.`);
            state.selectedAppIds.clear();
            await loadDuplicates();
            await loadDashboard();
            await loadQuarantine();
        } catch (e) {
            showToast("Quarantine operation failed: " + e.message);
        }
    });

    // Render Quarantined List
    function renderQuarantine() {
        const qList = document.getElementById('quarantine-list');
        if (!qList) return;

        if (state.quarantined.length === 0) {
            qList.innerHTML = `
                <div class="card" style="text-align: center; padding: 32px;">
                    <p style="color: #94a3b8;">Quarantine vault is currently empty.</p>
                </div>
            `;
            return;
        }

        qList.innerHTML = state.quarantined.map(q => `
            <div class="instance-row" style="padding: 14px; margin-bottom: 8px;">
                <span class="badge badge-emerald">QUARANTINED</span>
                <span style="font-weight: 700; color: #fff;">${q.app_name || q.name}</span>
                <span class="instance-path">${q.original_path || q.originalPath}</span>
                <span class="instance-meta">${formatBytes(q.total_size)} • ${q.quarantined_at || q.date || 'Recent'}</span>
                <button class="btn btn-secondary btn-restore" data-path="${q.original_path || q.originalPath}">↺ Restore</button>
            </div>
        `).join('');

        document.querySelectorAll('.btn-restore').forEach(btn => {
            btn.addEventListener('click', async () => {
                const p = btn.getAttribute('data-path');
                try {
                    await fetch('/api/restore', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ original_path: p })
                    });
                    showToast(`Restored application from quarantine!`);
                    await loadQuarantine();
                    await loadDuplicates();
                } catch (err) {
                    showToast("Restore failed: " + err.message);
                }
            });
        });
    }

    // Render JSON Report Viewer
    function renderReport() {
        const viewer = document.getElementById('json-report-viewer');
        if (!viewer) return;
        const reportData = {
            report_version: "1.0.0",
            generated_at: new Date().toISOString(),
            scan_engine: "Deterministic SHA-256 Multi-Stage",
            system_status: {
                total_applications: state.totalApps,
                duplicate_groups: state.duplicateGroups.length,
                reclaimable_bytes: state.reclaimableSize,
                safe_mode_enabled: true
            },
            groups: state.duplicateGroups
        };
        viewer.textContent = JSON.stringify(reportData, null, 2);
    }

    // Initial Data Fetch
    loadDashboard();
    loadDuplicates();
    loadQuarantine();
});
