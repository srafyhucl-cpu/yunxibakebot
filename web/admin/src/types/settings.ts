export type SettingsPanel = "shop" | "channel" | "api";

export interface ShopSettingsSummary {
  serverHost: string;
  serverPort: number;
  databasePath: string;
  embeddingPath: string;
  featuredProductCount: number;
  productTotal: number;
}

export interface ChannelSettingsSummary {
  youzan: {
    clientIdConfigured: boolean;
    clientSecretConfigured: boolean;
    kdtIdConfigured: boolean;
    webhookTokenConfigured: boolean;
    mockMode: boolean;
  };
  wecom: {
    corpIdConfigured: boolean;
    agentIdConfigured: boolean;
    secretConfigured: boolean;
    tokenConfigured: boolean;
    encodingAesKeyConfigured: boolean;
    staffIdConfigured: boolean;
    robotWebhookConfigured: boolean;
  };
}

export interface ApiSettingsSummary {
  adminTokenConfigured: boolean;
  deepseekApiKeyConfigured: boolean;
  deepseekBaseUrl: string;
  deepseekModel: string;
  deepseekTimeoutSeconds: number;
}

export interface SettingsSummary {
  shop: ShopSettingsSummary;
  channels: ChannelSettingsSummary;
  api: ApiSettingsSummary;
}
