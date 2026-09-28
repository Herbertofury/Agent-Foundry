# Minecraft Dev Kit v8 - verified behavior

Merged through PR #16 at `fdfff42799a0abef35c545a8384bb536ee1f743f`. Exact implementation head: `1cf4d02f932e2b35afdee2060e0ef13e50b5a8b7`.

All four final-head CI workflows passed: Northpoint 35963745980, Workbench 35963745982, First Run/Setup 35963746177, and Native Runtime 35963746120.

## Real native Minecraft checks

Both frozen Aoba and LibrarianTradeFinder conversions passed production Fabric 26.3: the candidate SHA-256 was checked inside Fabric, an integrated world was rendered, a server-owned block synchronized to the client, the world was saved/closed/reopened, the JVM exited, and a second JVM reopened the same save and verified persistence. Current exact logs, proof, dependency locks and native screenshots are under evidence/v8/. Aoba's menu renders its original gradient buttons/text and Singleplayer/Back navigation passes before and after process restart.

## Setup, recovery and preservation

Private Windows Python provisioning, managed JDK installation, offline verified reuse and tamper rejection passed in CI. Windows/Linux/macOS setup and the workbench workflow passed at the implementation head. The bundle preserves all 141 historical scripts/reference/assets byte-for-byte and isolates the 71 repository-tested worker files under worker/. The final package's source identity and fresh-extraction checks are recorded separately.

## Fixed visual failure

26.3 DynamicGpuData.Transform writes ModelViewMat, TextureMat, ColorModulator, ModelOffset. Legacy inline shaders placed ColorModulator at offset64, reading zero texture-matrix alpha and hiding UI despite a successful compile. The universal linked-shader rule migrates the exact four-field block, preserves all shader math, rejects unknown layouts atomically, and has a numeric regression reproducing the old transparency. All 11 affected Aoba shader stages are preserved. Real screenshots confirm the visible result in both JVMs.

## Evidence boundaries

Native automation is currently Fabric 26.3. These are recorded smoke/interaction cases, not every mod's gameplay, authenticated multiplayer, every Minecraft loader/version, or GPU-performance certification. Linux native Minecraft and cross-platform setup are different proof scopes. Historical v7 evidence is retained as history, not current v8 proof.

## Final distributable check

Extracted the packaged skill into a fresh directory containing spaces. The root doctor/help launchers, shader regression, independent-restart harness regression, and real Java compiler/JAR/JVM build-resume-recovery-package workflow all exited 0. Full command output and durations are in evidence/v8/final-fresh-extraction/. Final metadata-only repack preserves every worker byte used by this smoke test.

The full release includes the exact CI-tested Enderloom source snapshot at `beaa269a72091cc76f255c060a085339d8725988`, not a claim that its entire repository tree equals the actual merge. Concurrent main-only documentation and knowledge updates are retained in the merged repository and do not change the tested Dev Kit worker.
