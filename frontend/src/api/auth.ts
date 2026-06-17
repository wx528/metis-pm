import { api } from "./client";
export const authApi = { health: () => api.get("/auth/health") };
