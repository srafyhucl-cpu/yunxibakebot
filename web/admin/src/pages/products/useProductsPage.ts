import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { productsService } from "@/services/products";
import type { ProductListItem } from "@/types/product";

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
  const drawerVisible = ref(false);
  const products = ref<ProductListItem[]>([]);
  const total = ref(0);
  const pageSize = ref(30);
  const selectedProduct = ref<ProductListItem | null>(null);
  const searchDraft = ref(normalizeKeyword(route.query.keyword));

  const currentPage = computed(() => parsePage(route.query.page));
  const currentKeyword = computed(() => normalizeKeyword(route.query.keyword));
  const activeCount = computed(() => products.value.filter((item) => item.isActive).length);

  const tableRows = computed(() =>
    products.value.map((item) => ({
      ...item,
      syncSourceLabel: item.lastSyncSource || "未记录",
      syncStatusLabel: formatSyncStatus(item.vectorSyncStatus),
      activeLabel: item.isActive ? "在售" : "下架",
    })),
  );

  async function loadProducts() {
    loading.value = true;
    try {
      const payload = await productsService.listProducts(currentPage.value, currentKeyword.value);
      products.value = payload.items;
      total.value = payload.total;
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
    const nextKeyword = searchDraft.value.trim();
    await router.replace({
      query: buildQuery(1, nextKeyword),
    });
  }

  async function changePage(page: number) {
    await router.replace({
      query: buildQuery(page, currentKeyword.value),
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

  function buildQuery(page: number, keyword: string): Record<string, string> {
    const query: Record<string, string> = {};
    if (page > 1) {
      query.page = String(page);
    }
    if (keyword) {
      query.keyword = keyword;
    }
    return query;
  }

  watch(
    () => route.query,
    async () => {
      searchDraft.value = currentKeyword.value;
      await loadProducts();
    },
    { immediate: true },
  );
  return {
    loading,
    togglingId,
    drawerVisible,
    products,
    total,
    pageSize,
    selectedProduct,
    searchDraft,
    currentPage,
    currentKeyword,
    activeCount,
    tableRows,
    openDetail,
    closeDetail,
    submitSearch,
    changePage,
    toggleProduct,
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
