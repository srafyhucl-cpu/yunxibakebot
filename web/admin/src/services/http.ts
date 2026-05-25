import axios from "axios";

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE,
  withCredentials: true,
  timeout: 15000,
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
