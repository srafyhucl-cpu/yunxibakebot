import axios from "axios";

function readCookie(name: string): string {
  const prefix = `${name}=`;
  const segments = document.cookie.split(";").map((item) => item.trim());
  const matched = segments.find((item) => item.startsWith(prefix));
  return matched ? decodeURIComponent(matched.slice(prefix.length)) : "";
}

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
  withCredentials: true,
  timeout: 15000,
});

http.interceptors.request.use((config) => {
  const token = readCookie("admin_token");
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
    const isProfileCheck = requestUrl.includes("/auth/me");
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
