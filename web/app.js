// IADCS Web UI Controller - Stitch Obsidian Logic Edition
document.addEventListener('DOMContentLoaded', () => {
    // Mock State
    const state = {
        totalApps: 28,
        duplicateGroups: [
            {
                id: 1,
                name: "Node.js JavaScript Runtime (v20.10.0)",
                category: "Development",
                totalSize: 452000000,
                reclaimableSize: 226000000,
                instances: [
                    { id: 101, path: "C:\\Program Files\\nodejs", isOriginal: true, size: "226 MB", date: "2026-08-10" },
                    { id: 102, path: "D:\\Backups\\Programs\\nodejs_old", isOriginal: false, size: "226 MB", date: "2026-06-15" }
                ]
            },
            {
                id: 2,
                name: "VLC Media Player",
                category: "Media",
                totalSize: 180000000,
                reclaimableSize: 120000000,
                instances: [
                    { id: 201, path: "C:\\Program Files\\VideoLAN\\VLC", isOriginal: true, size: "60 MB", date: "2026-08-01" },
                    { id: 202, path: "D:\\Downloads\\vlc_portable", isOriginal: false, size: "60 MB", date: "2026-05-20" },
                    { id: 203, path: "D:\\SoftwareArchive\\VLC_Player", isOriginal: false, size: "60 MB", date: "2026-04-12" }
                ]
            },
            {
                id: 3,
                name: "PostgreSQL 16 Enterprise Database",
                category: "Database",
                totalSize: 1240000000,
                reclaimableSize: 620000000,
                instances: [
                    { id: 301, path: "C:\\Program Files\\PostgreSQL\\16", isOriginal: true, size: "620 MB", date: "2026-07-22" },
                    { id: 302, path: "E:\\DevTools\\PostgreSQL_16_Copy", isOriginal: false, size: "620 MB", date: "2026-05-18" }
                ]
            }
        ],
        categories: [
            { name: "Development", count: 11 },
            { name: "Database", count: 5 },
            { name: "Media", count: 4 },
            { name: "Utilities", count: 4 },
            { name: "Communication", count: 2 },
            { name: "System Software", count: 2 }
        ],
        quarantined: [
            { name: "DevApp_v1", originalPath: "D:\\Backups\\DevApp", date: "2026-08-29 14:02", size: "14.2 MB" }
        ],
        selectedAppIds: new Set([102, 202, 203, 302])
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
        });
    });

    // Render Dashboard Categories
    function renderCategories() {
        const listEl = document.getElementById('category-list');
        if (!listEl) return;
        listEl.innerHTML = state.categories.map(c => `
            <div class="category-item">
                <span>${c.name}</span>
                <span class="badge badge-indigo">${c.count} applications</span>
            </div>
        `).join('');

        const fullGrid = document.getElementById('full-categories-grid');
        if (fullGrid) {
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
            return g.name.toLowerCase().includes(filterText) || g.category.toLowerCase().includes(filterText);
        });

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="card" style="text-align: center; padding: 48px;">
                    <h3 style="color: #10b981; font-size: 18px; margin-bottom: 8px;">🎉 No Duplicate Applications Found</h3>
                    <p style="color: #94a3b8;">All tracked applications are unique or no items match your current filter.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = filtered.map(grp => `
            <div class="dup-group-card">
                <div class="dup-header">
                    <div class="dup-title-row">
                        <span class="dup-app-title">📦 ${grp.name}</span>
                        <span class="badge badge-indigo">${grp.category}</span>
                        <span class="badge badge-emerald">✓ 100% SHA-256 Match</span>
                    </div>
                    <div class="dup-meta-info">
                        <span>Total: ${(grp.totalSize / (1024*1024)).toFixed(0)} MB</span>
                        <span style="color: #10b981; font-weight: 700;">Reclaimable: ${(grp.reclaimableSize / (1024*1024)).toFixed(0)} MB</span>
                    </div>
                </div>
                <div class="dup-instances-table">
                    ${grp.instances.map(inst => `
                        <div class="instance-row">
                            <input type="checkbox" class="inst-checkbox" data-id="${inst.id}" ${state.selectedAppIds.has(inst.id) ? 'checked' : ''}>
                            <span class="badge ${inst.isOriginal ? 'badge-emerald' : 'badge-amber'}">
                                ${inst.isOriginal ? 'ORIGINAL (KEEP)' : 'DUPLICATE (REMOVE)'}
                            </span>
                            <span class="instance-path">${inst.path}</span>
                            <span class="instance-meta">${inst.size} • ${inst.date}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        // Reattach Checkbox Listeners
        document.querySelectorAll('.inst-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = parseInt(e.target.getAttribute('data-id'), 10);
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
            summaryEl.innerHTML = `Selected: <strong>${count} redundant copies (~${(count * 210).toFixed(0)} MB)</strong>`;
        }
    }

    // Smart Selection Handlers
    document.getElementById('btn-auto-select')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        state.duplicateGroups.forEach(g => {
            g.instances.forEach((inst, idx) => {
                if (idx > 0) state.selectedAppIds.add(inst.id);
            });
        });
        renderDuplicates();
        showToast("Auto-selected all duplicate instances while preserving originals!");
    });

    document.getElementById('btn-keep-newest')?.addEventListener('click', () => {
        state.selectedAppIds.clear();
        state.duplicateGroups.forEach(g => {
            const sorted = [...g.instances].sort((a,b) => b.date.localeCompare(a.date));
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
            const sorted = [...g.instances].sort((a,b) => a.date.localeCompare(b.date));
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

    // Search input
    document.getElementById('search-duplicates')?.addEventListener('input', (e) => {
        renderDuplicates(e.target.value.toLowerCase().trim());
    });

    // Scan Simulation
    const btnStartScan = document.getElementById('btn-start-scan');
    const scanStatusText = document.getElementById('scan-live-status');
    const progressFill = document.getElementById('progress-fill');

    function simulateScan() {
        if (!btnStartScan) return;
        btnStartScan.disabled = true;
        let progress = 0;
        const phases = [
            { p: 25, label: "Phase 1: Discovering application packages..." },
            { p: 55, label: "Phase 2: Calculating multi-stage SHA-256 fingerprints..." },
            { p: 85, label: "Phase 3: Classifying application categories..." },
            { p: 100, label: "Phase 4: Complete! Verified duplicate groups." }
        ];

        let phaseIndex = 0;
        const interval = setInterval(() => {
            if (phaseIndex < phases.length) {
                progress = phases[phaseIndex].p;
                scanStatusText.textContent = phases[phaseIndex].label;
                progressFill.style.width = `${progress}%`;
                phaseIndex++;
            } else {
                clearInterval(interval);
                btnStartScan.disabled = false;
                showToast("Multi-stage scan completed successfully!");
            }
        }, 600);
    }

    btnStartScan?.addEventListener('click', simulateScan);
    document.getElementById('btn-hero-scan')?.addEventListener('click', () => {
        document.querySelector('[data-tab="scan"]')?.click();
        simulateScan();
    });
    document.getElementById('btn-quick-scan-top')?.addEventListener('click', () => {
        document.querySelector('[data-tab="scan"]')?.click();
        simulateScan();
    });

    // Preset Chips
    document.querySelectorAll('.chip-btn').forEach(chip => {
        chip.addEventListener('click', () => {
            const preset = chip.getAttribute('data-preset');
            showToast(`Selected preset: ${preset}. Starting scan...`);
            document.querySelector('[data-tab="scan"]')?.click();
            simulateScan();
        });
    });

    // Safe Quarantine Action
    document.getElementById('btn-action-quarantine')?.addEventListener('click', () => {
        if (state.selectedAppIds.size === 0) {
            showToast("Please select at least 1 duplicate copy first.");
            return;
        }
        showToast(`🛡️ Successfully quarantined ${state.selectedAppIds.size} applications safely.`);
        state.selectedAppIds.clear();
        renderDuplicates();
    });

    // Toast Function
    function showToast(msg) {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3500);
    }

    // Render Quarantined List
    function renderQuarantine() {
        const qList = document.getElementById('quarantine-list');
        if (!qList) return;
        qList.innerHTML = state.quarantined.map(q => `
            <div class="instance-row" style="padding: 14px; margin-bottom: 8px;">
                <span class="badge badge-emerald">QUARANTINED</span>
                <span style="font-weight: 700; color: #fff;">${q.name}</span>
                <span class="instance-path">${q.originalPath}</span>
                <span class="instance-meta">${q.size} • ${q.date}</span>
                <button class="btn btn-secondary" onclick="alert('Restored ${q.name} safely!')">↩ Restore</button>
            </div>
        `).join('');
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
                reclaimable_bytes: 4820000000,
                safe_mode_enabled: true,
                protected_directories: ["C:\\Windows", "C:\\Windows\\System32"]
            },
            groups: state.duplicateGroups
        };
        viewer.textContent = JSON.stringify(reportData, null, 2);
    }

    // Initial Renders
    renderCategories();
    renderDuplicates();
    renderQuarantine();
    renderReport();
});
