// IADCS Sentinel - Obsidian Cyber-Glass Pro Client Controller
document.addEventListener('DOMContentLoaded', () => {
    // Application Reactive State
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

    // UI Elements
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');
    const navDupBadge = document.getElementById('nav-dup-badge');
    const navQuarBadge = document.getElementById('nav-quar-badge');

    const titles = {
        dashboard: { 
            title: "System Overview", 
            subtitle: "Content-based application discovery & deterministic SHA-256 deduplication" 
        },
        scan: { 
            title: "Scan Manager & Pipeline", 
            subtitle: "Configure target directories, safety exclusions, and run multi-stage pipeline" 
        },
        duplicates: { 
            title: "Duplicate Applications Review", 
            subtitle: "Compare content-matched groups and reclaim storage with 100% safety" 
        },
        categories: { 
            title: "Application Categories", 
            subtitle: "Organized domains classified by deterministic rule engine" 
        },
        quarantine: { 
            title: "Safe Quarantine Vault", 
            subtitle: "Isolated copies with complete one-click restoration manifests" 
        },
        reports: { 
            title: "Cryptographic Audit & Compliance", 
            subtitle: "Machine-readable compliance records and SHA-256 hash logs" 
        }
    };

    // Navigation Switcher
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

            // Lazy data sync for active tab
            if (targetTab === 'quarantine') loadQuarantine();
            if (targetTab === 'reports') loadReport();
            if (targetTab === 'duplicates') loadDuplicates();
            if (targetTab === 'dashboard') loadDashboard();
        });
    });

    // Helper: Format Bytes with high precision
    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return "0.0 B";
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Helper: Modern Toast Notifications
    function showToast(msg, icon = "ℹ️") {
        const toast = document.getElementById('toast');
        const toastMsg = document.getElementById('toast-msg');
        if (!toast || !toastMsg) return;
        toast.querySelector('.toast-icon').textContent = icon;
        toastMsg.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3800);
    }

    // ── API: Load Dashboard Metrics ─────────────────────────────
    async function loadDashboard() {
        try {
            const res = await fetch('/api/dashboard');
            if (!res.ok) throw new Error("Dashboard API returned status " + res.status);
            const data = await res.json();

            state.totalApps = data.totalApps || 0;
            state.totalSize = data.totalSize || 0;
            state.reclaimableSize = data.reclaimableSize || 0;
            state.categories = data.categories || [];

            // Update stats cards in UI
            const totalAppsEl = document.getElementById('stat-total-apps');
            if (totalAppsEl) totalAppsEl.textContent = state.totalApps;

            const dupCountEl = document.getElementById('stat-dup-groups');
            if (dupCountEl) dupCountEl.textContent = `${data.duplicateGroupsCount || 0} Groups`;

            const reclaimEl = document.getElementById('stat-reclaimable');
            if (reclaimEl) reclaimEl.textContent = formatBytes(state.reclaimableSize);

            const catEl = document.getElementById('stat-categories');
            if (catEl) catEl.textContent = `${state.categories.length} Active`;

            if (navDupBadge) navDupBadge.textContent = data.duplicateGroupsCount || 0;

            renderCategories();
        } catch (e) {
            console.warn("Backend API sync failed:", e);
        }
    }

    // ── API: Load Duplicate Groups ──────────────────────────────
    async function loadDuplicates(filterText = "") {
        try {
            const res = await fetch('/api/duplicates');
            if (!res.ok) throw new Error("Duplicates API error");
            const data = await res.json();
            state.duplicateGroups = data || [];

            if (navDupBadge) navDupBadge.textContent = state.duplicateGroups.length;
            const dupCopiesEl = document.getElementById('stat-dup-copies');
            if (dupCopiesEl) {
                const totalCopies = state.duplicateGroups.reduce((acc, g) => acc + (g.instances ? g.instances.length - 1 : 0), 0);
                dupCopiesEl.textContent = `${totalCopies} redundant instances`;
            }

            renderDuplicates(filterText);
        } catch (e) {
            console.warn("Failed to fetch live duplicates:", e);
            renderDuplicates(filterText);
        }
    }

    // ── API: Load Quarantine Vault ──────────────────────────────
    async function loadQuarantine() {
        try {
            const res = await fetch('/api/quarantine');
            if (!res.ok) throw new Error("Quarantine API error");
            const data = await res.json();
            state.quarantined = data || [];
            if (navQuarBadge) navQuarBadge.textContent = state.quarantined.length;
            renderQuarantine();
        } catch (e) {
            console.warn("Failed to fetch quarantine vault:", e);
            renderQuarantine();
        }
    }

    // ── API: Load Report Data ───────────────────────────────────
    async function loadReport() {
        try {
            const res = await fetch('/api/report');
            if (!res.ok) throw new Error("Report API error");
            const data = await res.json();
            const viewer = document.getElementById('json-report-viewer');
            if (viewer) viewer.textContent = JSON.stringify(data, null, 2);
        } catch (e) {
            console.warn("Failed to fetch JSON report", e);
        }
    }

    // Render Categories in Dashboard and Full Grid
    function renderCategories() {
        const listEl = document.getElementById('category-list');
        if (listEl) {
            if (state.categories.length === 0) {
                listEl.innerHTML = `<div class="empty-state-sm">No applications classified yet. Run a scan to discover applications.</div>`;
            } else {
                listEl.innerHTML = state.categories.map(c => `
                    <div class="category-item">
                        <span style="font-weight: 600; color: #fff;">${c.name}</span>
                        <span class="badge badge-indigo">${c.count} applications</span>
                    </div>
                `).join('');
            }
        }

        const fullGrid = document.getElementById('full-categories-grid');
        if (fullGrid) {
            if (state.categories.length === 0) {
                fullGrid.innerHTML = `<div class="empty-state-sm" style="grid-column: span 3;">No categories available yet.</div>`;
            } else {
                fullGrid.innerHTML = state.categories.map(c => `
                    <div class="category-item" style="padding: 20px; flex-direction: column; align-items: flex-start; gap: 10px;">
                        <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                            <strong style="font-size: 16px; color: #fff;">${c.name}</strong>
                            <span class="badge badge-indigo">${c.count} apps</span>
                        </div>
                        <p style="color: #94a3b8; font-size: 12px; margin: 0;">Automated rule classification domain</p>
                    </div>
                `).join('');
            }
        }
    }

    // Render Duplicate Groups Review Cards
    function renderDuplicates(filterText = "") {
        const container = document.getElementById('duplicate-groups-list');
        if (!container) return;

        const filtered = state.duplicateGroups.filter(g => {
            if (!filterText) return true;
            const q = filterText.toLowerCase();
            return (g.name && g.name.toLowerCase().includes(q)) ||
                   (g.category && g.category.toLowerCase().includes(q)) ||
                   (g.instances && g.instances.some(i => i.path && i.path.toLowerCase().includes(q)));
        });

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="card empty-card glass-card">
                    <div class="empty-icon">✓</div>
                    <h3>No Duplicate Applications Found</h3>
                    <p>All tracked application packages are unique or no records match your filter criteria.</p>
                </div>
            `;
            updateSummary();
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
                        <span>Group Size: <strong>${formatBytes(grp.totalSize)}</strong></span>
                        <span style="color: #34d399; font-weight: 700;">Reclaimable: ${formatBytes(grp.reclaimableSize)}</span>
                    </div>
                </div>
                <div class="dup-instances-table">
                    ${grp.instances.map(inst => `
                        <div class="instance-row">
                            <input type="checkbox" class="inst-checkbox" data-id="${inst.id}" data-path="${inst.path}" ${state.selectedAppIds.has(inst.id) ? 'checked' : ''}>
                            <span class="badge ${inst.isOriginal ? 'badge-emerald' : 'badge-amber'}">
                                ${inst.isOriginal ? 'PROTECTED (ORIGINAL)' : 'DUPLICATE (REMOVE)'}
                            </span>
                            <span class="instance-path" title="${inst.path}">${inst.path}</span>
                            <span class="instance-meta">${inst.size} • ${inst.date}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        // Reattach Checkbox Event Listeners
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
            if (g.instances) {
                g.instances.forEach((inst, idx) => {
                    if (!inst.isOriginal || idx > 0) state.selectedAppIds.add(inst.id);
                });
            }
        });
        renderDuplicates();
        showToast(`Auto-selected ${state.selectedAppIds.size} duplicate copies while preserving originals!`, "⚡");
    });

    document.getElementById('btn-keep-newest')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        state.duplicateGroups.forEach(g => {
            if (g.instances) {
                const sorted = [...g.instances].sort((a,b) => (b.date || "").localeCompare(a.date || ""));
                sorted.forEach((inst, idx) => {
                    if (idx > 0) state.selectedAppIds.add(inst.id);
                });
            }
        });
        renderDuplicates();
        showToast("Selected older copies to preserve the newest installation.", "⏱️");
    });

    document.getElementById('btn-keep-oldest')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        state.duplicateGroups.forEach(g => {
            if (g.instances) {
                const sorted = [...g.instances].sort((a,b) => (a.date || "").localeCompare(b.date || ""));
                sorted.forEach((inst, idx) => {
                    if (idx > 0) state.selectedAppIds.add(inst.id);
                });
            }
        });
        renderDuplicates();
        showToast("Selected newer copies to preserve the oldest original.", "🕰️");
    });

    document.getElementById('btn-deselect-all')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        renderDuplicates();
        showToast("Cleared all selections.", "✕");
    });

    // Real-time Search input
    document.getElementById('search-duplicates')?.addEventListener('input', (e) => {
        renderDuplicates(e.target.value.toLowerCase().trim());
    });

    // ── Live Multi-Stage Scan Pipeline ──────────────────────────
    const btnStartScan = document.getElementById('btn-start-scan');
    const scanStatusText = document.getElementById('scan-live-status');
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const steps = [
        document.getElementById('step-1'),
        document.getElementById('step-2'),
        document.getElementById('step-3'),
        document.getElementById('step-4')
    ];

    function updateStepVisualizer(pct) {
        if (progressFill) progressFill.style.width = `${pct}%`;
        if (progressPercent) progressPercent.textContent = `${pct}%`;

        steps.forEach((s, idx) => {
            if (!s) return;
            const threshold = (idx + 1) * 25;
            if (pct >= threshold) {
                s.classList.remove('active');
                s.classList.add('completed');
            } else if (pct >= threshold - 24) {
                s.classList.add('active');
                s.classList.remove('completed');
            } else {
                s.classList.remove('active', 'completed');
            }
        });
    }

    async function triggerRealScan(targetPath = "") {
        if (state.isScanning) return;
        state.isScanning = true;
        if (btnStartScan) btnStartScan.disabled = true;

        updateStepVisualizer(15);
        if (scanStatusText) scanStatusText.textContent = "Connecting to pipeline engine and indexing packages...";

        try {
            const scanResponse = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: targetPath })
            });

            if (!scanResponse.ok && scanResponse.status !== 409) {
                throw new Error("Pipeline initialization failed");
            }

            // Poll real-time progress from backend
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch('/api/scan/status');
                    const statusData = await statusRes.json();

                    if (scanStatusText) scanStatusText.textContent = statusData.stage || "Processing...";
                    const pct = statusData.progress || 35;
                    updateStepVisualizer(pct);

                    if (!statusData.is_scanning) {
                        clearInterval(pollInterval);
                        state.isScanning = false;
                        if (btnStartScan) btnStartScan.disabled = false;
                        updateStepVisualizer(100);

                        showToast("Scan finished successfully! Duplicate database updated.", "✓");
                        await loadDashboard();
                        await loadDuplicates();
                    }
                } catch (err) {
                    console.error("Poll status error", err);
                }
            }, 450);

        } catch (e) {
            console.error("Scan error", e);
            if (scanStatusText) scanStatusText.textContent = "Scan error: " + e.message;
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

    document.getElementById('btn-hero-custom')?.addEventListener('click', () => {
        document.querySelector('[data-tab="scan"]')?.click();
        const input = document.getElementById('scan-path-input');
        if (input) input.focus();
    });

    document.getElementById('btn-quick-scan-top')?.addEventListener('click', () => {
        document.querySelector('[data-tab="scan"]')?.click();
        triggerRealScan();
    });

    document.getElementById('btn-refresh-data')?.addEventListener('click', async () => {
        showToast("Synchronizing system state...", "🔄");
        await loadDashboard();
        await loadDuplicates();
        await loadQuarantine();
        showToast("System state synchronized.", "✓");
    });

    // Preset Target Chips
    document.querySelectorAll('.preset-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const preset = chip.getAttribute('data-preset');
            const pathInput = document.getElementById('scan-path-input');
            let targetPath = "";

            if (preset === 'sample_apps') targetPath = "";
            else if (preset === 'downloads') targetPath = "C:\\Users\\" + (window.location.pathname.split('/')[2] || 'User') + "\\Downloads";
            else if (preset === 'program_files') targetPath = "C:\\Program Files";

            if (pathInput) pathInput.value = targetPath;
            showToast(`Target set to ${preset}. Starting scan...`, "📂");
            document.querySelector('[data-tab="scan"]')?.click();
            triggerRealScan(targetPath);
        });
    });

    // Browse Folder Simulation
    document.getElementById('btn-browse-path')?.addEventListener('click', () => {
        const pathInput = document.getElementById('scan-path-input');
        const suggested = prompt("Enter full folder path to scan (or leave blank for sample_apps):", pathInput ? pathInput.value : "");
        if (suggested !== null && pathInput) {
            pathInput.value = suggested.trim();
        }
    });

    // ── Safe Quarantine Action ──────────────────────────────────
    document.getElementById('btn-action-quarantine')?.addEventListener('click', async () => {
        if (state.selectedAppIds.size === 0) {
            showToast("Please select at least 1 duplicate instance to quarantine.", "⚠️");
            return;
        }

        const ids = Array.from(state.selectedAppIds);
        showToast(`Quarantining ${ids.length} selected items safely...`, "🛡️");

        try {
            const res = await fetch('/api/quarantine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_ids: ids })
            });
            const data = await res.json();

            showToast(`Safely quarantined ${data.quarantined_count || ids.length} application copies. Space reclaimed!`, "✓");
            state.selectedAppIds.clear();
            await loadDuplicates();
            await loadDashboard();
            await loadQuarantine();
        } catch (e) {
            showToast("Quarantine failed: " + e.message, "✕");
        }
    });

    // Render Quarantined List with 1-Click Restore
    function renderQuarantine() {
        const qList = document.getElementById('quarantine-list');
        if (!qList) return;

        if (state.quarantined.length === 0) {
            qList.innerHTML = `
                <div class="card empty-card glass-card">
                    <div class="empty-icon">🛡️</div>
                    <h3>Quarantine Vault is Clean</h3>
                    <p>No application instances are currently in quarantine. Use the Duplicate Review tab to safely isolate redundant files.</p>
                </div>
            `;
            return;
        }

        qList.innerHTML = state.quarantined.map(q => `
            <div class="instance-row" style="padding: 16px; margin-bottom: 10px;">
                <span class="badge badge-emerald">QUARANTINED</span>
                <strong style="color: #fff; font-size: 14px;">${q.app_name || q.name || 'Application'}</strong>
                <span class="instance-path" style="margin-left: 10px;" title="${q.original_path || q.originalPath}">${q.original_path || q.originalPath}</span>
                <span class="instance-meta">${formatBytes(q.total_size)} • ${q.quarantined_at || q.date || 'Recent'}</span>
                <button class="btn btn-secondary btn-sm btn-restore-vault" data-path="${q.original_path || q.originalPath}">↺ Restore Application</button>
            </div>
        `).join('');

        document.querySelectorAll('.btn-restore-vault').forEach(btn => {
            btn.addEventListener('click', async () => {
                const path = btn.getAttribute('data-path');
                try {
                    showToast("Restoring application from vault...", "↺");
                    const res = await fetch('/api/restore', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ original_path: path })
                    });
                    const resData = await res.json();
                    if (resData.status === "restored") {
                        showToast(`Restored "${path}" successfully!`, "✓");
                        await loadQuarantine();
                        await loadDuplicates();
                        await loadDashboard();
                    } else {
                        showToast("Restore failed: Target path already exists.", "✕");
                    }
                } catch (err) {
                    showToast("Restore error: " + err.message, "✕");
                }
            });
        });
    }

    // ── Export JSON Report ──────────────────────────────────────
    document.getElementById('btn-download-report')?.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/report');
            const data = await res.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `iadcs_compliance_report_${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast("Report downloaded successfully!", "📥");
        } catch (e) {
            showToast("Failed to download report", "✕");
        }
    });

    // View All Categories shortcut
    document.getElementById('btn-view-all-cats')?.addEventListener('click', () => {
        document.querySelector('[data-tab="categories"]')?.click();
    });

    // Initialize System State
    loadDashboard();
    loadDuplicates();
    loadQuarantine();
});
