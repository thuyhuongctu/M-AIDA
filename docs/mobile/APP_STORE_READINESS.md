# M-AIDA mobile release readiness

Status: internal release candidate only. Public distribution is blocked.

The native projects wrap the React research workflow with Capacitor 8. M-AIDA v7.1.1 remains the frozen registered/citable research baseline; the mobile package is a v7.2.0 release candidate and does not alter that baseline.

## Release gates

| Gate | Internal build | Store build |
|---|---:|---:|
| Capacitor Android/iOS projects build | Required | Required |
| Physical-device test matrix complete | Recommended | Required |
| Signed CTU IP/commercialization agreement | Not asserted | Required |
| Final publisher and bundle ID confirmed | Provisional | Required |
| Production HTTPS API and CORS policy approved | Optional | Required |
| Production access model, tenant isolation, authorization, rate limits, and security review approved | Not implemented | Required |
| Privacy policy and retention schedule approved | Draft | Required |
| Apple privacy answers / Google Data safety approved | Draft | Required |
| Support owner and escalation channel active | Draft | Required |
| Store text, screenshots, and review notes approved | Draft | Required |

Run `npm run mobile:check` for an internal project check. `npm run mobile:release-check` is intentionally fail-closed and passes only when every approval is explicitly supplied as an environment variable. See `.env.store.example`.

## Platform baseline

- Capacitor 8 requires Node.js 22 or newer.
- Android compiles and targets API 36; Google Play requires new submissions and updates to target Android 16 / API 36 from August 31, 2026.
- Android release traffic is cleartext-disabled and app backup is disabled.
- iOS includes an app-level privacy manifest, in addition to SDK manifests.
- CI builds the unsigned iOS app for a generic simulator on a GitHub-hosted macOS runner. A signed archive and App Store validation still require the final Apple team, bundle ID, signing assets, and release approvals.
- Native network status and the system share sheet provide device integration beyond a static website wrapper.
- The backend allows the standard Capacitor WebView origins (`http://localhost` on Android and `capacitor://localhost` on iOS); production CORS must remain an explicit allow-list.

## Build workflow

1. `cd frontend && npm ci`
2. `npm run typecheck && npm run test:mobile`
3. `npm run mobile:check`
4. Set `VITE_API_URL` to an approved HTTPS API reachable from the test device, then run `npm run mobile:sync`. A build with no endpoint is intentionally useful only for UI/offline-state review.
5. After all approvals are real, populate the release environment and run `npm run mobile:prepare:store`. This command will stop before syncing if any release gate is missing.
6. Android: open Android Studio with `npm run mobile:open:android`; produce a signed Android App Bundle only after the release gate passes.
7. iOS: on macOS with current Xcode, use `npm run mobile:open:ios`; archive and validate only after the release gate passes.

Never commit signing keys, provisioning profiles, store API keys, backend secrets, or production environment files.

## Authoritative requirements checked

- [Google Play target API requirements](https://developer.android.com/google/play/requirements/target-sdk)
- [Android App Bundle](https://developer.android.com/guide/app-bundle)
- [Google Play Data safety](https://support.google.com/googleplay/android-developer/answer/10787469)
- [Google Play account deletion](https://support.google.com/googleplay/android-developer/answer/13327111)
- [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Apple app review preparation](https://developer.apple.com/distribute/app-review/)
- [Apple app privacy details](https://developer.apple.com/app-store/app-privacy-details/)
- [Apple privacy manifests](https://developer.apple.com/documentation/bundleresources/privacy-manifest-files)
- [Capacitor configuration and security guidance](https://capacitorjs.com/docs/config)
