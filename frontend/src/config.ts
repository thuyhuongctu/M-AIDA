import { Capacitor } from "@capacitor/core";

export type ReleaseChannel = "development" | "internal" | "store";

const releaseChannel: ReleaseChannel =
  import.meta.env.VITE_RELEASE_CHANNEL ??
  (import.meta.env.DEV ? "development" : "internal");

const apiUrl = (import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8765" : ""))
  .trim()
  .replace(/\/$/, "");

const rightsStatus =
  import.meta.env.VITE_RIGHTS_STATUS ?? "pending-ctu-agreement";

export const runtimeConfig = {
  apiUrl,
  appVersion: import.meta.env.VITE_APP_VERSION ?? "7.2.0-rc.1",
  isNative: Capacitor.isNativePlatform(),
  platform: Capacitor.getPlatform(),
  privacyPolicyUrl:
    import.meta.env.VITE_PRIVACY_POLICY_URL ?? "/app-privacy.html",
  releaseChannel,
  rightsStatus,
  supportUrl: import.meta.env.VITE_SUPPORT_URL ?? "/app-support.html",
  storePublicationAllowed:
    releaseChannel === "store" && rightsStatus === "ctu-agreement-signed",
} as const;

if (
  releaseChannel === "store" &&
  (!apiUrl.startsWith("https://") || rightsStatus !== "ctu-agreement-signed")
) {
  throw new Error(
    "Unsafe store configuration: an HTTPS API and signed CTU rights status are required."
  );
}
