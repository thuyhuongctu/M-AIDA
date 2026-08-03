import { existsSync, readFileSync } from "node:fs";
import process from "node:process";

const REQUIRED_PROJECT_FILES = [
  "capacitor.config.ts",
  "android/app/build.gradle",
  "ios/App/App/Info.plist",
  "ios/App/App/PrivacyInfo.xcprivacy",
];

function isHttps(value = "") {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.hostname.endsWith(".invalid");
  } catch {
    return false;
  }
}

export function validateMobileRelease({ env = process.env, store = false } = {}) {
  const failures = [];
  const notices = [];
  const nodeMajor = Number(process.versions.node.split(".")[0]);

  if (nodeMajor < 22) failures.push("Node.js 22 or newer is required by Capacitor 8.");
  for (const file of REQUIRED_PROJECT_FILES) {
    if (!existsSync(file)) failures.push(`Missing native project file: ${file}`);
  }

  const capacitorConfig = existsSync("capacitor.config.ts")
    ? readFileSync("capacitor.config.ts", "utf8")
    : "";
  if (!/appId:\s*["'][a-zA-Z][\w]*(?:\.[\w]+){2,}["']/.test(capacitorConfig)) {
    failures.push("Capacitor appId must be a valid reverse-domain identifier.");
  }

  const androidVariables = existsSync("android/variables.gradle")
    ? readFileSync("android/variables.gradle", "utf8")
    : "";
  const androidManifest = existsSync("android/app/src/main/AndroidManifest.xml")
    ? readFileSync("android/app/src/main/AndroidManifest.xml", "utf8")
    : "";
  const privacyManifest = existsSync("ios/App/App/PrivacyInfo.xcprivacy")
    ? readFileSync("ios/App/App/PrivacyInfo.xcprivacy", "utf8")
    : "";

  if (!/compileSdkVersion\s*=\s*36/.test(androidVariables)) {
    failures.push("Android compileSdkVersion must equal 36.");
  }
  if (!/targetSdkVersion\s*=\s*36/.test(androidVariables)) {
    failures.push("Android targetSdkVersion must equal 36.");
  }
  if (!/android:usesCleartextTraffic="false"/.test(androidManifest)) {
    failures.push("Android cleartext network traffic must remain disabled.");
  }
  if (!/android:allowBackup="false"/.test(androidManifest)) {
    failures.push("Android application backup must remain disabled.");
  }
  if (
    !privacyManifest.includes("<key>NSPrivacyTracking</key>") ||
    !privacyManifest.includes("<false/>")
  ) {
    failures.push("iOS privacy manifest must explicitly declare tracking behavior.");
  }

  if (store) {
    const requiredFlags = [
      ["MAIDA_RIGHTS_STATUS", "ctu-agreement-signed", "signed CTU IP agreement"],
      ["MAIDA_BUNDLE_ID_CONFIRMED", "true", "final bundle identifier ownership"],
      ["MAIDA_BACKEND_SECURITY_APPROVED", "true", "production access model and backend security review"],
      ["MAIDA_DATA_DISCLOSURE_APPROVED", "true", "privacy/data-safety disclosure"],
      ["MAIDA_STORE_LISTING_APPROVED", "true", "store listing and screenshots"],
    ];

    for (const [key, expected, label] of requiredFlags) {
      if (env[key] !== expected) failures.push(`Approval missing: ${label} (${key}).`);
    }
    if (!isHttps(env.VITE_API_URL)) failures.push("VITE_API_URL must be an HTTPS URL.");
    if (!isHttps(env.VITE_PRIVACY_POLICY_URL)) {
      failures.push("VITE_PRIVACY_POLICY_URL must be a public HTTPS URL.");
    }
    if (!isHttps(env.VITE_SUPPORT_URL)) {
      failures.push("VITE_SUPPORT_URL must be a public HTTPS URL.");
    }
    if (env.VITE_RELEASE_CHANNEL !== "store") {
      failures.push("VITE_RELEASE_CHANNEL must equal store.");
    }
    if (env.VITE_RIGHTS_STATUS !== "ctu-agreement-signed") {
      failures.push("VITE_RIGHTS_STATUS must equal ctu-agreement-signed.");
    }
  } else {
    notices.push("Internal build only; store-publication approvals were not asserted.");
  }

  return { failures, notices };
}

if (process.argv[1]?.endsWith("validate-mobile-release.mjs")) {
  const store = process.argv.includes("--store");
  const { failures, notices } = validateMobileRelease({ store });
  for (const notice of notices) console.log(`NOTICE: ${notice}`);
  if (failures.length) {
    for (const failure of failures) console.error(`BLOCKED: ${failure}`);
    process.exitCode = 1;
  } else {
    console.log(store ? "Store release gate passed." : "Mobile project checks passed.");
  }
}
