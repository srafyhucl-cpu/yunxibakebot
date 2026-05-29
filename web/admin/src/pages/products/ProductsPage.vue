<script setup lang="ts">
import { QuestionFilled, Refresh, Search } from "@element-plus/icons-vue";
import { computed, onMounted, onUnmounted, ref } from "vue";

import ProductDetailDrawer from "@/features/products/ProductDetailDrawer.vue";

import { useProductsPage } from "./useProductsPage";

const {
  loading,
  togglingId,
  drawerVisible,
  selectedProduct,
  searchDraft,
  filterActive,
  filterSyncStatus,
  filterFeatured,
  filterYouzanId,
  filterStockLevel,
  currentPage,
  total,
  totalActive,
  totalInactive,
  pageSize,
  activeCount,
  displayedTableRows,
  togglingFeaturedId,
  openDetail,
  closeDetail,
  submitSearch,
  resetFilters,
  changePage,
  toggleProduct,
  toggleFeatured,
  reconciling,
  runReconcile,
} = useProductsPage();

const inactiveCount = computed(() => displayedTableRows.value.filter((row) => !row.isActive).length);

const tableWrapper = ref<HTMLElement | null>(null);
const tableHeight = ref(400);
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (tableWrapper.value) {
    resizeObserver = new ResizeObserver(() => {
      tableHeight.value = tableWrapper.value?.clientHeight ?? 400;
    });
    resizeObserver.observe(tableWrapper.value);
    tableHeight.value = tableWrapper.value.clientHeight;
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
});
</script>

<template>
  <section class="products-page">
    <el-card shadow="never" class="products-page__filters">
      <div class="products-page__header-container">
        <!-- 核心统计与快速切换 Tab 卡片 (Global Quick-Filter Stats) -->
        <div class="products-page__global-stats">
          <div 
            class="products-page__stat-card" 
            :class="{ 'products-page__stat-card--active': filterActive === 'all' }"
            @click="filterActive = 'all'; submitSearch()"
          >
            <span class="products-page__stat-label">全部商品</span>
            <strong class="products-page__stat-value">{{ totalActive + totalInactive }}</strong>
          </div>
          <div 
            class="products-page__stat-card products-page__stat-card--success" 
            :class="{ 'products-page__stat-card--active': filterActive === '1' }"
            @click="filterActive = '1'; submitSearch()"
          >
            <span class="products-page__stat-label">在售中</span>
            <strong class="products-page__stat-value">{{ totalActive }}</strong>
          </div>
          <div 
            class="products-page__stat-card products-page__stat-card--warning" 
            :class="{ 'products-page__stat-card--active': filterActive === '0' }"
            @click="filterActive = '0'; submitSearch()"
          >
            <span class="products-page__stat-label">已下架</span>
            <strong class="products-page__stat-value">{{ totalInactive }}</strong>
          </div>
        </div>

        <!-- 商品检索与多维度过滤筛选项 (Filter Actions Form) -->
        <el-form class="products-page__filter-form" @submit.prevent="submitSearch">
          <el-input
            v-model="searchDraft"
            placeholder="搜索商品标题、关键词"
            clearable
            @keyup.enter="submitSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>

          <el-select v-model="filterActive" placeholder="上下架状态" clearable style="width:130px">
            <el-option label="全部状态" value="all" />
            <el-option label="在售" value="1" />
            <el-option label="已下架" value="0" />
          </el-select>

          <el-select v-model="filterSyncStatus" placeholder="AI 可读状态" clearable style="width:140px">
            <el-option label="全部状态" value="" />
            <el-option label="已入向量" value="success" />
            <el-option label="待同步" value="pending" />
            <el-option label="同步失败" value="failed" />
            <el-option label="同步中" value="syncing" />
          </el-select>

          <el-checkbox v-model="filterFeatured" border style="height:32px">仅看主推款</el-checkbox>

          <el-input
            v-model="filterYouzanId"
            placeholder="有赞ID"
            clearable
            style="width:140px"
          />

          <el-select v-model="filterStockLevel" placeholder="库存状态" clearable style="width:120px">
            <el-option label="全部" value="" />
            <el-option label="充足（>200）" value="sufficient" />
            <el-option label="靠近警告（≤200）" value="low" />
            <el-option label="无库存" value="zero" />
          </el-select>

          <el-button type="primary" :icon="Search" @click="submitSearch">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button
            type="warning"
            :loading="reconciling"
            :icon="Refresh"
            @click="runReconcile"
          >全量对账</el-button>
        </el-form>
      </div>
    </el-card>

    <el-card shadow="never" class="products-page__table-card">
      <template #header>
        <div class="products-page__header">
          <strong>商品列表</strong>
          <span class="products-page__header-total">共 {{ total }} 条</span>
        </div>
      </template>

      <div class="products-page__desktop" ref="tableWrapper">
        <el-table :data="displayedTableRows" v-loading="loading" stripe border :height="tableHeight" class="products-page__table" :default-sort="{ prop: 'updatedAt', order: 'descending' }">
          <el-table-column type="index" label="#" width="50" align="center" />
          <el-table-column prop="title" label="商品名" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <button class="products-page__title-button" type="button" @click="openDetail(row)">
                <strong class="products-page__title-text">{{ row.title || '（无标题）' }}</strong>
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="activeLabel" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.isActive ? 'success' : 'info'" effect="light" size="small">
                {{ row.activeLabel }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="syncStatusLabel" label="AI 可读" width="90" align="center" />
          <el-table-column prop="keywords" label="关键词" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.keywords" class="products-page__keywords">{{ row.keywords }}</span>
              <span v-else class="products-page__empty">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="youzanItemId" label="有赞ID" width="110" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.youzanItemId" class="products-page__youzan-id">{{ row.youzanItemId }}</span>
              <span v-else class="products-page__empty">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="priceFen" label="单价" width="90" align="right" sortable>
            <template #default="{ row }">
              <span v-if="row.priceFen != null" class="products-page__price">
                ¥{{ (row.priceFen / 100).toFixed(2) }}
              </span>
              <span v-else class="products-page__empty">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="stock" width="100" align="center" sortable>
            <template #header>
              <el-tooltip content="库存 > 200 显示「充足」" placement="top">
                <el-icon style="margin-right:3px;vertical-align:middle;cursor:help;color:var(--el-color-info);"><QuestionFilled /></el-icon>
              </el-tooltip>
              <span>库存</span>
            </template>
            <template #default="{ row }">
              <span v-if="row.stock == null" class="products-page__empty">—</span>
              <el-tooltip v-else-if="row.stock > 200" :content="`实际库存：${row.stock.toLocaleString()} 件`" placement="top">
                <span class="products-page__stock-sufficient">充足</span>
              </el-tooltip>
              <span v-else class="products-page__stock">{{ row.stock.toLocaleString() }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="soldNum" label="销量" width="80" align="center" sortable>
            <template #default="{ row }">
              <span v-if="row.soldNum" class="products-page__sold-num">{{ row.soldNum.toLocaleString() }}</span>
              <span v-else class="products-page__empty">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="updatedAt" label="最近更新" min-width="170" align="center" sortable>
            <template #default="{ row }">
              {{ row.updatedAt ? row.updatedAt.replace("T", " ").slice(0, 19) : "未记录" }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right" align="center">
            <template #default="{ row }">
              <div class="products-page__actions">
                <el-tooltip :content="row.isFeatured ? '着移出主推款' : '加入主推款'" placement="top">
                  <el-switch
                    :model-value="row.isFeatured"
                    :loading="togglingFeaturedId === row.id"
                    size="small"
                    active-color="#f59e0b"
                    @change="toggleFeatured(row)"
                  />
                </el-tooltip>
                <el-button link type="primary" @click="openDetail(row)">查看</el-button>
                <el-button
                  :loading="togglingId === row.id"
                  :type="row.isActive ? 'warning' : 'success'"
                  plain
                  size="small"
                  @click="toggleProduct(row)"
                >
                  {{ row.isActive ? "下架" : "上架" }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="products-page__mobile">
        <el-skeleton :rows="4" animated v-if="loading" />
        <div v-else class="products-page__cards">
          <button
            v-for="row in displayedTableRows"
            :key="row.id"
            class="products-page__card"
            type="button"
            @click="openDetail(row)"
          >
            <div class="products-page__card-top">
              <strong>{{ row.title }}</strong>
              <el-tag size="small" :type="row.isActive ? 'success' : 'info'" effect="light">
                {{ row.activeLabel }}
              </el-tag>
            </div>
            <div class="products-page__card-meta">
              <span v-if="row.youzanItemId">有赞ID：{{ row.youzanItemId }}</span>
              <span>来源：{{ row.syncSourceLabel }}</span>
              <span>AI：{{ row.syncStatusLabel }}</span>
              <span>更新：{{ row.updatedAt ? row.updatedAt.replace("T", " ").slice(0, 19) : "未记录" }}</span>
            </div>
          </button>
        </div>
      </div>

      <div class="products-page__pagination">
        <div class="products-page__page-stats">
          <span>当前页 <strong>{{ displayedTableRows.length }}</strong> 条</span>
          <span class="products-page__stat-divider" />
          <span>在售 <strong class="products-page__stat-value--active">{{ activeCount }}</strong></span>
          <span class="products-page__stat-divider" />
          <span>下架 <strong>{{ inactiveCount }}</strong></span>
        </div>
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

    <ProductDetailDrawer
      v-model:visible="drawerVisible"
      :product="selectedProduct"
      :toggling-id="togglingId"
      @toggle="toggleProduct"
      @update:visible="($event) => (!$event ? closeDetail() : null)"
    />
  </section>
</template>

<style scoped>
.products-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 16px;
  overflow: hidden;
}

.products-page__table-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.products-page__table-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding-bottom: 0;
  overflow: hidden;
}

.products-page__header-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.products-page__global-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
  flex-shrink: 0;
}

.products-page__stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--yx-bg);
  border: 1px solid var(--yx-border);
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.products-page__stat-card:hover {
  background: var(--yx-panel);
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transform: translateY(-1px);
}

.products-page__stat-card--active {
  background: var(--el-color-primary-light-9) !important;
  border-color: var(--el-color-primary) !important;
  color: var(--el-color-primary);
}

.products-page__stat-card--active .products-page__stat-value {
  color: var(--el-color-primary) !important;
}

.products-page__stat-card--success.products-page__stat-card--active {
  background: var(--el-color-success-light-9) !important;
  border-color: var(--el-color-success) !important;
  color: var(--el-color-success);
}

.products-page__stat-card--success.products-page__stat-card--active .products-page__stat-value {
  color: var(--el-color-success) !important;
}

.products-page__stat-card--warning.products-page__stat-card--active {
  background: var(--el-color-warning-light-9) !important;
  border-color: var(--el-color-warning) !important;
  color: var(--el-color-warning);
}

.products-page__stat-card--warning.products-page__stat-card--active .products-page__stat-value {
  color: var(--el-color-warning) !important;
}

.products-page__stat-label {
  color: var(--yx-text-muted);
  font-size: 13px;
  font-weight: 500;
}

.products-page__stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--yx-text);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.products-page__page-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--yx-text-muted);
  white-space: nowrap;
}

.products-page__stat {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.products-page__stat-divider {
  display: inline-block;
  width: 1px;
  height: 14px;
  background: var(--el-border-color);
}

.products-page__filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.products-page__filter-form .el-input {
  width: 220px;
}

.products-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.products-page__header-total {
  color: var(--yx-text-muted);
  font-size: 13px;
}

.products-page__table {
  flex: 1;
}

.products-page__table :deep(.el-scrollbar__bar.is-vertical) {
  display: none;
}

.products-page__table :deep(.el-table__header th) {
  text-align: center;
  padding: 10px 0;
}

.products-page__table :deep(.el-table__header th .cell) {
  white-space: nowrap;
}

.products-page__desktop {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.products-page__mobile {
  display: none;
}

.products-page__title-button,
.products-page__card {
  width: 100%;
  border: 0;
  background: transparent;
  padding: 0;
  text-align: left;
  color: inherit;
  cursor: pointer;
}

.products-page__title-button {
  display: block;
  max-width: 100%;
}

.products-page__title-text {
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: 100%;
}

.products-page__title-button span,
.products-page__card-meta {
  color: var(--yx-text-muted);
  font-size: 12px;
}

.products-page__price {
  font-variant-numeric: tabular-nums;
  font-size: 13px;
}

.products-page__stock {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.products-page__mono {
  font-family: var(--yx-font-mono);
  font-size: 12px;
  color: var(--yx-text-muted);
}

.products-page__empty {
  color: var(--yx-text-muted);
  font-size: 13px;
}

.products-page__youzan-id {
  font-family: var(--yx-font-mono);
  font-size: 12px;
  color: var(--yx-text-muted);
}

.products-page__sold-num {
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: var(--el-color-primary);
}

.products-page__stock-sufficient {
  color: var(--el-color-success);
  font-weight: 500;
  font-size: 13px;
}

.products-page__keywords {
  font-size: 12px;
  color: var(--yx-text-muted);
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.products-page__actions {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: nowrap;
  gap: 8px;
}

.products-page__table :deep(.el-table__cell) {
  vertical-align: middle;
}

.products-page__table :deep(.el-table__row td) {
  padding: 8px 0;
}

.products-page__pagination {
  position: sticky;
  bottom: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0 4px;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 8px;
}

@media (max-width: 767px) {
  .products-page__filter-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .products-page__filter-form {
    grid-template-columns: minmax(0, 1fr);
  }

  .products-page__desktop {
    display: none;
  }

  .products-page__mobile {
    display: block;
  }

  .products-page__cards {
    display: grid;
    gap: 12px;
  }

  .products-page__card {
    display: grid;
    gap: 10px;
    padding: 14px;
    border: 1px solid var(--yx-border);
    border-radius: 12px;
  }

  .products-page__card-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .products-page__card-meta {
    display: grid;
    gap: 4px;
  }

  .products-page__pagination {
    justify-content: center;
  }
}
</style>
