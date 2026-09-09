import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export const MEDIA = BACKEND_URL;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("snd_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

export const mediaUrl = (u) => {
  if (!u) return "";
  if (u.startsWith("http") || u.startsWith("data:")) return u;
  if (u.startsWith("/api/")) return `${MEDIA}${u}`;
  return u; // /restaurant/* served by frontend public
};
