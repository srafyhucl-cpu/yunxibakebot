<script setup lang="ts">
import { Refresh, Search } from "@element-plus/icons-vue";
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
  filterSource,
  filterSyncStatus,
  currentPage,
  total,
  pageSize,
  activeCount,
  tableRows,
  openDetail,
  closeDetail,
  submitSearch,
  resetFilters,
  changePage,
  toggleProduct,
  reconciling,
  runReconcile,
} = useProductsPage();

const inactiveCount = computed(() => Math.max(total.value - activeCount.value, 0));

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
    <div class="products-page__summary">
      <span class="products-page__stat">
        <span class="products-page__stat-label">当前页</span>
        <strong class="products-page__stat-value">{{ tableRows.length }}</strong>
      </span>
      <span class="products-page__stat-divider" />
      <span class="products-page__stat">
        <span class="products-page__stat-label">在售</span>
        <strong class="products-page__stat-value products-page__stat-value--active">{{ activeCount }}</strong>
      </span>
      <span class="products-page__stat-divider" />
      <span class="products-page__stat">
        <span class="products-page__stat-label">下架</span>
        <strong class="products-page__stat-value">{{ inactiveCount }}</strong>
      </span>
    </div>

    <el-card shadow="never" class="products-page__filters">
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
          <el-option label="全部状态" value="" />
          <el-option label="在售" value="1" />
          <el-option label="已下架" value="0" />
        </el-select>

        <el-select v-model="filterSource" placeholder="数据来源" clearable style="width:140px">
          <el-option label="全部来源" value="" />
          <el-option label="有赞推送" value="youzan_webhook" />
          <el-option label="有赞对账同步" value="product_reconcile" />
          <el-option label="人工录入" value="admin_manual" />
        </el-select>

        <el-select v-model="filterSyncStatus" placeholder="AI 可读状态" clearable style="width:140px">
          <el-option label="全部状态" value="" />
          <el-option label="已入向量" value="success" />
          <el-option label="待同步" value="pending" />
          <el-option label="同步失败" value="failed" />
          <el-option label="同步中" value="syncing" />
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
    </el-card>

    <el-card shadow="never" class="products-page__table-card">
      <template #header>
        <div class="products-page__header">
          <strong>商品列表</strong>
          <span class="products-page__header-total">共 {{ total }} 条</span>
        </div>
      </template>

      <div class="products-page__desktop" ref="tableWrapper">
        <el-table :data="tableRows" v-loading="loading" stripe :height="tableHeight" class="products-page__table">
          <el-table-column prop="title" label="商品名" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              <button class="products-page__title-button" type="button" @click="openDetail(row)">
                <strong class="products-page__title-text">{{ row.title }}</strong>
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="activeLabel" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.isActive ? 'success' : 'info'" effect="light" size="small">
                {{ row.activeLabel }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="syncSourceLabel" label="来源" min-width="120" />
          <el-table-column prop="syncStatusLabel" label="AI 可读" width="90" />
          <el-table-column prop="priceFen" label="单价" width="90" align="right">
            <template #default="{ row }">
              <span v-if="row.priceFen != null" class="products-page__price">
                ¥{{ (row.priceFen / 100).toFixed(2) }}
              </span>
              <span v-else class="products-page__empty">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="stock" label="库存" width="80" align="right">
            <template #default="{ row }">
              <span v-if="row.stock != null" class="products-page__stock">{{ row.stock }}</span>
              <span v-else class="products-page__empty">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="updatedAt" label="最近更新" min-width="170">
            <template #default="{ row }">
              {{ row.updatedAt ? row.updatedAt.replace("T", " ").slice(0, 19) : "未记录" }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="190" fixed="right">
            <template #default="{ row }">
              <div class="products-page__actions">
                <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
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
            v-for="row in tableRows"
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

.products-page__summary {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
}

.products-page__stat {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.products-page__stat-label {
  color: var(--yx-text-muted);
  font-size: 13px;
}

.products-page__stat-value {
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}

.products-page__stat-value--active {
  color: var(--el-color-success);
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
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: var(--yx-text-muted);
}

.products-page__empty {
  color: var(--yx-text-muted);
  font-size: 13px;
}

.products-page__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.products-page__pagination {
  position: sticky;
  bottom: 0;
  z-index: 10;
  display: flex;
  justify-content: flex-end;
  padding: 10px 0 4px;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 8px;
}

@media (max-width: 767px) {
  .products-page__summary {
    flex-wrap: wrap;
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
