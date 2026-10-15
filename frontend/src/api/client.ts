import axios from "axios";
import {
  createLoginRedirectUrl,
  shouldRedirectToLogin,
} from "./authRedirect";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true,
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const requestUrl = String(error.config?.url ?? "");

    if (
      shouldRedirectToLogin(
        status,
        requestUrl,
        window.location.pathname,
      )
    ) {
      const currentPath =
        window.location.pathname +
        window.location.search +
        window.location.hash;

      window.location.assign(
        createLoginRedirectUrl(currentPath, window.location.origin),
      );
    }

    return Promise.reject(
      error.response?.data?.detail || error.message,
    );
  },
);

export default client;
