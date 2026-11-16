import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const requiredConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const missingConfig = Object.entries(requiredConfig)
  .filter(([, value]) => !value)
  .map(([key]) => key);

if (missingConfig.length > 0 && import.meta.env.DEV) {
  console.warn(
    `Firebase configuration is missing: ${missingConfig.join(", ")}. ` +
      "Add the VITE_FIREBASE_* values to frontend/.env.local."
  );
}

const firebaseApp = initializeApp(requiredConfig);
export const auth = getAuth(firebaseApp);
