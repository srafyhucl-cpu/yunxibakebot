import http from "./http";

import type { AdminProfile } from "@/stores/auth";

interface AuthMeResponse {
  ok: boolean;
  data: AdminProfile;
}

export const authService = {
  async getProfile(): Promise<AdminProfile> {
    const response = await http.get<AuthMeResponse>("/auth/me");
    return response.data.data;
  },
};
