export interface ProductListItem {
  id: number;
  category: string;
  contentType: string;
  title: string;
  content: string;
  keywords: string;
  priority: number;
  isActive: boolean;
  youzanItemId: string;
  lastSyncSource: string;
  lastSyncRef: string;
  vectorSyncStatus: string;
  updatedAt: string;
}

export interface ProductListPayload {
  items: ProductListItem[];
  total: number;
  page: number;
  pageSize: number;
}
