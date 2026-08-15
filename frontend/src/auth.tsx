import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken } from "./api";
import type { User } from "./types";

const UserContext = createContext<{ user: User | null; refresh: () => void }>({
  user: null,
  refresh: () => {},
});

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    // Sans token (page de login), ne PAS appeler /auth/me : le 401 déclencherait
    // une redirection → rechargement → boucle infinie.
    if (!getToken()) return;
    api.get<User>("/auth/me").then(setUser).catch(() => {});
  }, []);
  return (
    <UserContext.Provider
      value={{
        user,
        refresh: () => {
          if (!getToken()) return;
          api.get<User>("/auth/me").then(setUser).catch(() => {});
        },
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
