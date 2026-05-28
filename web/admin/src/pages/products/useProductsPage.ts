import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { productsService, type ReconcileResult } from "@/services/products";
import type { ProductListItem } from "@/types/product";
import { formatSyncSource } from "@/utils/syncSourceLabel";

const DEFAULT_PAGE = 1;

function parsePage(rawValue: unknown): number {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_PAGE;
  }
  return Math.floor(parsed);
}

function normalizeKeyword(rawValue: unknown): string {
  return typeof rawValue === "string" ? rawValue.trim() : "";
}

export function useProductsPage() {
  const route = useRoute();
  const router = useRouter();

  const loading = ref(false);
  const togglingId = ref(0);
  const reconciling = ref(false);
  const drawerVisible = ref(false);
  const products = ref<ProductListItem[]>([]);
  const total = ref(0);
  const totalActive = ref(0);
  const totalInactive = ref(0);
  const pageSize = ref(30);
  const selectedProduct = ref<ProductListItem | null>(null);
  const searchDraft = ref(normalizeKeyword(route.query.keyword));
  const filterActive = ref(String(route.query.is_active ?? ""));
  const filterSource = ref(String(route.query.sync_source ?? ""));
  const filterSyncStatus = ref(String(route.query.vector_sync_status ?? ""));

  const currentPage = computed(() => parsePage(route.query.page));
  const currentKeyword = computed(() => normalizeKeyword(route.query.keyword));
  const currentActive = computed(() => String(route.query.is_active ?? ""));
  const currentSource = computed(() => String(route.query.sync_source ?? ""));
  const currentSyncStatus = computed(() => String(route.query.vector_sync_status ?? ""));
  const activeCount = computed(() => products.value.filter((item) => item.isActive).length);

  const tableRows = computed(() =>
    products.value.map((item) => ({
      ...item,
      syncSourceLabel: formatSyncSource(item.lastSyncSource),
      syncStatusLabel: formatSyncStatus(item.vectorSyncStatus),
      activeLabel: item.isActive ? "在售" : "下架",
    })),
  );

  async function loadProducts() {
    loading.value = true;
    try {
      const payload = await productsService.listProducts(
        currentPage.value, currentKeyword.value,
        currentActive.value, currentSource.value, currentSyncStatus.value,
      );
      products.value = payload.items;
      total.value = payload.total;
      totalActive.value = payload.totalActive;
      totalInactive.value = payload.totalInactive;
      pageSize.value = payload.pageSize;
      if (selectedProduct.value) {
        const nextSelected = payload.items.find((item) => item.id === selectedProduct.value?.id) || null;
        selectedProduct.value = nextSelected;
        drawerVisible.value = nextSelected !== null;
      }
    } finally {
      loading.value = false;
    }
  }

  function openDetail(product: ProductListItem) {
    selectedProduct.value = product;
    drawerVisible.value = true;
  }

  function closeDetail() {
    selectedProduct.value = null;
    drawerVisible.value = false;
  }

  async function submitSearch() {
    await router.replace({
      query: buildQuery(1, searchDraft.value.trim(), filterActive.value, filterSource.value, filterSyncStatus.value),
    });
  }

  async function resetFilters() {
    searchDraft.value = "";
    filterActive.value = "";
    filterSource.value = "";
    filterSyncStatus.value = "";
    await router.replace({ query: {} });
  }

  async function changePage(page: number) {
    await router.replace({
      query: buildQuery(page, currentKeyword.value, currentActive.value, currentSource.value, currentSyncStatus.value),
    });
  }

  async function toggleProduct(product: ProductListItem) {
    togglingId.value = product.id;
    try {
      const result = await productsService.toggleProductActive(product.id);
      ElMessage.success(`${result.title}已${result.is_active ? "上架" : "下架"}`);
      await loadProducts();
    } finally {
      togglingId.value = 0;
    }
  }

  async function runReconcile(): Promise<ReconcileResult | null> {
    reconciling.value = true;
    try {
      const result = await productsService.reconcileProducts();
      if (result.deactivated > 0) {
        ElMessage.warning(`对账完成：下架 ${result.deactivated} 条商品`);
      } else {
        ElMessage.success(`对账完成：全部对齐，无需下架`);
      }
      await loadProducts();
      return result;
    } catch (err) {
      ElMessage.error("对账失败，请检查网络或后台日志");
      return null;
    } finally {
      reconciling.value = false;
    }
  }

  function buildQuery(
    page: number,
    keyword: string,
    isActive: string = "",
    syncSource: string = "",
    syncStatus: string = "",
  ): Record<string, string> {
    const query: Record<string, string> = {};
    if (page > 1) query.page = String(page);
    if (keyword) query.keyword = keyword;
    if (isActive) query.is_active = isActive;
    if (syncSource) query.sync_source = syncSource;
    if (syncStatus) query.vector_sync_status = syncStatus;
    return query;
  }

  watch(
    () => route.query,
    async () => {
      searchDraft.value = currentKeyword.value;
      filterActive.value = currentActive.value;
      filterSource.value = currentSource.value;
      filterSyncStatus.value = currentSyncStatus.value;
      await loadProducts();
    },
    { immediate: true },
  );
  return {
    loading,
    togglingId,
    reconciling,
    drawerVisible,
    products,
    total,
    totalActive,
    totalInactive,
    pageSize,
    selectedProduct,
    searchDraft,
    filterActive,
    filterSource,
    filterSyncStatus,
    currentPage,
    currentKeyword,
    activeCount,
    tableRows,
    openDetail,
    closeDetail,
    submitSearch,
    resetFilters,
    changePage,
    toggleProduct,
    runReconcile,
  };
}

function formatSyncStatus(status: string): string {
  if (status === "success") {
    return "已入向量";
  }
  if (status === "failed") {
    return "同步失败";
  }
  if (status === "syncing") {
    return "同步中";
  }
  if (status === "pending") {
    return "待同步";
  }
  return "未记录";
}
