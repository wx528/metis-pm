import { api } from "./client";

export const authApi = {
  login: (password: string) =>
    api.post<{ token: string; sub: string; role: string }>("/auth/login", { password }),
  me: () => api.get<{ sub: string; role: string }>("/auth/me"),
};
