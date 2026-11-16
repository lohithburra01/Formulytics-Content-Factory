# Surrogates, aero maps and reduced-order models for low per-weekend airflow cost

Scope: whether you can run a set of attitude/speed CFD states once, then build each race weekend's per-frame airflow by interpolating or predicting from the lap's speed and attitude trace, on one RTX 4060 Laptop (8 GB VRAM). Researched 2026-10-26. 16 tool calls. Several findings come from search-engine summaries of the source pages, not from full-text reads. Those are marked "(summary)", and the writer should treat their wording as approximate.

## 1. How do motorsport teams use aero maps, and how are the maps built and used in lap simulation?

### Takeaway
An aero map is a lookup table or response surface of downforce, drag and balance against front and rear ride height, extended with roll, yaw and steer (and sometimes exhaust flow). Teams build it once per aero package from tunnel or CFD sweeps and query it at each point of a lap simulation. This is the same "precompute states, interpolate per frame" idea the user proposes, but for integrated forces, not full flow fields.

### Cited Findings
- An aero map is described as aerodynamic forces against ride height: drag, downforce and balance measured over a grid of front and rear ride heights (summary) — [LEAP Australia blog](https://www.leapaust.com.au/blog/?p=4917)
- A practitioner forum post describes the map as lookup tables: downforce by front ride height vs rear ride height, and drag the same way (summary; forum, secondary) — [DSR forum "aero maps"](https://www.tapatalk.com/groups/dsrforum/aero-maps-t1413.html)
- A Politecnico di Milano thesis defines each car state by front and rear ride height, roll, yaw, steering and exhaust mass flow. It weights each state by how likely it is to occur over a lap and by the coefficient sensitivities, and calls the resulting weighted list the "wind tunnel map". It uses that map to compare aero packages by lap time (summary) — [PoliMi thesis 10589/234015](https://www.politesi.polimi.it/handle/10589/234015)
- A Formula Student study (FST10e) used five map parameters: front and rear ride height, roll, steering and yaw, all estimated with CFD (summary) — [M. Carreira thesis, IST Lisbon](https://fenix.tecnico.ulisboa.pt/downloadFile/845043405586591/MiguelCarreira_Thesis.pdf); [extended abstract](https://fenix.tecnico.ulisboa.pt/downloadFile/845043405586592/MiguelCarreira_ExtendedAbstract.pdf)
- The map can also be measured on track with ride-height laser sensors and suspension force transducers (summary) — [LEAP Australia blog](https://www.leapaust.com.au/blog/?p=4917)
- AeroDyn, a commercial tunnel, yaws the car about the front axle "similar to what is seen on track", over a range of +3° to −5° (summary) — [AeroDyn tunnel info](https://www.aerodynwindtunnel.com/tunnel-info)
- A self-described "verified F1 aerodynamicist" (Reddit r/F1Technical, secondary) says the tunnel shows very high SCL (downforce) sensitivity to steer angle, and that steer can be swept on its own with the other variables held fixed. The same post says straight tunnel walls give zero flow curvature, so a tunnel-built map does not capture cornering curvature well (summary) — [r/F1Technical mirror](https://teddit.bsalzberg.com/r/F1Technical/comments/1j14bwb/insights_behind_the_steer_sweep_technique)
- FIA testing limits in force since 2008: one wind tunnel, 60% maximum model scale and 50 m/s maximum tunnel speed — [CFD Online news](https://www.cfd-online.com/Forum/news.cgi/read/9505); [Autosport](https://www.autosport.com/f1/news/64312/fia-to-limit-wind-tunnel-use-from-2008)
- Later rules (2022 report) keep the 60% and 50 m/s limits and cap tunnel runs, wind-on time and occupancy hours. They limit CFD by the number of new geometries and by Mega Allocation Unit hours (MAUh). Since 2021, a sliding scale ties each team's allowance to its championship position — [Automotive Testing Technology International, June 2022, p.60](https://automotivetesting.mydigitalpublication.com/automotive-testing-technology-international-june-2022-issue/page-60)

### Inferences
- Running an F1 tunnel model at 60% scale and at most 50 m/s, then using the results at track speeds of about 80+ m/s, depends on the coefficients scaling with dynamic pressure. That suggests teams treat force coefficients as close to independent of speed and Reynolds number over the speed range they test (see section 5). No primary source states this directly.
- A map that weights states by how often they occur on a lap points to a practical sampling plan: put the precomputed CFD states where the lap's attitude trace spends its time (low ride height at high speed, high steer and roll at low speed).

### Gaps
- No primary source (SAE paper, Katz, or Milliken) was fetched on aero-map construction or the interpolation scheme teams use. The sources above are theses, a vendor blog and forums.
- Map grid density (number of points per axis) was not found.

## 2. Reduced-order models of flow fields (POD/PCA, DMD, parametric ROMs): libraries, and how accurately they interpolate separated car wakes

### Takeaway
Parametric POD with interpolation is a standard non-intrusive way to rebuild full fields at new parameter values. EZyRB and pod-rbf implement it in Python. It has been applied to the yaw dependence of a Windsor body, but quantified accuracy for interpolating separated car wakes, and for extrapolating outside the training range, was not found. The literature reports degradation away from the sampled conditions.

### Cited Findings
- The standard method has two phases. Offline, high-fidelity solutions are collected at sampled parameter values and a POD basis is extracted. Online, the modal coefficients and/or basis for a new parameter value come from interpolation models (summary) — [Non-intrusive ROM for parametrized CFD-DEM, arXiv 2302.12625](https://arxiv.org/pdf/2302.12625)
- POD bases can also be interpolated on a Grassmann manifold to build a new modal matrix at arbitrary conditions. One hypersonic-vehicle study combined this with LS-SVM to map inputs to POD coefficients (summary) — [NUAA page](https://hhy.nuaa.edu.cn/2020/0503/c11897a198902/page.htm)
- A draft paper builds a surrogate for yaw effects on a Windsor square-back body from wall-modelled LES at 10° yaw, with POD computed by SVD of the snapshot matrix. It notes that yaw intensifies rear suction and raises drag (summary; draft, details provisional) — [Sanchez Pinedo et al., "Deep learning model order reduction for the automotive industry" (draft)](https://scipedia.com/wd/images/b/bc/Draft_Sanchez_Pinedo_479052337pap_2505.pdf)
- A 2026 conference abstract uses POD of velocity-magnitude and pressure snapshots, with RBF or neural-network regression of the reduced coefficients, validated by leave-one-out (summary) — [UniPi event, Jun 2026](https://events.dm.unipi.it/event/331/contributions/855/)
- POD-type ROMs stay accurate mainly near the sampled conditions. One study with snapshots at a single Mach number was accurate only near that Mach number (summary) — [NLR report](https://dspace-erf.nlr.nl/server/api/core/bitstreams/4a20ce9a-34e9-4b52-9d82-13c0cef91955/content); see also [Gappy POD, MIT ACDL](https://acdl.mit.edu/GappyAIAA.pdf)
- EZyRB is a Python model-order-reduction library. It selects parameter points by barycentric triangulation and modes by POD, then interpolates the low-rank coefficients over parameter space. It is non-intrusive (needs only solver output files), offers PODI with RBF interpolation, installs with pip as `ezyrb`, and depends on vtk — [libraries.io EZyRB](https://libraries.io/pypi/ezyrb); [MORwiki EZyRB](https://modelreduction.org/morwiki/EZyRB); [JOSS paper](https://joss.theoj.org/papers/10.21105/joss.00661.pdf)
- EZyRB has been used with FFD morphing for aerodynamic shape optimisation — [arXiv 1803.04688](https://arxiv.org/pdf/1803.04688)
- pod-rbf is a separate pip package that builds a truncated POD basis from a snapshot matrix and interpolates new parameters with an RBF network — [pypi pod-rbf](https://pypi.org/project/pod-rbf/1.3.0)
- pyMOR is a Python MOR library (reduced-basis methods for parametric linear and non-linear problems, plus balanced truncation and IRKA). It connects to external PDE solvers through abstract interfaces. Older releases carry BSD-style terms, but the exact current licence was not confirmed — [pyMOR paper, arXiv 1506.07094](https://ar5iv.arxiv.org/html/1506.07094); [PyPI pymor](https://pypi.org/project/pymor/2021.1.0/)

### Inferences
- For a fixed car, the parameter space is small: about 5 attitude parameters plus speed. If speed is removed by coefficient scaling (section 5), the remaining space suits a POD+RBF ROM. The online cost is a small matrix-vector product per frame, cheap on a laptop CPU or GPU. Memory is set by the number of modes times the number of grid points kept (for example, a 2D top-down slice or a coarse 3D box rather than the full 100M+ cell mesh).
- POD of time-averaged fields interpolates the mean flow. It will not produce shedding. Separated-wake regions that change topology between states (a wake that attaches and detaches, or a vortex that bursts) tend to interpolate badly. A leave-one-out check on the user's own snapshots is the honest way to measure this, because no published error figure for car wakes was found.

### Gaps
- PyDMD and RBniCS: no source was retrieved this session, so their licences and features are unverified. PyDMD is commonly reported at github.com/PyDMD/PyDMD, but this was not checked. DMD suits time-resolved snapshots of one condition, not parametric attitude sweeps.
- No published error metrics were found for POD/RBF interpolation of race-car or open-wheel wakes across ride height, yaw or steer.

## 3. ML surrogates for car aerodynamics: datasets, models, 8 GB inference, ground effect and yaw, pretrained weights, F1/open-wheel data

### Takeaway
The large open datasets (DrivAerML, DrivAerNet++, WindsorML, AhmedML) are passenger-car or bluff-body sets at a single flow condition. Their variation is geometry, not attitude. DrivAerML and WindsorML have no moving ground and no yaw sweep. The one race-car, map-point dataset (Dallara LMP2, arXiv 2604.18491) does not list public data or weights. NVIDIA's pretrained DoMINO NIM officially needs 40 GB of GPU memory. So no off-the-shelf pretrained model predicts F1 airflow against attitude on an 8 GB GPU. A small custom surrogate or ROM trained on the user's own CFD states is the realistic route.

### Cited Findings
**Datasets**
- DrivAerML: 500 morphed variants of the DrivAer notchback; about 30 TB; CC BY-SA 4.0 (commercial use allowed); OpenFOAM v2212 hybrid RANS-LES (SA-σ-DDES); about 160M cells per case; Re_L = 7.19×10⁶ at U∞ = 38.889 m/s. **Stationary ground and static wheels; no yaw or inflow-speed variation** (moving ground and yaw listed as future work). Provides time-averaged volume fields (.vtu), surface data (.vtp), 2D slices, STL and force coefficients — [DrivAerML, arXiv 2408.11969](https://arxiv.org/html/2408.11969v2)
- WindsorML: 355 Windsor-body variants; more than 20 TB; CC BY-SA 4.0; GPU wall-modelled LES (Volcano ScaLES, Vreman subgrid model); fixed yaw of −2.5°; Re = 2.9×10⁶; **no moving ground**; **time-averaged only** (time series left out because it would need more than 100,000 timesteps). Cell counts conflict within the paper: "more than 280M" in the abstract vs 275M for the baseline grid in Table 1. Available on S3 with no AWS account needed — [WindsorML, arXiv 2407.19320](https://arxiv.org/html/2407.19320v4)
- AhmedML: 500 Ahmed-body variants, hybrid RANS-LES in OpenFOAM, about 20M cells, same structure and access policy as DrivAerML and WindsorML; CC BY-SA (summary) — [WindsorML, arXiv 2407.19320](https://arxiv.org/html/2407.19320v4); [AhmedML, arXiv 2407.20801](https://arxiv.org/html/2407.20801v1)
- DrivAerNet++: 8,000 designs in the paper (8,150 in the current README); 39 TB; dataset CC BY-NC 4.0 (non-commercial; commercial licence on enquiry), code MIT. Includes meshes, parametric models (26 parameters), coefficients, surface fields (Cp, wall shear), full 3D volume fields (pressure, velocity, turbulence), part segmentation and point clouds — [DrivAerNet++, arXiv 2406.09624](https://arxiv.org/html/2406.09624v2); [GitHub DrivAerNet](https://github.com/Mohamedelrefaie/DrivAerNet). One benchmark paper instead calls the licence CC-BY-SA, which conflicts with the primary sources — [arXiv 2507.10747](https://arxiv.org/pdf/2507.10747)
- CarBench, a benchmark built on DrivAerNet++, says the ground truth is OpenFOAM simpleFoam steady RANS (k-ω SST) **with moving ground and rotating wheels**. Its task is surface-pressure regression, and transformer-style neural solvers and operators gave the best accuracy-scalability trade-off (summary) — [CarBench, arXiv 2512.07847](https://arxiv.org/pdf/2512.07847)
- **Race car, map points:** "Faster by Design" (IBM Research authors, with data validated by Dallara aerodynamicists) introduces an LMP2-class parametric CAD dataset with RANS CFD at **six map points** covering straight-line and cornering states (combinations of heave, pitch, yaw, roll and steer) that capture underfloor ground effect. The authors state that standard benchmarks fix a single flow condition, which rules out map-point surrogates. Model: GIST (Gauge-Invariant Spectral Transformer, a graph neural operator that scales linearly with mesh size). The abstract page lists **no public dataset, code or weights**, and the CC BY-SA 4.0 licence shown covers the article only. Attitude ranges, moving-ground settings, accuracy numbers and inference time are not on the abstract page — [arXiv 2604.18491](https://arxiv.org/abs/2604.18491)

**Models and hardware**
- NVIDIA PhysicsNeMo DoMINO is a local, multi-scale, point-cloud neural operator. It takes STL input and predicts surface pressure and wall shear plus volume velocity and pressure. It is typically trained on DrivAerML, with training taking "a couple of days" on one H100 node. Out-of-memory errors are handled by reducing `model.volume_points_sample`, and domain parallelism (ShardTensor/FSDP) is supported — [PhysicsNeMo DoMINO docs](https://docs.nvidia.com/physicsnemo/26.03/physicsnemo/examples/cfd/external_aerodynamics/domino/README.html)
- DoMINO-Automotive-Aero NIM: pretrained on road-vehicle geometries and served through an API with STL input — [NVIDIA dev blog](https://developer.nvidia.com/blog/how-to-run-ai-powered-cae-simulations/); [PhysicsNeMo release notes](https://docs.nvidia.com/physicsnemo/26.03/release-notes/index.html). Support matrix: optimised on H100 80 GB, A100 40/80 GB, L40S 48 GB and RTX PRO 6000 96 GB. **Minimum 40 GB GPU memory** (FP32, 1 GPU, non-optimised), x86 only. Smaller GPUs "may need runtime adjustments" (smaller point cloud) — [NIM support matrix](https://docs.nvidia.com/nim/physicsnemo/domino-automotive-aero/latest/support-matrix.html)
- AB-UPT (Emmi AI): reports state-of-the-art surface and volume field accuracy on automotive CFD from 33K to 150M cells. The authors claim end-to-end inference on 9M surface and 140M volume cells on one NVIDIA GPU, training on one GPU in under a day, and predictions "within seconds". SHIFT-SUV: about 13.5 h training on one H100 and under 34 s inference for 45M-cell meshes. **These are vendor and author claims, not independent benchmarks**, and the GPU memory used is not stated in the retrieved text — [AB-UPT, arXiv 2502.09692](https://arxiv.org/html/2502.09692v4); [Emmi AI, Jun 2025](https://www.emmi.ai/news/ab-upt-scaling-neural-surrogates-100m-cfd-meshes); [Emmi AI, Oct 2025](https://emmi.ai/news/ab-upt-sets-new-benchmarks-cfd-datasets); [ICLR 2026 poster](https://iclr.cc/virtual/2026/poster/10014061)

### Inferences
- None of the open datasets vary attitude (ride height, roll, yaw, steer) for a fixed geometry. So no public pretrained model learns the mapping this project needs. Every public model maps geometry to fields at one condition. Encoding attitude as geometry (moving the STL to each pitch, roll and ride height, with steered front wheels) and feeding it to a geometry-conditioned model is conceptually possible, but these models were trained on road cars with no wings, no diffuser ground effect and (for DrivAerML) a stationary floor. Their predictions for an F1 car would be extrapolation, which no source validates.
- An 8 GB laptop GPU is well below DoMINO's stated 40 GB minimum. Running inference on a heavily subsampled point cloud may work, but this is unverified. A small model trained on the user's own about 20 to 100 CFD states, or a POD+RBF ROM, fits easily in 8 GB.

### Gaps
- Transolver, FIGConvNet, X-MeshGraphNet, FNO and GINO: no source was retrieved this session for their memory use, weights or licences.
- Whether DoMINO NIM weights can be downloaded for local use, and their licence, was not stated on the pages fetched.
- Luminary Cloud open models (for example any "Shift" datasets): not researched beyond the Emmi AI mention of SHIFT-SUV.
- No public **open-wheel or F1** CFD dataset was found. The LMP2 dataset is the closest, and its availability is unconfirmed.

## 4. Unsteady wakes: cheap ways to get time-resolved-looking trails, and whether they are honest

### Takeaway
All the large open datasets ship only time-averaged fields because time series are too costly (WindsorML's explicit reason). Established methods add synthetic turbulence on top of a RANS-type mean (synthetic turbulence generators, RANS-conditioned generative models), but these exist to feed simulations or to model statistics. They are not a validated way to show a car's real unsteady wake. Pathlines through a steady mean field show the mean flow, not instantaneous structures, and should be labelled that way.

### Cited Findings
- WindsorML left out time series because it would need more than 100,000 timesteps per case, so it ships time-averaged fields only — [WindsorML, arXiv 2407.19320](https://arxiv.org/html/2407.19320v4). DrivAerML likewise provides time-averaged volume fields — [DrivAerML, arXiv 2408.11969](https://arxiv.org/html/2408.11969v2)
- A turbomachinery method runs RANS of the full machine, then uses a dynamic volumetric synthetic turbulence generator (source terms) to inject unsteady perturbations into a scale-resolving IDDES of one region (summary) — [Supercomputing Frontiers & Innovations](https://superfri.org/index.php/superfri/article/view/610)
- A Bayesian conditional diffusion model generates LES-like spatiotemporal turbulent fields conditioned on a URANS flow, demonstrated on a backward-facing step (summary) — [arXiv 2311.07896](https://arxiv.org/pdf/2311.07896)

### Inferences
- An honest budget option is to compute 1 to 3 short unsteady (DES/LES) runs at representative states offline, extract the fluctuation statistics or a short loop of fluctuating fields, and overlay those on the interpolated mean field. Label it as "mean field from CFD + representative fluctuations". Tracing particles through the interpolated mean field (pathlines/streaklines advected frame by frame while the field changes with attitude) shows how the mean flow changes and is physically defensible. It just is not instantaneous turbulence.
- Random noise not drawn from real fluctuation statistics would be decoration and should not be presented as simulated turbulence. This is a judgement, not a sourced finding.

### Gaps
- No source was found that specifically validates synthetic-eddy overlays or pathline rendering for vehicle-wake visualisation, or shows them on a car.

## 5. Scaling velocity with speed (Reynolds independence) to reuse fields across speeds

### Takeaway
Treating force coefficients (and, by extension, normalised velocity fields u/U∞) as speed-independent once Reynolds number is high enough is common practice, and implicit in F1's 60%-scale, 50 m/s tunnel testing. But independence is shape-dependent and not guaranteed. No primary source was found that sets a general threshold for race cars.

### Cited Findings
- Reduced-scale streamlined bodies often show strong Reynolds sensitivity, which makes transfer to full scale hard (KIT velomobile project) (summary) — [KIT](https://www.iwu.kit.edu/efm/2149.php)
- Tests on 1/24-scale car models found Reynolds independence did not hold for every model, with drag errors up to 14% for one (summary) — [Gazi University study](https://abs.gazi.edu.tr/yayin/a2192a86-274c-4614-89a5-a09fa251f609/determination-of-drag-coefficients-of-various-automobile-models-in-a-low-speed-wind-tunnel)
- A prototype-vehicle study reported Cd becoming independent of Re above 2.8×10⁵, at 0.25 (summary; small-scale) — [Erciyes study](https://avesis.erciyes.edu.tr/yayin/0422a7fa-7007-426d-b9a9-7fd68452d498/experimental-and-numerical-aerodynamic-investigation-of-a-prototype-vehicle)
- Flow past a high-sided trailer was found to depend on Re, challenging the independence assumption used in overturning studies (summary) — [US DOT ROSAP](https://rosap.ntl.bts.gov/view/dot/79179)
- F1 tunnel testing is capped at 60% scale and 50 m/s — [CFD Online](https://www.cfd-online.com/Forum/news.cgi/read/9505); [ATTI 2022](https://automotivetesting.mydigitalpublication.com/automotive-testing-technology-international-june-2022-issue/page-60). A forum estimate puts this at about 36 m/s full-scale-equivalent Re for a full-size car (hobbyist, unverified) — [F1Technical forum](https://www.f1technical.net/forum/viewtopic.php?p=774660)

### Inferences
- Over an F1 lap (about 20 to 95 m/s at full scale, so Re roughly 10⁷ to 5×10⁷ on car length), using one CFD state per attitude and scaling velocity by U∞ (forces by U∞²) is the standard simplifying assumption. The errors to expect are small coefficient shifts, not changes in flow topology. Running one state at two speeds (for example 40 and 80 m/s) and comparing would measure this directly for the user's own car. That is a suggestion, not a sourced result.
- Speed-dependent effects that do not scale this way (ride height changing with downforce, tyre deflection) enter through the attitude trace, which the user already has per frame.

### Gaps
- No SAE, AIAA or textbook source (Katz, Milliken) was retrieved that states the Reynolds-independence range for open-wheel or ground-effect cars. Ground-effect underfloors may be more Re-sensitive (transition, separation in the diffuser), but this is unverified.
