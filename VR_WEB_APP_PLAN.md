# F1 Hot-Lap → Web/VR Replay App — Engine, Cost & Roadmap Plan

**Date:** 2026-05-10
**Author:** drafted with Claude Opus 4.7 (web-sourced; verify pricing before committing)
**Scope:** decide between Unity 6 and Unreal Engine 5.5/5.6 for a web app where users pick driver + track + year + lap and get a real-time VR lap-comparison replay, building on the existing Blender addon's telemetry-driven animation pipeline.

---

## 0. TL;DR — The actual recommendation

> **Don't pick Unity *or* Unreal as a binary.** The right answer is a hybrid that uses **client-side 3D Gaussian Splatting + Three.js (or PlayCanvas / Babylon)** for the long tail, and **a small Unreal Engine pixel-streaming pool** only for the "cinematic" / hero path. Engine choice for the cinematic path is **Unreal 5.5+**, primarily because:
>
> 1. **Lumen and Nanite are unavailable on Quest standalone for both engines.** ([Road to VR](https://www.roadtovr.com/meta-quest-unreal-engine-5-support-lumen-nanite/), [Epic forums](https://forums.unrealengine.com/t/lumen-with-meta-quest/1315397)). On Quest you ship URP-class fidelity regardless of which engine you pick — so engine choice is decided by the *cloud-rendered cinematic path*, not the Quest path.
> 2. **Unreal Pixel Streaming is the only mature, GA, cloud-render-to-browser pipeline with managed providers (Vagon, Eagle3D, Pureweb, AWS GameLift Streams).** Unity Render Streaming exists but is far less production-tested.
> 3. **Quixel/Megascans/RealityScan integration** is far cheaper inside the Unreal toolchain in 2026 — the perpetual-license catalog of free Megascans assets you already have stays usable forever ([Quixel news](https://quixel.com/en-US/news/quixel-on-fab-new-megascans-and-megaplants)).
>
> **For the client-side VR path on Quest 3,** ship a native Quest APK or WebXR experience that renders 3D-Gaussian-splat tracks + traditional mesh F1 cars. Use **Spark 2.0** (WebGL2, streaming LoD, VR-ready, [worldlabs.ai](https://www.worldlabs.ai/blog/spark-2.0)) or **SuperSplat** ([thefuture3d](https://www.thefuture3d.com/software/supersplat/)). This is genuinely the cheaper and more photoreal path in 2026.
>
> **POC in 8–10 weeks. Beta in 4 months. Scale at 10k MAU for ~$300–$3k/month** depending on how aggressively you pre-bake replays vs. live-render.

The rest of this doc is the evidence.

---

## 1. The system we're building

User flow:

```
[Web UI]  pick year → race → driver(s) → lap
   ↓
[Backend]  pull FastF1 telemetry, pre-process (already built in Blender addon)
   ↓
[Renderer]  EITHER  client-side WebGPU/WebGL2 + 3DGS  (cheap path)
            OR      cloud Pixel Streaming UE5         (premium path)
            OR      pre-baked HLS video               (long-tail path)
   ↓
[Display]  flat-screen browser, WebXR Quest browser, OR native Quest app
```

The Blender addon already produces deterministic, telemetry-driven car animation. The job of the runtime engine is:
- Render the **track environment** photoreally
- Render **multiple cars** with synced telemetry (we already have the data pipeline)
- Run at **VR framerates (90 fps both eyes)** when in VR mode
- Stream or load fast in the browser

That's a different problem from "build a sim-racing game" — the *physics* is solved (it's recorded telemetry). What we need is a **photoreal data-driven replay viewer**, which has lighter engine demands than people typically assume.

---

## 2. Unity 6 vs Unreal Engine 5.5/5.6 — the comparison the question asked for

### 2.1 Rendering quality at VR framerates (Quest 3 standalone)

| | Unity 6 | UE 5.5 / 5.6 |
|---|---|---|
| Pipeline for Quest standalone | **URP** (HDRP not viable on mobile VR, [Unity discussions](https://discussions.unity.com/t/terrible-build-performance-on-quest-3-with-urp-and-meta-sdk-conflicting-information-in-meta-documentation/1598096)) | **Mobile Forward+** (Lumen/Nanite disabled on mobile, [Road to VR](https://www.roadtovr.com/meta-quest-unreal-engine-5-support-lumen-nanite/)) |
| Lumen-equivalent on Quest | None (URP uses baked GI) | None — Epic explicitly: "no plans to develop a dynamic GI system for the mobile renderer" ([Epic forums](https://forums.unrealengine.com/t/lumen-with-meta-quest/1315397)) |
| Nanite on Quest | N/A | Not supported on mobile, no Android plan |
| 90 fps headroom on Quest 3 | Mature: many shipping titles | Less battle-tested for Quest standalone; UE community guides strongly recommend baked lighting + Mobile Forward+ ([StraySpark guide](https://www.strayspark.studio/blog/vr-game-development-meta-quest-ue5-2026)) |
| 2026 strategic direction | Unity is **doubling down on URP** — HDRP only gets maintenance + Switch 2 work in 2026 ([Unity discussions strategy thread](https://discussions.unity.com/t/render-pipelines-strategy-for-2026/1710004/print)) | UE5 mobile renderer continues to improve but Lumen/Nanite stay desktop/PCVR only |

**Bottom line on Quest standalone:** both engines look about the same on-headset because both are forced into baked-lighting forward renderers. **You will not get "Unreal photoreal" on Quest 3 in 2026** with either engine. The photoreal-on-Quest path is **3D Gaussian Splatting**, not the engine's renderer.

### 2.2 PCVR and cloud-rendered modes

This is where Unreal pulls ahead. Lumen and Nanite *do* work in PCVR rendered scenes (and therefore in cloud-streamed scenes if we're willing to accept the latency for non-VR clients). Real PCVR demos at 90 fps with Lumen + Nanite have shipped on RTX 3080-class hardware ([UploadVR](https://www.uploadvr.com/unreal-engine-5-lumen-nanite-vr/)).

For our cinematic / cloud-streaming path: **Unreal wins**.

### 2.3 VR development workflow

Both engines have OpenXR-based VR templates. Specifics:

- **Unity** — XR Interaction Toolkit (mature, widely used), Meta XR SDK plug-in. Quest hand-tracking + passthrough have stable Unity bindings.
- **Unreal** — VR Template + Meta XR plugin. Hand-tracking and passthrough are well-supported but the Unity ecosystem has more shipped Quest titles.

Tie. For a *replay* app (no complex interaction loop), this matters less than the rendering question.

### 2.4 Web/browser delivery — this is where the answer changes

| Path | Unity 6 | UE 5.5/5.6 |
|---|---|---|
| WebGL build for browser flat-screen | Yes; **WebGPU still experimental in Unity 6.1** ([Unity manual](https://docs.unity3d.com/6000.3/Documentation/Manual/WebGPU.html)). Hard ~2 GB heap cap; ~512 MB iOS Safari. Not for ultra-photoreal. | Not really. Epic stopped serious WebGL work years ago. |
| Pixel Streaming (cloud render → browser) | Unity Render Streaming exists, less mature. | **Production-grade**, used at scale, multiple managed providers. |
| WebXR for Quest browser | Yes via [De-Panther/unity-webxr-export](https://github.com/De-Panther/unity-webxr-export) (community). Works. | No production-grade story. |
| Native Quest APK | Yes, mature. | Yes, mature. |

**Big takeaway:** if you want a "browser-based" experience without forcing the user to install anything, the only real options are (a) pixel-streaming an Unreal scene, or (b) a custom Three.js / PlayCanvas / Babylon.js viewer with WebGPU + 3DGS. Unity WebGL is *third* and not really a contender at the photoreal end.

### 2.5 Scripting / data ingestion

Both engines load CSV/JSON telemetry trivially. C# vs C++/Blueprints is a team-skill question. Existing addon is Python — neither engine helps directly, but Unity's C# is simpler for porting Python animation logic. Tie, slight edge to Unity for engineer ergonomics.

### 2.6 Licensing economics (2026)

| Cost item | Unity 6 | UE 5.5/5.6 |
|---|---|---|
| Free tier threshold | < $200k revenue/funding (Personal) | < $1M revenue (free, no royalty) |
| Pro/Studio price | **Pro $2,200/seat/year × 1.05 ≈ $2,310/seat/year from Jan 12 2026** ([Unity support](https://support.unity.com/hc/en-us/articles/30322080156692-Cancellation-of-the-Runtime-Fee-and-Pricing-Changes), [Unity blog](https://unity.com/products/pricing-updates)) | **No per-seat fee** — 5% royalty above $1M lifetime revenue. |
| Required at $25M revenue | Unity Enterprise (custom price, +25% increase 2024) | Same 5% royalty |
| Quixel/Megascans | Buy on Fab.com (mostly paid since 2025, [80.lv](https://80.lv/articles/epic-games-to-launch-tool-for-free-megascans-downloads-in-fab)). | Same Fab marketplace. |
| RealityScan (photogrammetry) | $1,250/seat/year if commercial >$1M ([RealityScan](https://www.realityscan.com/news/realityscan-20-new-release-brings-powerful-new-features-to-a-rebranded-realitycapture)) | Same |

For an indie team building this: **Unreal is materially cheaper while you're under $1M revenue**. Once over $1M, the 5% royalty starts compounding — a $5M revenue product pays Epic ~$200k/yr (vs. small revenue pays Unity ~$2.3k × N seats — typically ~$10–30k for a small team). Cross-over is around $1.5–2M revenue depending on team size.

### 2.7 Asset ecosystem

| | Unity | Unreal |
|---|---|---|
| Marketplace | Unity Asset Store (still active) | **Fab.com** — unified post Quixel/Megascans/Sketchfab merger |
| Free assets in 2026 | Limited free curation | ~800 free Megascans assets remain ([Quixel](https://quixel.com/en-US/news/quixel-on-fab-new-megascans-and-megaplants)); perpetual license once acquired |
| Photogrammetry pipeline | Decent | **Best-in-class** (Epic owns RealityCapture/RealityScan) |
| F1 / racing track assets | Few clean ones | Few clean ones — see §4 on IP risk |

### 2.8 Verdict table

| If primary target is… | Pick | Because |
|---|---|---|
| **Quest 3 standalone, photoreal-by-rendering** | Neither — it's not possible at AAA quality. Pick **3DGS + Three.js** | Lumen/Nanite blocked on mobile; URP/Forward+ ceilings are similar |
| **PCVR / cloud cinematic mode at AAA quality** | **Unreal 5.5+** | Lumen + Nanite in PCVR; Pixel Streaming production-grade; cheaper licensing under $1M |
| **Browser flat-screen, server-rendered** | **Unreal Pixel Streaming** | Mature, multiple managed providers, AV1 on L40S |
| **Browser flat-screen, client-rendered** | **Three.js / Babylon / PlayCanvas + 3DGS** (skip game engines) | No 4 GB heap cap, runs WebGPU natively, smallest runtime |
| **Easiest team onboarding (Python/C# devs)** | Unity 6 | C# > C++/Blueprints for telemetry-driven animation |
| **Largest existing free asset base** | Unreal | Free Megascans tail + perpetual licenses |

---

## 3. The real architecture question: Server-render vs. Client-render vs. Pre-bake

Engine wars matter less than where the GPU work happens. Three architectures, with concrete economics:

### 3.1 Architecture A — Pure Pixel Streaming (premium path)

UE5 runs headless on a cloud GPU, streams WebRTC video to browser. Latency 60–110 ms motion-to-photon — **fine for flat-screen, unacceptable for VR head-tracking** (need <20 ms or aggressive Async Time Warp). Epic does not list any HMD as a supported PS client.

**Economics:** Pixel Streaming is fundamentally **1 UE process : 1 GPU encoder : 1 user** at 1080p60. NVIDIA lifted consumer NVENC session caps in R550+ drivers (mid-2024) so an L4/L40S can drive multiple streams, but each needs its own UE instance + VRAM slice.

### 3.2 Architecture B — Client-side WebGPU / WebGL2 + 3DGS (cheapest path)

Static track captured as 3D-Gaussian-splat (~50 MB compressed with Self-Organizing Gaussians, [arxiv 2312.13299](https://arxiv.org/abs/2312.13299)), cars stay as PBR meshes from the existing pipeline, everything renders on the user's device.

- **Spark 2.0** (released April 2026, [worldlabs.ai](https://www.worldlabs.ai/blog/spark-2.0)) explicitly supports streaming LoD splats on **WebGL2 — chosen over WebGPU for compatibility**. Runs on desktop, iOS, Android, *and VR*.
- **SuperSplat + SOGS format** ([thefuture3d](https://www.thefuture3d.com/software/supersplat/)) handles 10M+ Gaussian scenes with progressive streaming.
- WebGPU itself shipped in Chrome (long ago), Firefox 141 (Win) / 145 (Mac), Safari 26.0 (incl. visionOS) — but Linux still gappy ([webgpu.com](https://www.webgpu.com/news/webgpu-hits-critical-mass-all-major-browsers/)). For our app, WebGL2 + Spark is more universal.

This architecture is *more photoreal than Unreal-on-Quest* because the splat captures real-world appearance, and *cheaper than Pixel Streaming* because there's no GPU server.

### 3.3 Architecture C — Pre-baked HLS for the long tail

23 circuits × 20 drivers × ~24 races × ~60 laps ≈ 28k unique laps/season. Render each once on spot GPUs, store as HLS on Cloudflare R2 (zero egress), serve like a normal video for "casual" viewers. Live-render only fires when the user hits "interactive mode."

This single lever is **the biggest cost saver** — moves 80–95% of the GPU work from per-stream live render to a one-time bake.

### 3.4 Recommended mix

```
Free tier              → pre-baked HLS (Architecture C)
Logged-in/Pro          → client-side WebGPU + 3DGS (Architecture B)
"Cinematic"/VIP mode   → pixel-streamed UE5 (Architecture A)
```

---

## 4. Photoreal F1 environments — cheapest path to "good enough"

### 4.1 The 3DGS-first strategy

For each circuit:
1. Drone-capture flyover (or buy existing scans / use OpenStreetMap+Mapbox satellite as fallback)
2. Train **Scaffold-GS** ([arxiv 2312.00109](https://arxiv.org/abs/2312.00109)) with anchor-grid for ~5× fewer Gaussians than vanilla 3DGS
3. Apply **Mip-Splatting** ([arxiv 2311.16493](https://arxiv.org/abs/2311.16493)) for clean broadcast zoom
4. Compress with **Self-Organizing Gaussians** ([arxiv 2312.13299](https://arxiv.org/abs/2312.13299)) → ~50 MB delivery
5. Optionally chunk with **Hierarchical 3DGS** ([arxiv 2406.12080](https://arxiv.org/abs/2406.12080)) for kilometre-scale streaming

Recent 2025 papers extending this:
- **LODGE** — Level-of-Detail large-scale GS with efficient rendering ([arxiv 2505.23158](https://arxiv.org/abs/2505.23158))
- **Horizon-GS** — aerial-to-ground unification, perfect for circuit scans
- **SfM-Free hierarchical GS** — skip the structure-from-motion preprocessing (CVPR 2025)

### 4.2 Photogrammetry costs in 2026

- **RealityScan 2.0** is **free** for individuals/companies under $1M revenue ([RealityScan news](https://www.realityscan.com/news/realityscan-20-new-release-brings-powerful-new-features-to-a-rebranded-realitycapture)) — that's our case. Otherwise $1,250/seat/yr or PPI ~$0.01/image.
- Drone hardware: $2k–$20k buys a competent mapping drone ([Power KH](https://www.powerkh.com/how-much-reality-capture-cost/)).
- Total project cost: medium-sized landscape project $5k–$20k; large/complex $20k–$1M+.

### 4.3 Realistic per-circuit cost tiers

| Tier | Method | Per circuit | All 23 circuits |
|---|---|---|---|
| **Procedural** | OSM + SRTM elevation + Houdini/UE PCG | ~$3–7k | $70–160k |
| **Photogrammetry-aided** (recommended) | Commission drone scan + 3DGS train | ~$15–35k | $345–805k |
| **AAA team-built** | Codemasters/iRacing equivalent | $200k+ | $4.6M+ |

**Recommendation:** start with 3 marquee circuits (Monaco, Silverstone, Suzuka or Spa) at the photogrammetry tier (~$60–100k total) for the POC. Generate the rest procedurally and replace iteratively as funding allows.

### 4.4 IP red flags (don't do these)

- **Codemasters / EA F1 game assets** — proprietary, never use.
- **iRacing laser-scan data** — proprietary; very high accuracy ([iRacing](https://www.iracing.com/track-technology/)) but not licensable.
- **Assetto Corsa / rFactor 2 community track mods** — copyright status varies wildly per mod. Don't ingest as a pipeline. Reference for layout only.
- **F1's own assets** — F1 Group + FOM hold most likeness rights. Driver/team likeness needs FOM or per-team licensing; circuit *layouts* are not copyrightable but on-trackside branding (sponsor logos, hoardings) is.

For a production launch you will need an **F1 commercial license** (FOM) for driver likenesses, team liveries, and broadcast-overlay-style graphics. Telemetry itself is publicly accessible via FastF1 — that's your moat: data is free, presentation needs a license.

---

## 5. Cost economics — the numbers that actually matter

### 5.1 Cloud GPU pricing (Q1–Q2 2026, list prices)

| Instance | GPU | On-demand $/hr | Spot $/hr typical |
|---|---|---|---|
| AWS g4dn.xlarge | T4 16GB | $0.526 | ~$0.20 |
| AWS g5.xlarge | A10G 24GB | $1.006 | ~$0.40 |
| AWS g6.xlarge | L4 24GB | $0.805 | ~$0.35 |
| AWS g6e.xlarge | L40S 48GB | $1.861 | ~$0.80 |
| Lambda Labs L4 | L4 | $0.43 | n/a |
| **AWS GameLift Streams gen6n_small** | (managed) | **$0.16/hr in us-east-2** ([AWS announcement](https://aws.amazon.com/about-aws/whats-new/2025/12/aws-gameliftstream-gen6-enhanced-autoscaling/)) | n/a |

GameLift Streams (GA March 2025; Gen6 added Dec 2025, [pricing page](https://aws.amazon.com/gamelift/streams/pricing/)) is now competitive with raw EC2 for managed cases.

### 5.2 Per-session cost (8-min lap replay average)

| Stack | Compute | Egress (10 Mbps × 8 min) | Per session |
|---|---|---|---|
| g6.xlarge spot + AV1 5 Mbps | $0.047 | $0.027 | **$0.07** |
| g5.xlarge on-demand H.264 | $0.134 | $0.054 | **$0.19** |
| GameLift Streams gen5n_high | ~$0.20 | $0.054 | **$0.25** |
| Pre-rendered HLS on R2 | ~$0.001 (storage) | **$0** (R2 free egress) | **<$0.005** |
| Client-side 3DGS render | $0 | one-time 50 MB asset download | **<$0.005** |

### 5.3 Monthly burn at scale (assume 4 sessions/MAU/month, 8 min each)

| Architecture | 1k MAU | 10k MAU | 100k MAU |
|---|---|---|---|
| All Pixel Streaming on-demand | $750 | $7,500 | $75,000 |
| All Pixel Streaming on spot | $300 | $3,000 | $30,000 |
| Hybrid (80% pre-baked, 20% live) | $80 | $700 | $7,000 |
| **All client-side 3DGS** | **$30** | **$200** | **$1,500** |
| Pure HLS (no interactivity) | $20 | $150 | $1,000 |

Storage of 28k pre-baked HLS clips at ~50 MB each ≈ 1.4 TB on Cloudflare R2 ≈ $21/month (R2 storage $0.015/GB-month).

### 5.4 Top 5 cost-reduction levers (ranked)

1. **Pre-render the long tail to HLS once** — 50–100× reduction vs. always-live. Single biggest lever.
2. **Client-side rendering for the free tier** — zero per-user GPU cost, scales for free.
3. **Spot/preemptible instances for the bake farm** — 60–70% reduction on bake cost.
4. **AV1 on L4/L40S + Cloudflare R2** — halves bandwidth, eliminates egress (often 30–50% of bill at scale).
5. **GPU bin-packing** — one g6e.xlarge L40S (48 GB) running 3 UE instances drops per-stream cost from $1.86 to $0.62/hr. Requires Lumen off + baked lighting.

---

## 6. Market landscape

### 6.1 Competitor map

| Category | Product | What it does | VR? | 3D replay? | Why we differ |
|---|---|---|---|---|---|
| **Official broadcast** | F1 TV Pro/Premium | Live + onboard + multiview, 4K UHD, 6-device multiview ([Sports Video Group](https://www.sportsvideo.org/2025/03/11/f1-tv-launches-new-f1-tv-premium-subscription-tier/)) | No | No | We do interactive 3D replay; F1 TV is broadcast video |
| **Official broadcast** | F1 Insights / Track Pulse | AWS-powered real-time graphics layer ([AWS blog](https://aws.amazon.com/blogs/media/real-time-storytelling-the-aws-architecture-behind-formula-1-track-pulse/)) | No | 2D/AR overlays | We give the viewer agency over camera + driver selection |
| **Sim-racing** | iRacing | Laser-scanned tracks, replay, full VR with foveated rendering ([iRacing track tech](https://www.iracing.com/track-technology/)) | Yes (PC) | In-app replay only, no web | Sim, not data replay; subscription gated; not F1 |
| **Sim-racing** | EA Sports F1 25 | F1 game with PC VR (Quest 3 via PCVR), no PSVR2 ([allkeyshop](https://www.allkeyshop.com/blog/f1-25-vr-performance-guide-price-comparison-news-y/)) | Yes (PC) | No real-data replay | Game, not telemetry replay |
| **Strategy game** | F1 Manager 2024 (Frontier) | "Race Replay" mode with multiple cinematic camera angles ([Formula1.com](https://corp.formula1.com/f1-manager-2024-out-now-with-new-create-a-team-mode/)) | No | Yes (3D, in-app) | Manager game, not VR, no comparison overlay |
| **Telemetry-only** | F1Laps, F1-tempo.com, FastF1 ecosystem | Charts + tables of telemetry | No | No | We render in 3D / VR |
| **Adjacent** | NFL Next Gen Stats / NBA 3D replays | AWS-powered 3D player tracking | Limited | Yes | Reference architecture, not competitor |
| **Volumetric** | Canon Free Viewpoint, Intel True View | Multi-cam volumetric capture | No | Yes (very expensive) | Stadium-bound; F1 hasn't deployed |

**No one ships what we're describing**: a *fan-controllable VR replay of any historical lap, any driver, any track, any year*, layered with comparison telemetry. F1 TV is closest in audience, F1 Manager is closest in 3D-replay UX, iRacing is closest in track quality. We sit in the gap.

### 6.2 Pricing benchmarks (what the market sustains)

- **F1 TV Premium** ~$10–12/month tier launched 2025 ([news.gp](https://www.news.gp/en/f1-tv-introduces-new-premium-subscription-for-2025-season))
- **iRacing** ~$13/month
- **EA F1 25** $69.99 one-time
- **Quest store premium experiences** $20–40 one-time
- **F1 Manager 2024** $54.99 one-time

**Recommended pricing for our app:** freemium with $7.99/month Pro (unlock 4K, all years, VR mode, advanced overlays). Lower than F1 TV because we don't have rights costs at the broadcast level.

### 6.3 White space

- **Real telemetry × photoreal VR × historical comparison** = nobody.
- Closest "vibe" reference is F1 Manager's Race Replay mode in VR, with telemetry overlays, on the web.
- Differentiators we should lean into: (a) **historical depth** (FastF1 covers 2018+ with full telemetry, expanding earlier seasons via timing tower), (b) **driver-vs-driver comparison** which the addon already produces, (c) **VR-native presentation**.

---

## 7. Latest research & open-source stack to build on

### 7.1 Top 5 papers to read first

| # | Paper | arxiv ID | Why |
|---|---|---|---|
| 1 | Hierarchical 3D Gaussian Representation for Very Large Scenes (Kerbl et al., SIGGRAPH 2024) | [2406.12080](https://arxiv.org/abs/2406.12080) | Closest to "render a 5km circuit at 90 fps" |
| 2 | Scaffold-GS (CVPR 2024) | [2312.00109](https://arxiv.org/abs/2312.00109) | Anchor-grid → ~5× fewer Gaussians |
| 3 | Mip-Splatting (CVPR 2024 best student paper) | [2311.16493](https://arxiv.org/abs/2311.16493) | Fixes zoom aliasing — broadcast camera moves require this |
| 4 | Self-Organizing Gaussians (ECCV 2024) | [2312.13299](https://arxiv.org/abs/2312.13299) | The compression paper — 1 GB → ~50 MB |
| 5 | LODGE: Level-of-Detail Large-Scale GS (CVPR 2025) | [2505.23158](https://arxiv.org/abs/2505.23158) | LoD streaming for outdoor scenes |

### 7.2 Repos to evaluate / fork

| Repo | License | What for |
|---|---|---|
| [nerfstudio-project/gsplat](https://github.com/nerfstudio-project/gsplat) | Apache-2.0 | **Drop-in CUDA splatting kernels with permissive license** (the original Inria 3DGS is research-only) |
| [graphdeco-inria/gaussian-splatting](https://github.com/graphdeco-inria/gaussian-splatting) | Inria research | Reference impl — read code, do not ship |
| [mkkellogg/GaussianSplats3D](https://github.com/mkkellogg/GaussianSplats3D) | MIT | Three.js-friendly viewer, progressive load |
| [aras-p/UnityGaussianSplatting](https://github.com/aras-p/UnityGaussianSplatting) | MIT | If we ever ship a Unity build |
| [playcanvas/supersplat](https://github.com/playcanvas/supersplat) | MIT | GS editor + SOGS format |
| [worldlabs/spark](https://www.worldlabs.ai/blog/spark-2.0) | (check at fork time) | WebGL2 LoD splat streamer with VR support |
| [city-super/Scaffold-GS](https://github.com/city-super/Scaffold-GS) | MIT | Reference Scaffold-GS |
| [fraunhoferhhi/Self-Organizing-Gaussians](https://github.com/fraunhoferhhi/Self-Organizing-Gaussians) | MIT | Compression reference |
| [dylanebert/gsplat.js](https://github.com/dylanebert/gsplat.js) | MIT | TypeScript GS renderer with ESM imports — drop-in for Vite/Next.js stacks |
| [ArthurBrussee/brush](https://github.com/ArthurBrussee/brush) | Apache-2.0 / MIT | Rust + WGPU 3DGS trainer **and** viewer; runs in browser via WebGPU; cross-platform, no CUDA required |
| [Tencent/Hunyuan3D-2](https://github.com/Tencent/Hunyuan3D-2) | Apache-2.0 | Image-to-3D mesh generator — trackside props (banners, marshal posts, advertising boards) |
| [microsoft/TRELLIS](https://github.com/microsoft/TRELLIS) | MIT | Microsoft text/image-to-3D — alternative to Hunyuan3D for prop generation |
| [theheroshep/FastF1](https://github.com/theOehrly/Fast-F1) | MIT | Already in our pipeline |

### 7.3 Cutting-edge vs. boring per subsystem

| Subsystem | Boring & reliable (ship Q3 2026) | Cutting edge (ship 2027) |
|---|---|---|
| Track environment | Photogrammetry mesh + baked lighting (RealityScan → glTF + KTX2) | Scaffold-GS / Hierarchical-3DGS + SOG compression |
| Car rendering | PBR mesh + cube-map reflections (current pipeline) | Hybrid mesh + neural decals |
| Web runtime | Three.js r170 + Draco/Meshopt + Spark 2.0 | Babylon.js 8 / PlayCanvas WebGPU |
| Cloud rendering | UE5 Pixel Streaming on g5/g6 | Foveated WebRTC + FSR3 client upscale |
| Gen-AI assets (trackside props) | **Hunyuan3D-2 (Tencent, Apache-2.0) / TRELLIS (Microsoft, MIT) / TripoSR / Meshy v4** — all production-usable for cones, banners, marshal posts | Genie-3-class scene completion (no asset-export path, too unstable) |
| Textures | Substance 3D | EverArt / Layer AI texture diffusion |
| VR streaming | Native OpenXR app, no streaming | WebXR + Async Space Warp (Meta-only) |

---

## 8. Final recommended stack

**Authoring / Backend**
- Existing Blender addon → emits `.gltf` car animation + telemetry JSON
- FastF1 → telemetry feed (already there)
- RealityScan 2.0 (free under $1M) → photogrammetry → 3DGS training pipeline
- Self-Organizing-Gaussians → compress to ~50 MB per circuit
- gsplat (Apache-2.0) → training kernels (NOT Inria's reference for shipping)

**Cinematic mode (cloud-rendered, premium)**
- Unreal Engine 5.5 + Pixel Streaming, headless on AWS g6.xlarge spot or GameLift Streams gen5n_high
- AV1 encode where possible
- Cloudflare R2 for static assets, Cloudflare Workers for signaling/matchmaking

**Standard mode (client-rendered)**
- Three.js (or PlayCanvas) + **Spark 2.0** for splats + PBR mesh cars
- Telemetry overlay drawn in HTML/CSS/SVG on top
- WebXR for Quest 3 browser entry; native Quest APK for premium

**Free mode (long-tail)**
- Pre-bake one HLS per popular driver/lap pair on spot bake farm, store on R2

**Front-end**
- Next.js / SvelteKit for the SaaS dashboard
- React Three Fiber wrapper around Three.js scene

---

## 9. Proposed timeline & milestones

### Phase 0 — Spike (2–3 weeks, weeks 1–3)

Goal: prove the riskiest assumption — "we can render a Gaussian-splat circuit + animated mesh F1 car at 60 fps in browser, and 72 fps native on Quest 3."

- [ ] Photogrammetry capture of one home-circuit corner (drive + drone, 1 hour of capture)
- [ ] Train a vanilla 3DGS, then Scaffold-GS, compare visual quality + size
- [ ] Drop into [mkkellogg/GaussianSplats3D](https://github.com/mkkellogg/GaussianSplats3D) Three.js demo
- [ ] Add a single mesh car driven by a CSV from the addon
- [ ] Test in Quest 3 browser via WebXR
- [ ] Cost: $0 (use free RealityScan tier, gsplat OSS, existing assets)

**Exit criteria:** 60 fps browser, 72+ fps Quest, splat looks "good enough" at 50 MB. If splat fails, fall back to mesh + baked lighting and downgrade fidelity expectations.

### Phase 1 — Public POC (8 weeks, weeks 4–11)

Goal: shippable demo with 3 circuits, 2 drivers, 1 race year. Public URL.

- [ ] Backend: Next.js app with circuit/driver/year/lap pickers wired to FastF1
- [ ] Asset pipeline: 3 circuits photogrammetry-scanned (Monaco, Silverstone, Spa) ≈ $45–90k commissioned, OR DIY drone capture if you have access
- [ ] Telemetry → glTF animation pipeline as a server-side job (port from Blender addon)
- [ ] Three.js viewer with telemetry overlay HUD
- [ ] WebXR mode for Quest 3
- [ ] Auth + Stripe for "Pro" gate
- [ ] Cloudflare R2 + Workers for asset delivery
- [ ] Telemetry: PostHog / Plausible
- [ ] Cost so far: $50–100k (mostly track scans), monthly burn ~$50/month at <100 users

**Exit criteria:** 100 beta testers, NPS > 30, page-1 lap completes in < 10 s on a Quest 3.

### Phase 2 — Beta (3–4 months, months 4–7)

Goal: 10 circuits, current full season + previous two, native Quest app, first paying customers.

- [ ] Add 7 more circuits (mix of photogrammetry + procedural)
- [ ] Native Quest APK (Unity 6 or Three.js + Babylon Native or Godot 4 — cheapest path)
- [ ] Pre-bake top-100 most-popular lap clips to HLS for free tier
- [ ] Cinematic mode prototype on UE5 Pixel Streaming (AWS GameLift Streams)
- [ ] FOM commercial license conversation (essential for commercial launch with driver/team likenesses) — budget legal $20–50k for outreach + initial license

**Cost so far:** $200–400k invested (assumes commissioned scans). Monthly burn at 1k MAU: $200–500.

**Exit criteria:** 1k MAU, $7.99/mo conversion ≥ 4%, F1 commercial license at least in pilot/POC stage.

### Phase 3 — Scale (6–12 months, months 8–18)

Goal: full 23-circuit season + historical depth (2018+), 10k–100k MAU, sustainable unit economics.

- [ ] All 23 circuits at procedural-or-better fidelity, 5–8 at photogrammetry tier
- [ ] FOM commercial license signed — budget $50–250k+/year depending on scope
- [ ] Cinematic mode public via Pixel Streaming pool (10–50 GPUs spot)
- [ ] Multi-region CDN
- [ ] Backend autoscaling with bake farm preempting on spot
- [ ] Apple Vision Pro port (if WebXR Safari 26 path is solid)

**Monthly burn at 10k MAU:** ~$700–3,000 depending on cinematic-mode usage.
**Monthly burn at 100k MAU:** ~$7k–30k.

**Revenue at 10k MAU @ 4% paid conversion @ $7.99 ARPU:** ~$3,200/mo. **Negative margin** until 25k+ MAU at this conversion. Push paid conversion to 8% (premium positioning, exclusive content) or push ARPU to $14.99 (cinematic-mode entitlement) to break even at 10k MAU.

---

## 10. Risk & open questions

1. **F1 commercial licensing** is the biggest unknown. Telemetry is FastF1-public, but driver names/likenesses, team liveries, and circuit branding all touch FOM/team rights. **De-risk early** — get a yes/no from FOM before Phase 2 so you don't build something un-shippable.
2. **3DGS-on-Quest standalone** at 72 fps with 50 MB scenes is plausible but not yet shipping in production VR titles I can find — the spike in Phase 0 must validate it. Fallback: render to flat WebXR (no headlock) at lower fidelity.
3. **Photogrammetry of active F1 circuits** typically requires venue permission. Cheaper substitute: capture during track-day windows, or partner with circuit owners (some are willing for marketing exposure).
4. **Cinematic-mode VR is hard.** Pixel Streaming does not solve VR head tracking. If the cinematic mode must run in VR, plan for native Quest builds with downloaded high-quality assets, not streaming.
5. **AV1 encoding requires L4/L40S** — not all spot capacity has it. Plan H.265 fallback.
6. **F1 schedule churn.** Tracks rotate; budget asset capture for new venues annually (Las Vegas, Miami, etc. were recent additions).

---

## Sources (verify before quoting)

**Engine comparison & VR**
- Unreal forums: [Lumen with Meta Quest](https://forums.unrealengine.com/t/lumen-with-meta-quest/1315397)
- Road to VR: [Meta Quest gets UE5 minus two headlining features](https://www.roadtovr.com/meta-quest-unreal-engine-5-support-lumen-nanite/)
- UploadVR: [UE5 Lumen & Nanite now work with high-end VR](https://www.uploadvr.com/unreal-engine-5-lumen-nanite-vr/)
- Unity discussions: [Render pipelines strategy for 2026](https://discussions.unity.com/t/render-pipelines-strategy-for-2026/1710004/print)
- Unity discussions: [Quest 3 URP performance](https://discussions.unity.com/t/terrible-build-performance-on-quest-3-with-urp-and-meta-sdk-conflicting-information-in-meta-documentation/1598096)
- StraySpark: [VR game dev for Meta Quest with UE5: 2026 guide](https://www.strayspark.studio/blog/vr-game-development-meta-quest-ue5-2026)

**Pricing & licensing**
- Unity support: [Cancellation of the runtime fee and pricing changes](https://support.unity.com/hc/en-us/articles/30322080156692-Cancellation-of-the-Runtime-Fee-and-Pricing-Changes)
- Unity blog: [Unity is canceling the runtime fee](https://unity.com/blog/unity-is-canceling-the-runtime-fee)
- AWS: [GameLift Streams pricing](https://aws.amazon.com/gamelift/streams/pricing/)
- AWS: [Gen6 stream classes announcement Dec 2025](https://aws.amazon.com/about-aws/whats-new/2025/12/aws-gameliftstream-gen6-enhanced-autoscaling/)

**Assets & photogrammetry**
- Quixel: [Megascans on Fab](https://quixel.com/en-US/news/quixel-on-fab-new-megascans-and-megaplants)
- 80lv: [Free Megascans downloads in Fab](https://80.lv/articles/epic-games-to-launch-tool-for-free-megascans-downloads-in-fab)
- RealityScan: [2.0 release](https://www.realityscan.com/news/realityscan-20-new-release-brings-powerful-new-features-to-a-rebranded-realitycapture)
- Power KH: [Reality capture costs 2025](https://www.powerkh.com/how-much-reality-capture-cost/)

**3DGS web/VR**
- World Labs: [Spark 2.0 streaming 3DGS worlds on the web](https://www.worldlabs.ai/blog/spark-2.0)
- The Future 3D: [SuperSplat review 2026](https://www.thefuture3d.com/software/supersplat/)
- The Future 3D: [State of Gaussian Splatting in 2026](https://www.thefuture3d.com/blog/state-of-gaussian-splatting-2026/)
- WebGPU.com: [WebGPU hits critical mass — all major browsers ship it](https://www.webgpu.com/news/webgpu-hits-critical-mass-all-major-browsers/)

**Market**
- F1 TV: [Premium tier launch (Sports Video Group)](https://www.sportsvideo.org/2025/03/11/f1-tv-launches-new-f1-tv-premium-subscription-tier/)
- AWS: [Track Pulse architecture blog](https://aws.amazon.com/blogs/media/real-time-storytelling-the-aws-architecture-behind-formula-1-track-pulse/)
- iRacing: [Track technology / laser scanning](https://www.iracing.com/track-technology/)
- Allkeyshop: [F1 25 VR performance guide](https://www.allkeyshop.com/blog/f1-25-vr-performance-guide-price-comparison-news-y/)
- Formula1.com: [F1 Manager 2024 launch](https://corp.formula1.com/f1-manager-2024-out-now-with-new-create-a-team-mode/)

**Papers (3DGS)**
- Hierarchical 3DGS: [arxiv 2406.12080](https://arxiv.org/abs/2406.12080)
- Scaffold-GS: [arxiv 2312.00109](https://arxiv.org/abs/2312.00109)
- Mip-Splatting: [arxiv 2311.16493](https://arxiv.org/abs/2311.16493)
- Self-Organizing Gaussians: [arxiv 2312.13299](https://arxiv.org/abs/2312.13299)
- LODGE: [arxiv 2505.23158](https://arxiv.org/abs/2505.23158)

---

## Appendix A — Why I'm recommending against full Unity-or-Unreal commitment

The framing of "Unity vs Unreal" assumed the renderer is the primary engineering concern. For a *telemetry-replay* app it's not — the primary concerns in 2026 are:

1. **Browser delivery** (where Unity WebGL has hard limits and Unreal has no real WebGL story)
2. **Photoreal scene capture** (where 3DGS now beats both engines for realism per dollar)
3. **VR delivery** (where neither engine ships Lumen/Nanite on standalone Quest 3)

A bespoke Three.js / PlayCanvas viewer with 3DGS for static and PBR meshes for dynamic objects sidesteps all three of those constraints, while being strictly cheaper than either game engine. **Unreal stays in the stack only as the cinematic-mode pixel-streaming server** for users who pay for that tier.

This is a "use the right tool" argument, not a tribal "Unity sucks / Unreal sucks" argument.

---

*Draft v1 — 2026-05-10. Treat all $ figures as starting estimates; verify against linked pricing pages before committing to spend.*
