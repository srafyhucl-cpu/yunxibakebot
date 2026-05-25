(function () {
  const page = document.getElementById("knowledge-page");
  if (!page) {
    return;
  }

  const token = page.dataset.apiToken || "";
  const state = {
    page: 1,
    editingId: null,
    entries: [],
  };

  const els = {
    tableBody: document.getElementById("knowledge-table-body"),
    total: document.getElementById("knowledge-total"),
    pagination: document.getElementById("knowledge-pagination"),
    drawer: document.getElementById("knowledge-drawer"),
    drawerTitle: document.getElementById("drawer-title"),
    drawerSubtitle: document.getElementById("drawer-subtitle"),
    createButton: document.getElementById("create-entry"),
    closeButton: document.getElementById("drawer-close"),
    cancelButton: document.getElementById("drawer-cancel"),
    saveButton: document.getElementById("drawer-save"),
    retryButton: document.getElementById("retry-sync"),
    drawerMask: document.getElementById("knowledge-drawer-mask"),
    historyList: document.getElementById("history-list"),
    suggestedLabel: document.getElementById("suggested-label"),
    suggestedReason: document.getElementById("suggested-reason"),
    syncStatusPill: document.getElementById("sync-status-pill"),
    syncSpinner: document.getElementById("sync-spinner"),
    syncSyncedAt: document.getElementById("sync-synced-at"),
    syncError: document.getElementById("sync-error"),
    syncRetryCount: document.getElementById("sync-retry-count"),
    filters: {
      contentType: document.getElementById("filter-content-type"),
      active: document.getElementById("filter-active"),
      vectorStatus: document.getElementById("filter-vector-status"),
      keyword: document.getElementById("filter-keyword"),
      apply: document.getElementById("filter-apply"),
    },
    form: {
      title: document.getElementById("entry-title"),
      contentType: document.getElementById("entry-content-type"),
      content: document.getElementById("entry-content"),
      keywords: document.getElementById("entry-keywords"),
      priority: document.getElementById("entry-priority"),
      isActive: document.getElementById("entry-is-active"),
      errors: {
        title: document.getElementById("error-title"),
        contentType: document.getElementById("error-content-type"),
        content: document.getElementById("error-content"),
      },
    },
  };

  function authHeaders() {
    return {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + token,
    };
  }

  function showError(message) {
    if (window.showToast) {
      window.showToast(message, "error");
    }
  }

  function showSuccess(message) {
    if (window.showToast) {
      window.showToast(message, "success");
    }
  }

  function clearErrors() {
    Object.values(els.form.errors).forEach(function (node) {
      node.textContent = "";
    });
  }

  function openDrawer() {
    els.drawer.classList.add("is-open");
    els.drawer.setAttribute("aria-hidden", "false");
  }

  function closeDrawer() {
    els.drawer.classList.remove("is-open");
    els.drawer.setAttribute("aria-hidden", "true");
    state.editingId = null;
    clearErrors();
  }

  function resetDrawer() {
    state.editingId = null;
    els.drawerTitle.textContent = "新建内容";
    els.drawerSubtitle.textContent = "保存后会自动同步到 AI 向量检索。";
    els.form.title.value = "";
    els.form.contentType.value = "";
    els.form.content.value = "";
    els.form.keywords.value = "";
    els.form.priority.value = 50;
    els.form.isActive.checked = true;
    renderSuggestion({ label: "待分析", reason: "填写标题和正文后会给出建议分类。" });
    renderSyncState({ vector_sync_status: "pending", vector_synced_at: "", vector_sync_error: "", vector_sync_retry_count: 0 });
    renderHistory([]);
    els.retryButton.disabled = true;
    clearErrors();
  }

  function renderSuggestion(data) {
    els.suggestedLabel.textContent = data.label || "待分析";
    els.suggestedReason.textContent = data.reason || "暂无建议";
  }

  function renderSyncState(entry) {
    const statusMap = {
      success: { label: "已入向量", cls: "status-pill--success", loading: false },
      syncing: { label: "同步中", cls: "status-pill--syncing", loading: true },
      failed: { label: "同步失败", cls: "status-pill--failed", loading: false },
      pending: { label: "未同步", cls: "status-pill--pending", loading: false },
    };
    const current = statusMap[entry.vector_sync_status] || statusMap.pending;
    els.syncStatusPill.className = "status-pill " + current.cls;
    els.syncStatusPill.textContent = current.label;
    els.syncSpinner.hidden = !current.loading;
    els.syncSyncedAt.textContent = entry.vector_synced_at || "-";
    els.syncError.textContent = entry.vector_sync_error || "-";
    els.syncRetryCount.textContent = String(entry.vector_sync_retry_count || 0);
    els.retryButton.disabled = !state.editingId;
  }

  function renderHistory(history) {
    if (!history.length) {
      els.historyList.innerHTML = '<div class="history-empty">保存后会在这里看到修改记录。</div>';
      return;
    }
    els.historyList.innerHTML = history.map(function (item) {
      const summary = item.summary || {};
      const operator = summary.operator || "admin";
      const syncedAt = summary.synced_at || "-";
      const errorMessage = item.error_message || summary.error_message || "-";
      return (
        '<article class="history-item">' +
          '<div class="history-item__head">' +
            '<strong>' + escapeHtml(actionLabel(item.action)) + '</strong>' +
            '<span class="status-pill ' + statusClass(item.status) + '">' + escapeHtml(statusLabel(item.status)) + '</span>' +
          '</div>' +
          '<p class="history-meta">' + escapeHtml(item.occurred_at) + " · 操作人: " + escapeHtml(operator) + '</p>' +
          '<p>同步时间: ' + escapeHtml(syncedAt) + '</p>' +
          '<p>失败原因: ' + escapeHtml(errorMessage) + '</p>' +
        '</article>'
      );
    }).join("");
  }

  function statusLabel(status) {
    const labels = {
      success: "成功",
      failed: "失败",
      pending: "未同步",
      syncing: "同步中",
    };
    return labels[status] || status;
  }

  function statusClass(status) {
    const classes = {
      success: "status-pill--success",
      failed: "status-pill--failed",
      pending: "status-pill--pending",
      syncing: "status-pill--syncing",
    };
    return classes[status] || "status-pill--pending";
  }

  function actionLabel(action) {
    const labels = {
      create: "新建",
      update: "编辑",
      activate: "启用",
      deactivate: "停用",
      sync_retry: "重新同步",
    };
    return labels[action] || action;
  }

  function contentTypeLabel(contentType) {
    const labels = {
      faq: "常见问答",
      rule: "门店规则",
      script: "回复话术",
    };
    return labels[contentType] || contentType;
  }

  function activeLabel(isActive) {
    return isActive ? "启用中" : "已停用";
  }

  function vectorLabel(status) {
    const labels = {
      success: "已入向量",
      syncing: "同步中",
      failed: "同步失败",
      pending: "未同步",
    };
    return labels[status] || status;
  }

  function vectorClass(status) {
    const classes = {
      success: "status-pill--success",
      syncing: "status-pill--syncing",
      failed: "status-pill--failed",
      pending: "status-pill--pending",
    };
    return classes[status] || "status-pill--pending";
  }

  function buildFilters() {
    const params = new URLSearchParams();
    params.set("page", String(state.page));
    if (els.filters.contentType.value) {
      params.set("content_type", els.filters.contentType.value);
    }
    if (els.filters.active.value) {
      params.set("is_active", els.filters.active.value);
    }
    if (els.filters.vectorStatus.value) {
      params.set("vector_status", els.filters.vectorStatus.value);
    }
    if (els.filters.keyword.value.trim()) {
      params.set("keyword", els.filters.keyword.value.trim());
    }
    return params;
  }

  async function loadEntries() {
    els.tableBody.innerHTML = '<tr><td colspan="7" class="knowledge-empty">正在加载内容...</td></tr>';
    const response = await fetch("/api/v1/admin/knowledge-config/entries?" + buildFilters().toString(), {
      headers: authHeaders(),
      credentials: "same-origin",
    });
    if (!response.ok) {
      showError("内容列表加载失败");
      return;
    }
    const payload = await response.json();
    state.entries = payload.data || [];
    renderTable(payload.data || []);
    renderPagination(payload.pagination || {});
  }

  function renderTable(entries) {
    if (!entries.length) {
      els.tableBody.innerHTML = '<tr><td colspan="7" class="knowledge-empty">当前筛选条件下没有内容。</td></tr>';
      els.total.textContent = "当前共 0 条";
      return;
    }
    els.total.textContent = "当前共 " + entries.length + " 条";
    els.tableBody.innerHTML = entries.map(function (entry) {
      return (
        "<tr>" +
          '<td><div class="knowledge-title"><strong>' + escapeHtml(entry.title) + '</strong><p>' + escapeHtml(summarize(entry.content)) + "</p></div></td>" +
          '<td><span class="status-pill status-pill--pending">' + escapeHtml(contentTypeLabel(entry.content_type)) + "</span></td>" +
          '<td><span class="status-pill ' + (entry.is_active ? "status-pill--success" : "status-pill--inactive") + '">' + escapeHtml(activeLabel(entry.is_active)) + "</span></td>" +
          '<td><span class="status-pill ' + vectorClass(entry.vector_sync_status) + '">' + escapeHtml(vectorLabel(entry.vector_sync_status)) + "</span></td>" +
          "<td>" + escapeHtml(entry.vector_synced_at || "-") + "</td>" +
          "<td>" + escapeHtml(entry.updated_at || "-") + "</td>" +
          '<td><div class="knowledge-actions">' +
            '<button class="btn" data-action="edit" data-id="' + entry.id + '" type="button">查看 / 编辑</button>' +
            '<button class="btn" data-action="retry" data-id="' + entry.id + '" type="button">重新同步</button>' +
            '<button class="btn" data-action="toggle" data-id="' + entry.id + '" type="button">' + (entry.is_active ? "停用" : "启用") + "</button>" +
          "</div></td>" +
        "</tr>"
      );
    }).join("");
  }

  function renderPagination(pagination) {
    const totalPages = pagination.total_pages || 0;
    const total = pagination.total || 0;
    els.total.textContent = "当前共 " + total + " 条";
    if (totalPages <= 1) {
      els.pagination.innerHTML = "";
      return;
    }
    const prevDisabled = state.page <= 1 ? "disabled" : "";
    const nextDisabled = state.page >= totalPages ? "disabled" : "";
    els.pagination.innerHTML =
      '<button class="btn" type="button" data-page="' + (state.page - 1) + '" ' + prevDisabled + '>上一页</button>' +
      '<span>第 ' + state.page + " / " + totalPages + " 页</span>" +
      '<button class="btn" type="button" data-page="' + (state.page + 1) + '" ' + nextDisabled + '>下一页</button>';
  }

  async function loadEntryDetail(entryId) {
    const response = await fetch("/api/v1/admin/knowledge-config/entries/" + entryId, {
      headers: authHeaders(),
      credentials: "same-origin",
    });
    if (!response.ok) {
      showError("条目详情加载失败");
      return;
    }
    const payload = await response.json();
    const entry = payload.data.entry;
    state.editingId = entry.id;
    els.drawerTitle.textContent = "编辑内容";
    els.drawerSubtitle.textContent = "保存后会自动重新同步 AI 向量检索。";
    els.form.title.value = entry.title || "";
    els.form.contentType.value = entry.content_type || "";
    els.form.content.value = entry.content || "";
    els.form.keywords.value = entry.keywords || "";
    els.form.priority.value = entry.priority ?? 50;
    els.form.isActive.checked = !!entry.is_active;
    renderSuggestion({
      label: contentTypeLabel(entry.suggested_category || entry.content_type),
      reason: entry.suggest_reason || "暂无建议",
    });
    renderSyncState(entry);
    renderHistory(payload.data.history || []);
    openDrawer();
  }

  async function saveEntry() {
    clearErrors();
    const payload = {
      title: els.form.title.value,
      content_type: els.form.contentType.value,
      content: els.form.content.value,
      keywords: els.form.keywords.value,
      priority: Number(els.form.priority.value || 50),
      is_active: els.form.isActive.checked,
    };
    const url = state.editingId
      ? "/api/v1/admin/knowledge-config/entries/" + state.editingId
      : "/api/v1/admin/knowledge-config/entries";
    const method = state.editingId ? "PUT" : "POST";
    const response = await fetch(url, {
      method: method,
      headers: authHeaders(),
      body: JSON.stringify(payload),
      credentials: "same-origin",
    });
    if (response.status === 422) {
      const result = await response.json();
      renderValidationError(result.detail || "表单校验失败");
      return;
    }
    if (!response.ok) {
      showError("保存失败，请稍后再试");
      return;
    }
    const result = await response.json();
    state.editingId = result.data.id;
    renderSyncState(result.data);
    await loadEntryDetail(result.data.id);
    await loadEntries();
    showSuccess("保存成功");
  }

  async function retrySync(entryId) {
    const response = await fetch("/api/v1/admin/knowledge-config/entries/" + entryId + "/retry-sync", {
      method: "POST",
      headers: authHeaders(),
      credentials: "same-origin",
    });
    if (!response.ok) {
      showError("重新同步失败");
      return;
    }
    const result = await response.json();
    if (state.editingId === entryId) {
      renderSyncState(result.data);
      await loadEntryDetail(entryId);
    }
    await loadEntries();
    showSuccess("已触发重新同步");
  }

  async function toggleActive(entryId) {
    const response = await fetch("/api/v1/admin/knowledge-config/entries/" + entryId + "/toggle-active", {
      method: "POST",
      headers: authHeaders(),
      credentials: "same-origin",
    });
    if (!response.ok) {
      showError("启停更新失败");
      return;
    }
    const result = await response.json();
    if (state.editingId === entryId) {
      renderSyncState(result.data);
      await loadEntryDetail(entryId);
    }
    await loadEntries();
    showSuccess(result.data.is_active ? "已启用" : "已停用");
  }

  async function requestSuggestion() {
    const title = els.form.title.value.trim();
    const content = els.form.content.value.trim();
    if (!title && !content) {
      renderSuggestion({ label: "待分析", reason: "填写标题和正文后会给出建议分类。" });
      return;
    }
    const response = await fetch("/api/v1/admin/knowledge-config/suggest-category", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ title: title, content: content }),
      credentials: "same-origin",
    });
    if (!response.ok) {
      return;
    }
    const result = await response.json();
    renderSuggestion(result.data);
  }

  function renderValidationError(message) {
    if (message.indexOf("标题") >= 0) {
      els.form.errors.title.textContent = message;
      return;
    }
    if (message.indexOf("分类") >= 0) {
      els.form.errors.contentType.textContent = message;
      return;
    }
    if (message.indexOf("正文") >= 0) {
      els.form.errors.content.textContent = message;
      return;
    }
    showError(message);
  }

  function summarize(text) {
    const clean = (text || "").replace(/\s+/g, " ").trim();
    return clean.length > 46 ? clean.slice(0, 46) + "..." : clean;
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  els.createButton.addEventListener("click", function () {
    resetDrawer();
    openDrawer();
  });
  els.closeButton.addEventListener("click", closeDrawer);
  els.cancelButton.addEventListener("click", closeDrawer);
  els.drawerMask.addEventListener("click", closeDrawer);
  els.saveButton.addEventListener("click", saveEntry);
  els.retryButton.addEventListener("click", function () {
    if (state.editingId) {
      retrySync(state.editingId);
    }
  });
  els.filters.apply.addEventListener("click", function () {
    state.page = 1;
    loadEntries();
  });
  els.filters.keyword.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      state.page = 1;
      loadEntries();
    }
  });
  els.form.title.addEventListener("blur", requestSuggestion);
  els.form.content.addEventListener("blur", requestSuggestion);

  els.tableBody.addEventListener("click", function (event) {
    const button = event.target.closest("button[data-action]");
    if (!button) {
      return;
    }
    const entryId = Number(button.dataset.id);
    if (button.dataset.action === "edit") {
      loadEntryDetail(entryId);
    } else if (button.dataset.action === "retry") {
      retrySync(entryId);
    } else if (button.dataset.action === "toggle") {
      toggleActive(entryId);
    }
  });

  els.pagination.addEventListener("click", function (event) {
    const button = event.target.closest("button[data-page]");
    if (!button || button.disabled) {
      return;
    }
    state.page = Number(button.dataset.page);
    loadEntries();
  });

  loadEntries();
})();
