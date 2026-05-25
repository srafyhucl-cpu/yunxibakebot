import http from "./http";

import type { ProductListItem, ProductListPayload } from "@/types/product";

interface ProductListResponse {
  code: number;
  total: number;
  page?: number;
  page_size?: number;
  data: Array<{
    id: number;
    category: string;
    content_type?: string;
    title: string;
    content: string;
    keywords?: string;
    priority: number;
    is_active: boolean;
    youzan_item_id?: string | null;
    last_sync_source?: string;
    last_sync_ref?: string;
    vector_sync_status?: string;
    updated_at?: string;
  }>;
}

interface ToggleProductResponse {
  code: number;
  is_active: boolean;
  title: string;
}

function normalizeProduct(item: ProductListResponse["data"][number]): ProductListItem {
  return {
    id: item.id,
    category: item.category,
    contentType: item.content_type || "product",
    title: item.title,
    content: item.content,
    keywords: item.keywords || "",
    priority: item.priority,
    isActive: item.is_active,
    youzanItemId: item.youzan_item_id || "",
    lastSyncSource: item.last_sync_source || "",
    lastSyncRef: item.last_sync_ref || "",
    vectorSyncStatus: item.vector_sync_status || "",
    updatedAt: item.updated_at || "",
  };
}

export const productsService = {
  async listProducts(page: number, keyword: string): Promise<ProductListPayload> {
    const response = await http.get<ProductListResponse>("/products", {
      params: {
        page,
        search: keyword,
      },
    });
    return {
      items: response.data.data.map(normalizeProduct),
      total: response.data.total,
      page: response.data.page || page,
      pageSize: response.data.page_size || 30,
    };
  },

  async toggleProductActive(productId: number): Promise<ToggleProductResponse> {
    const response = await http.post<ToggleProductResponse>(`/products/${productId}/toggle-active`);
    return response.data;
  },
};
