/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_RELEASE_CHANNEL?: "development" | "internal" | "store";
  readonly VITE_RIGHTS_STATUS?: "pending-ctu-agreement" | "ctu-agreement-signed";
  readonly VITE_PRIVACY_POLICY_URL?: string;
  readonly VITE_SUPPORT_URL?: string;
  readonly VITE_APP_VERSION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
