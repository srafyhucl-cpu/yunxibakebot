<script setup lang="ts">
import { Search } from "@element-plus/icons-vue";

import { useKnowledgePage } from "./useKnowledgePage";

const {
  loading,
  saving,
  actionId,
  drawerVisible,
  drawerMode,
  errorMessage,
  rows,
  selectedEntry,
  history,
  total,
  pageSize,
  activeCount,
  failedSyncCount,
  currentPage,
  filterDraft,
  form,
  loadEntries,
  submitFilters,
  changePage,
  openCreate,
  openEdit,
  closeDrawer,
  saveEntry,
  toggleEntry,
  retrySync,
  suggestCategory,
} = useKnowledgePage();
</script>

<template>
  <section class="knowledge-page">
    <div class="knowledge-page__summary">
      <el-card shadow="never">
        <span>当前页条目</span>
        <strong>{{ rows.length }}</strong>
      </el-card>
      <el-card shadow="never">
        <span>当前页启用</span>
        <strong>{{ activeCount }}</strong>
      </el-card>
      <el-card shadow="never">
        <span>同步失败</span>
        <strong>{{ failedSyncCount }}</strong>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="knowledge-page__header">
          <div>
            <strong>知识配置</strong>
            <p>管理 FAQ、规则、话术和商品知识，保存后会同步到 AI 可读向量索引。</p>
          </div>
          <el-button type="primary" @click="openCreate">新增知识</el-button>
        </div>
      </template>

      <el-form class="knowledge-page__filters" @submit.prevent="submitFilters">
        <el-select v-model="filterDraft.contentType" clearable placeholder="内容类型">
          <el-option label="FAQ" value="faq" />
          <el-option label="规则" value="rule" />
          <el-option label="话术" value="copywriting" />
          <el-option label="商品知识" value="product" />
        </el-select>
        <el-select v-model="filterDraft.isActive" clearable placeholder="启停状态">
          <el-option label="启用" value="1" />
          <el-option label="停用" value="0" />
        </el-select>
        <el-select v-model="filterDraft.vectorStatus" clearable placeholder="AI 可读状态">
          <el-option label="待同步" value="pending" />
          <el-option label="同步中" value="syncing" />
          <el-option label="已入向量" value="success" />
          <el-option label="同步失败" value="failed" />
        </el-select>
        <el-input
          v-model="filterDraft.keyword"
          clearable
          placeholder="搜索标题、内容或关键词"
          @keyup.enter="submitFilters"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="submitFilters">筛选</el-button>
      </el-form>

      <el-alert
        v-if="errorMessage"
        class="knowledge-page__alert"
        type="error"
        show-icon
        :closable="false"
      >
        <template #title>
          <span>{{ errorMessage }}</span>
          <el-button link type="primary" @click="loadEntries">重试</el-button>
        </template>
      </el-alert>

      <div class="knowledge-page__desktop">
        <el-table :data="rows" v-loading="loading" stripe>
          <el-table-column prop="title" label="知识条目" min-width="260">
            <template #default="{ row }">
              <button class="knowledge-page__title-button" type="button" @click="openEdit(row)">
                <strong>{{ row.title }}</strong>
                <span>{{ row.keywords || row.content.slice(0, 48) }}</span>
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="typeLabel" label="类型" width="120" />
          <el-table-column prop="activeLabel" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.isActive ? 'success' : 'info'" effect="light">{{ row.activeLabel }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="syncLabel" label="AI 可读" width="120">
            <template #default="{ row }">
              <el-tag :type="row.syncType" effect="light">{{ row.syncLabel }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updatedAtLabel" label="更新时间" min-width="170" />
          <el-table-column label="操作" width="230" fixed="right">
            <template #default="{ row }">
              <div class="knowledge-page__actions">
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button
                  link
                  :type="row.isActive ? 'warning' : 'success'"
                  :loading="actionId === row.id"
                  @click="toggleEntry(row)"
                >
                  {{ row.isActive ? "停用" : "启用" }}
                </el-button>
                <el-button
                  v-if="row.vectorSyncStatus === 'failed'"
                  link
                  type="danger"
                  :loading="actionId === row.id"
                  @click="retrySync(row)"
                >
                  重试同步
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="knowledge-page__mobile">
        <el-skeleton v-if="loading" :rows="4" animated />
        <button
          v-for="row in rows"
          v-else
          :key="row.id"
          class="knowledge-page__card"
          type="button"
          @click="openEdit(row)"
        >
          <div>
            <strong>{{ row.title }}</strong>
            <el-tag size="small" :type="row.syncType">{{ row.syncLabel }}</el-tag>
          </div>
          <span>{{ row.typeLabel }} · {{ row.activeLabel }} · {{ row.updatedAtLabel }}</span>
        </button>
      </div>

      <el-empty v-if="!loading && rows.length === 0" description="当前筛选条件下没有知识条目" />

      <div class="knowledge-page__pagination">
        <el-pagination
          background
          layout="prev, pager, next"
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          @current-change="changePage"
        />
      </div>
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      :title="drawerMode === 'create' ? '新增知识' : '编辑知识'"
      size="560px"
      @closed="closeDrawer"
    >
      <el-form label-position="top" class="knowledge-page__drawer-form">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="例如：配送范围说明" />
        </el-form-item>
        <el-form-item label="内容类型">
          <div class="knowledge-page__inline-field">
            <el-select v-model="form.contentType">
              <el-option label="FAQ" value="faq" />
              <el-option label="规则" value="rule" />
              <el-option label="话术" value="copywriting" />
              <el-option label="商品知识" value="product" />
            </el-select>
            <el-button plain @click="suggestCategory">AI 建议分类</el-button>
          </div>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="form.keywords" placeholder="用逗号分隔，便于检索" />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="8"
            placeholder="写入客服回答时需要严格依据的内容"
          />
        </el-form-item>
        <div class="knowledge-page__drawer-row">
          <el-form-item label="优先级">
            <el-input-number v-model="form.priority" :min="0" :max="100" />
          </el-form-item>
          <el-form-item label="是否启用">
            <el-switch v-model="form.isActive" active-text="启用" inactive-text="停用" />
          </el-form-item>
        </div>
      </el-form>

      <el-alert
        v-if="selectedEntry?.vectorSyncError"
        type="error"
        show-icon
        :closable="false"
        :title="selectedEntry.vectorSyncError"
      />

      <section v-if="history.length" class="knowledge-page__history">
        <h4>最近变更</h4>
        <pre>{{ JSON.stringify(history.slice(0, 5), null, 2) }}</pre>
      </section>

      <template #footer>
        <div class="knowledge-page__drawer-actions">
          <el-button @click="drawerVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveEntry">保存</el-button>
        </div>
      </template>
    </el-drawer>
  </section>
</template>

<style scoped>
.knowledge-page {
  display: grid;
  gap: 16px;
}

.knowledge-page__summary,
.knowledge-page__filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.knowledge-page__summary :deep(.el-card__body) {
  display: grid;
  gap: 8px;
}

.knowledge-page__summary span,
.knowledge-page__header p,
.knowledge-page__title-button span,
.knowledge-page__card span {
  color: var(--yx-text-muted);
}

.knowledge-page__summary strong {
  font-size: 28px;
}

.knowledge-page__header,
.knowledge-page__drawer-row,
.knowledge-page__drawer-actions,
.knowledge-page__inline-field {
  display: flex;
  gap: 12px;
}

.knowledge-page__header {
  justify-content: space-between;
  align-items: flex-start;
}

.knowledge-page__header p {
  margin: 6px 0 0;
}

.knowledge-page__filters {
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-bottom: 16px;
}

.knowledge-page__alert {
  margin-bottom: 16px;
}

.knowledge-page__title-button,
.knowledge-page__card {
  width: 100%;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.knowledge-page__title-button {
  display: grid;
  gap: 4px;
  padding: 0;
}

.knowledge-page__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.knowledge-page__mobile {
  display: none;
}

.knowledge-page__card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--yx-border);
  border-radius: 14px;
  padding: 14px;
}

.knowledge-page__card div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.knowledge-page__pagination,
.knowledge-page__drawer-actions {
  justify-content: flex-end;
}

.knowledge-page__pagination {
  display: flex;
  margin-top: 16px;
}

.knowledge-page__drawer-form {
  display: grid;
  gap: 8px;
}

.knowledge-page__drawer-row > * {
  flex: 1;
}

.knowledge-page__inline-field {
  width: 100%;
}

.knowledge-page__inline-field .el-select {
  flex: 1;
}

.knowledge-page__history {
  margin-top: 18px;
}

.knowledge-page__history pre {
  max-height: 180px;
  overflow: auto;
  border-radius: 12px;
  padding: 12px;
  background: #f8fafc;
  font-size: 12px;
}

@media (max-width: 1100px) {
  .knowledge-page__summary,
  .knowledge-page__filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .knowledge-page__summary,
  .knowledge-page__filters {
    grid-template-columns: minmax(0, 1fr);
  }

  .knowledge-page__header,
  .knowledge-page__drawer-row,
  .knowledge-page__inline-field {
    flex-direction: column;
  }

  .knowledge-page__desktop {
    display: none;
  }

  .knowledge-page__mobile {
    display: grid;
    gap: 12px;
  }
}
</style>
