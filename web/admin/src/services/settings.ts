import http from "./http";

import type { SettingsSummary } from "@/types/settings";

interface SettingsSummaryResponse {
  code: number;
  data: {
    shop: {
      server_host: string;
      server_port: number;
      database_path: string;
      embedding_path: string;
      featured_product_count: number;
      product_total: number;
    };
    channels: {
      youzan: {
        client_id_configured: boolean;
        client_secret_configured: boolean;
        kdt_id_configured: boolean;
        webhook_token_configured: boolean;
        mock_mode: boolean;
      };
      wecom: {
        corp_id_configured: boolean;
        agent_id_configured: boolean;
        secret_configured: boolean;
        token_configured: boolean;
        encoding_aes_key_configured: boolean;
        staff_id_configured: boolean;
        robot_webhook_configured: boolean;
      };
    };
    api: {
      admin_token_configured: boolean;
      deepseek_api_key_configured: boolean;
      deepseek_base_url: string;
      deepseek_model: string;
      deepseek_timeout_seconds: number;
    };
  };
}

function normalizeSettingsSummary(data: SettingsSummaryResponse["data"]): SettingsSummary {
  return {
    shop: {
      serverHost: data.shop.server_host,
      serverPort: data.shop.server_port,
      databasePath: data.shop.database_path,
      embeddingPath: data.shop.embedding_path,
      featuredProductCount: data.shop.featured_product_count,
      productTotal: data.shop.product_total,
    },
    channels: {
      youzan: {
        clientIdConfigured: data.channels.youzan.client_id_configured,
        clientSecretConfigured: data.channels.youzan.client_secret_configured,
        kdtIdConfigured: data.channels.youzan.kdt_id_configured,
        webhookTokenConfigured: data.channels.youzan.webhook_token_configured,
        mockMode: data.channels.youzan.mock_mode,
      },
      wecom: {
        corpIdConfigured: data.channels.wecom.corp_id_configured,
        agentIdConfigured: data.channels.wecom.agent_id_configured,
        secretConfigured: data.channels.wecom.secret_configured,
        tokenConfigured: data.channels.wecom.token_configured,
        encodingAesKeyConfigured: data.channels.wecom.encoding_aes_key_configured,
        staffIdConfigured: data.channels.wecom.staff_id_configured,
        robotWebhookConfigured: data.channels.wecom.robot_webhook_configured,
      },
    },
    api: {
      adminTokenConfigured: data.api.admin_token_configured,
      deepseekApiKeyConfigured: data.api.deepseek_api_key_configured,
      deepseekBaseUrl: data.api.deepseek_base_url,
      deepseekModel: data.api.deepseek_model,
      deepseekTimeoutSeconds: data.api.deepseek_timeout_seconds,
    },
  };
}

export const settingsService = {
  async getSummary(): Promise<SettingsSummary> {
    const response = await http.get<SettingsSummaryResponse>("/settings/summary");
    return normalizeSettingsSummary(response.data.data);
  },
};
