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
    if (error.response?.status === 401) {
      window.location.href = `${import.meta.env.VITE_ROUTER_BASE}login`;
    }
    return Promise.reject(error);
  },
);

export default http;
