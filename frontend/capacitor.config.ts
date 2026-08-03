import type { CapacitorConfig } from "@capacitor/cli";

// Provisional identifier for internal testing. Confirm the final publisher and
// bundle identifier in the signed CTU IP agreement before creating store records.
const config: CapacitorConfig = {
  appId: "io.github.thuyhuongctu.maida",
  appName: "M-AIDA Research",
  webDir: "build",
  loggingBehavior: "none",
  android: {
    allowMixedContent: false,
    backgroundColor: "#f7f9fc",
  },
  ios: {
    backgroundColor: "#f7f9fc",
    contentInset: "automatic",
  },
};

export default config;
