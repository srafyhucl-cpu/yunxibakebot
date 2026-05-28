<script setup lang="ts">
import { Refresh, Search } from "@element-plus/icons-vue";
import { computed } from "vue";

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
</script>

<template>
  <section class="products-page">
    <div class="products-page__summary">
      <el-card shadow="never">
        <div class="products-page__metric">
          <span class="products-page__metric-label">当前页商品</span>
          <strong class="products-page__metric-value">{{ tableRows.length }}</strong>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="products-page__metric">
          <span class="products-page__metric-label">在售商品</span>
          <strong class="products-page__metric-value">{{ activeCount }}</strong>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="products-page__metric">
          <span class="products-page__metric-label">下架商品</span>
          <strong class="products-page__metric-value">{{ inactiveCount }}</strong>
        </div>
      </el-card>
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

        <el-select v-model="filterSource" placeholder="数据来源" clearable style="width:150px">
          <el-option label="全部来源" value="" />
          <el-option label="有赞推送" value="youzan_webhook" />
          <el-option label="有赞对账同步" value="product_reconcile" />
          <el-option label="人工录入" value="admin_manual" />
        </el-select>

        <el-button type="primary" :icon="Search" @click="submitSearch">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="products-page__header">
          <div>
            <strong>商品列表</strong>
            <p>优先展示当前页商品状态、同步来源和最近更新时间。</p>
          </div>
          <div class="products-page__header-actions">
            <el-button
              type="warning"
              :loading="reconciling"
              :icon="Refresh"
              @click="runReconcile"
            >全量对账</el-button>
            <span class="products-page__header-total">共 {{ total }} 条</span>
          </div>
        </div>
      </template>

      <div class="products-page__desktop">
        <el-table :data="tableRows" v-loading="loading" stripe>
          <el-table-column prop="title" label="商品" min-width="260">
            <template #default="{ row }">
              <button class="products-page__title-button" type="button" @click="openDetail(row)">
                <strong>{{ row.title }}</strong>
                <span>ID {{ row.id }}<template v-if="row.youzanItemId"> / 有赞 {{ row.youzanItemId }}</template></span>
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="activeLabel" label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.isActive ? 'success' : 'info'" effect="light">
                {{ row.activeLabel }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="syncSourceLabel" label="来源" min-width="140" />
          <el-table-column prop="syncStatusLabel" label="AI 可读状态" min-width="120" />
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
  display: grid;
  gap: 16px;
}

.products-page__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.products-page__metric {
  display: grid;
  gap: 8px;
}

.products-page__metric-label {
  color: var(--yx-text-muted);
  font-size: 14px;
}

.products-page__metric-value {
  font-size: 28px;
  line-height: 1;
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.products-page__header p {
  margin: 6px 0 0;
  color: var(--yx-text-muted);
  font-size: 13px;
}

.products-page__header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.products-page__header-total {
  color: var(--yx-text-muted);
  font-size: 13px;
}

.products-page__desktop {
  display: block;
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
  display: grid;
  gap: 4px;
}

.products-page__title-button span,
.products-page__card-meta {
  color: var(--yx-text-muted);
  font-size: 12px;
}

.products-page__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.products-page__pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1199px) {
  .products-page__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .products-page__summary,
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
