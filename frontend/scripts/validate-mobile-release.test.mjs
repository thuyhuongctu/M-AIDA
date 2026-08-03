import assert from "node:assert/strict";
import { test } from "node:test";
import { validateMobileRelease } from "./validate-mobile-release.mjs";

const approved = {
  MAIDA_RIGHTS_STATUS: "ctu-agreement-signed",
  MAIDA_BUNDLE_ID_CONFIRMED: "true",
  MAIDA_BACKEND_SECURITY_APPROVED: "true",
  MAIDA_DATA_DISCLOSURE_APPROVED: "true",
  MAIDA_STORE_LISTING_APPROVED: "true",
  VITE_API_URL: "https://api.example.edu",
  VITE_PRIVACY_POLICY_URL: "https://example.edu/privacy",
  VITE_SUPPORT_URL: "https://example.edu/support",
  VITE_RELEASE_CHANNEL: "store",
  VITE_RIGHTS_STATUS: "ctu-agreement-signed",
};

test("internal project check does not assert store approvals", () => {
  const result = validateMobileRelease({ env: {}, store: false });
  assert.equal(result.failures.length, 0);
  assert.match(result.notices[0], /Internal build only/);
});

test("store release remains blocked while the CTU agreement is pending", () => {
  const result = validateMobileRelease({
    env: { ...approved, MAIDA_RIGHTS_STATUS: "pending-ctu-agreement" },
    store: true,
  });
  assert.ok(result.failures.some((failure) => failure.includes("signed CTU IP agreement")));
});

test("store release rejects insecure endpoints", () => {
  const result = validateMobileRelease({
    env: { ...approved, VITE_API_URL: "http://api.example.edu" },
    store: true,
  });
  assert.ok(result.failures.some((failure) => failure.includes("VITE_API_URL")));
});

test("store release rejects placeholder domains", () => {
  const result = validateMobileRelease({
    env: { ...approved, VITE_SUPPORT_URL: "https://support.example.invalid" },
    store: true,
  });
  assert.ok(result.failures.some((failure) => failure.includes("VITE_SUPPORT_URL")));
});

test("store release passes when every approval is explicit", () => {
  const result = validateMobileRelease({ env: approved, store: true });
  assert.deepEqual(result.failures, []);
});
