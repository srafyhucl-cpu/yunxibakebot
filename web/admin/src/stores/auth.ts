import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { authService } from "@/services/auth";

export interface AdminProfile {
  name: string;
  role: string;
}

export const useAuthStore = defineStore("auth", () => {
  const profile = ref<AdminProfile | null>(null);
  const loading = ref(false);
  const initialized = ref(false);

  const isLoggedIn = computed(() => profile.value !== null);

  async function fetchProfile() {
    loading.value = true;
    try {
      profile.value = await authService.getProfile();
    } finally {
      loading.value = false;
      initialized.value = true;
    }
  }

  function clearProfile() {
    profile.value = null;
    initialized.value = true;
  }

  return {
    profile,
    loading,
    initialized,
    isLoggedIn,
    fetchProfile,
    clearProfile,
  };
});
