import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY || "metis-pm-default-key-change-me";

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
  },
});
