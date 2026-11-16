import {
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signOut,
  type User,
  sendPasswordResetEmail,
} from "firebase/auth";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { auth } from "../firebase";
import { AuthContext, type AuthContextValue } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    void setPersistence(auth, browserLocalPersistence).catch(() => {
      if (active) {
        setLoading(false);
      }
    });

    const unsubscribe = onAuthStateChanged(auth, (nextUser) => {
      if (active) {
        setUser(nextUser);
        setLoading(false);
      }
    });

    return () => {
      active = false;
      unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => {
        await signInWithEmailAndPassword(auth, email, password);
      },
      register: async (email, password) => {
        await createUserWithEmailAndPassword(auth, email, password);
      },
      logout: async () => {
        await signOut(auth);
      },
      resetPassword: async (email) => {
        await sendPasswordResetEmail(auth, email);
      },
    }),
    [loading, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
