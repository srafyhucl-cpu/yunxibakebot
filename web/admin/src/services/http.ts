import axios from "axios";

/** 管理员 Token 在 localStorage 中的存储键名 */
const TOKEN_STORAGE_KEY = "admin_token";

/** 从 localStorage 读取管理员 Token（Cookie 已设为 httponly，JS 无法读取） */
export function getStoredToken(): string {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || "";
}

/** 登录成功后将 Token 持久化到 localStorage */
export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

/** 退出时清除 localStorage 中的 Token */
export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
  withCredentials: true,
  timeout: 60000,
});

http.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers ?? {};
    if (!config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = String(error.config?.url || "");
    const routerBase = import.meta.env.VITE_ROUTER_BASE;
    const isProfileCheck = /(?:^|\/)me(?:\?|$)/.test(requestUrl);
    const isLoginPage = window.location.pathname === `${routerBase}login`;

    if (error.response?.status === 401 && !isProfileCheck && !isLoginPage) {
      const currentPath = window.location.pathname.startsWith(routerBase)
        ? window.location.pathname.slice(routerBase.length - 1)
        : window.location.pathname;
      const redirect = `${currentPath}${window.location.search}`;
      window.location.href = `${routerBase}login?redirect=${encodeURIComponent(redirect)}`;
    }
    return Promise.reject(error);
  },
);

export default http;
