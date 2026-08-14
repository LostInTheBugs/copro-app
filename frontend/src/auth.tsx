import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";
import type { User } from "./types";

const UserContext = createContext<{ user: User | null; refresh: () => void }>({
  user: null,
  refresh: () => {},
});

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    api.get<User>("/auth/me").then(setUser).catch(() => {});
  }, []);
  return (
    <UserContext.Provider value={{ user, refresh: () => api.get<User>("/auth/me").then(setUser).catch(() => {}) }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
