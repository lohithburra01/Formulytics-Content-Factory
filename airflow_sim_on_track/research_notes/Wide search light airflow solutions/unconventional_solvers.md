# Unconventional / lightweight open-source CFD for a laptop-scale 3D car wake (RTX 4060 Laptop 8 GB, i9-13950HX, 32 GB, Win 11)

Scope note: ~30 tool calls, breadth first. Licensing ignored per brief. FluidX3D, OpenFOAM, ParaView, and the standard LBM solvers were already rejected and are only mentioned for comparison. Items marked **[UNVERIFIED]** come from background knowledge that I did not re-confirm in this session. They sit in Gaps or carry that mark, and should not be presented as fact without a check.

## Q1. Which codes or methods could give a credible 3D car wake or ground-effect downforce in minutes on this laptop? (catalogue)

### Takeaway
The strongest find is **WaterLily.jl**, a Julia GPU immersed-boundary Navier-Stokes solver with implicit LES. Its authors profiled it on an RTX 4060 laptop GPU, the same GPU as the user's. It is validated on a sphere at Re 3700 (C_D within 4% of DNS) and takes any geometry given as a signed-distance function. The second-best fit is **XLB** (Python LBM with JAX and NVIDIA Warp backends, a KBC collision model, Smagorinsky LES, a trimesh voxelizer and a DrivAer showcase). It is still an LBM code, but a Python-scriptable one. Most vortex-particle and panel codes cannot shed bluff-body separation wakes, and FLOWUnsteady says so explicitly. Neural surrogates trained on DrivAer data (AB-UPT, DrivAerNet/RegDGCNN, PhysicsNeMo AeroGraphNet) return fields in seconds, but they are learned models, not simulations.

### Cited Findings

**A. GPU immersed-boundary / Cartesian Navier-Stokes (best fit)**

1. **WaterLily.jl (Julia; CUDA, AMD, Metal and CPU)**
   - Method: incompressible Navier-Stokes on a uniform Cartesian grid, with the pressure Poisson equation solved by geometric multigrid. Bodies use the Boundary Data Immersion Method — [GitHub README](https://github.com/WaterLily-jl/WaterLily.jl)
   - Backends: GPU via `mem=CuArray`, also AMDGPU/ROCArray and Metal/MtlArray (Float32 only on Apple) — [README](https://github.com/WaterLily-jl/WaterLily.jl)
   - Turbulence: "model-free, making it an implicit Large Eddy Simulation (iLES) solver" — [arXiv 2407.16032v3](https://arxiv.org/html/2407.16032v3)
   - Speed: cost "as low as 1.44 ns per DOF per time step" — [README](https://github.com/WaterLily-jl/WaterLily.jl). The paper reports 1.57 ns/DOF/dt for TGV on an H100, and the H100 runs about 2x faster than an MI250X. GPU is about two orders of magnitude faster than serial CPU, and CPU multithreading plateaus near 5x — [arXiv 2407.16032v3](https://arxiv.org/html/2407.16032v3)
   - **The profiling run used an RTX 4060 laptop GPU**, the user's GPU — [arXiv 2407.16032v3](https://arxiv.org/html/2407.16032v3)
   - README example: a 3D GPU sphere run took about 40 s, roughly 40% slower than a much smaller 2D case on 8 CPU threads — [README](https://github.com/WaterLily-jl/WaterLily.jl)
   - Older preprint: a 3D TGV ran 70x faster on a GTX 1650 Ti laptop-class GPU than serial CPU. The pressure solver dominates when a solid body is present — [arXiv 2304.08159](https://arxiv.org/pdf/2304.08159)
   - Validation: sphere at Re 3700 gives C_D = 0.38, within 4% of DNS and 7% of LES, with only about 3 cells across the boundary layer on the finest grid. A small domain gives 0.45, so domain size matters. An oscillating cylinder gives a power coefficient within 3% of experiment — [arXiv 2407.16032v3](https://arxiv.org/html/2407.16032v3)
   - Memory: 226M DOF uses 29 GB in FP32 — [arXiv 2407.16032v3](https://arxiv.org/html/2407.16032v3)
   - Limits: the uniform grid "requires vast resources to fully resolve the boundary layer". The solver is memory-bandwidth bound — [arXiv 2407.16032v3](https://arxiv.org/html/2407.16032v3)
   - Geometry: a signed-distance function wrapped in `AutoBody`, or ParametricBodies.jl. The README mentions no STL reader — [README](https://github.com/WaterLily-jl/WaterLily.jl); [JuliaLang blog](https://julialang.org/blog/2021/08/sharks/)
   - Moving bodies are native ("dynamic bodies") — [arXiv 2407.16032](https://arxiv.org/pdf/2407.16032)
   - Differentiable — [arXiv 2304.08159](https://arxiv.org/pdf/2304.08159)
   - MPI / multigrid follow-up: near-ideal strong scaling, and weak scaling above 96% across nodes up to about 1B cells. The original venue is unconfirmed — [mirror](https://docshare.wps.com/document/scaling-waterlilyjl-with-mpi-and-an-improved-geometric-multigrid-solver/83283/_payload.json)
   - Benchmark data is public (v1.4.0) — [4TU dataset](https://data.4tu.nl/datasets/f5bf6c46-8fbd-42b8-afb6-5eb356eae2e2)

2. **TUCANGPU (Python + Numba CUDA + CuPy)**
   - Method: direct-forcing IBM (Uhlmann), fractional step, RK3, staggered grid. The text does not mention STL; bodies are defined analytically — [arXiv 2406.19920v2](https://arxiv.org/html/2406.19920v2)
   - Speed: 34–54x faster than the 96–128-core CPU version. Tested on a TITAN V (12 GB) and an A100 — [arXiv 2406.19920v2](https://arxiv.org/html/2406.19920v2)
   - Validation: only code-to-code against the CPU version (errors around 1e-8). No experimental check. Code availability is not stated in the part I read.

3. **IB-Flows (CUDA Fortran, multi-GPU, 2026 preprint)**
   - Method: fractional-step finite differences with moving-least-squares and sharp-interface IBM, plus SGS eddy-viscosity LES — [arXiv 2609.19130](https://arxiv.org/abs/2609.19130)
   - The abstract mentions no STL support and no repository link. It targets HPC.

4. **cuIBM / PetIBM (Barba group)**
   - cuIBM is **2D only** on a single GPU, and its speed-up is limited because the method is bandwidth-bound — [arXiv 1109.3524](https://arxiv.org/pdf/1109.3524); [JOSS](https://www.theoj.org/joss-papers/joss.00301/10.21105.joss.00301.pdf)
   - PetIBM is 3D on distributed CPUs (PETSc), with optional AmgX GPU linear solves — [JOSS 00558](https://joss.theoj.org/papers/10.21105/joss.00558); [GTC2016 notebook](https://nbviewer.org/github/barbagroup/conferences/blob/master/GTC2016/GTC2016_S6355.ipynb)
   - Not a fit for minutes on a laptop.

5. **ViCar3D (JHU, sharp-interface IBM; OpenACC and CUDA Fortran)**
   - Roughly 20x node-to-node speed-up over CPU. Runs 3D flow past a finite wing, with up to 200M points on one 4-GPU node — [arXiv 2505.17287v2](https://arxiv.org/abs/2505.17287v2)
   - Open-source status is unverified.

6. **AMReX-based codes (incflo; FLARE LBM)**
   - AMReX provides cut-cell embedded boundaries and CUDA/HIP/SYCL GPU support — [FASTMath catalogue](https://scidac-fastmath.lbl.gov/software-catalog/software_amrex)
   - incflo is an AMReX incompressible solver — [arXiv 1905.07392](https://arxiv.org/pdf/1905.07392)
   - FLARE, a multi-GPU AMReX LBM thesis code, supports STL-driven embedded boundaries and ran DrivAer, according to the search snippet — [UNIGE archive](https://archive-ouverte.unige.ch/unige:194359)
   - Single-GPU runtime is unverified. These are Linux-first HPC codes.

7. **JAX-Fluids (TUM; compressible, JAX)**
   - Features: level-set immersed solids. Scaled to 512 A100s — [GitHub](https://github.com/tumaer/jaxfluids)
   - Speed: under 0.1 s per step for 4.2M cells on 8 GPUs. Single precision is about 2x faster than double — [arXiv 2406.19494](https://arxiv.org/pdf/2406.19494)
   - Compressible formulation at car Mach (~0.1–0.3) means small time steps. I found no immersed-solid 3D timings.
   - A separate 2025 JAX sharp-interface incompressible IB solver uses **triangular surface meshes** (so STL-like input). Its numbers were not in the abstract — [APS DFD 2025](https://meetings-archive.aps.org/dfd/2025/c12/7)

8. **PhiFlow (TUM; NumPy, PyTorch, JAX, TensorFlow)**
   - 3D on GPU via PyTorch or TF — [PMLR ICML 2024](https://proceedings.mlr.press/v235/holl24a.html); [mirror](https://gitee.com/xjtu-forge/PhiFlow)
   - I found no 3D obstacle wind-tunnel example. It is aimed at ML research, not validated aero.

9. **Basilisk (C, adaptive quad/octree)**
   - Refinement is driven by a wavelet error estimate every time step, so cells are only placed where needed — [Basilisk sandbox](https://basilisk.dalembert.upmc.fr/sandbox/Antoonvh/README)
   - The octree "allows for much faster solution procedures than a general-purpose LES code" — [arXiv 2211.16628](https://arxiv.org/pdf/2211.16628)
   - The sandbox has 3D LES cases (vortex cannon, isotropic turbulence) — [sandbox](https://basilisk.dalembert.upmc.fr/sandbox/Antoonvh/README)
   - I found no car or bluff-body laptop case. It is CPU-only to my knowledge (GPU status, Windows support and STL import via `distance.h` are all **[UNVERIFIED]**).

**B. Python / JIT lattice Boltzmann (not FluidX3D)**

10. **XLB (Autodesk; JAX, NVIDIA Warp and Neon backends)**
    - Backends: Warp for single GPU, Neon for multi-GPU and multi-resolution — [GitHub](https://github.com/Autodesk/XLB)
    - Physics: BGK and KBC collision models ("unconditionally stable for flows with high Reynolds number"), Smagorinsky LES — [GitHub](https://github.com/Autodesk/XLB)
    - Geometry and output: "3D mesh voxelizer using trimesh" (so STL/OBJ via trimesh), VTK via PyVista, HDF5/XDMF, in-situ rendering — [GitHub](https://github.com/Autodesk/XLB)
    - Showcase: DrivAer in a wind tunnel, KBC, about 317M cells. That is multi-GPU scale — [examples](https://xlb.readthedocs.io/en/latest/_sources/examples.md); [Autodesk blog](https://www.research.autodesk.com/blog/accelerating-scientific-computing-with-jax-lbm)
    - Windows is not mentioned (install notes cover Linux and Mac). No single-GPU MLUPS figure is in the README — [GitHub](https://github.com/Autodesk/XLB)
    - The XLB paper reports "giga-scale lattice updates per second" — [arXiv 2311.16080](https://arxiv.org/abs/2311.16080v3)
    - I found no published DrivAer C_D validation for XLB.

11. **Lettuce (PyTorch LBM, Univ. Siegen)**
    - 2D/3D, CUDA via PyTorch, custom native CUDA extensions, neural collision models — [arXiv 2106.12929](https://arxiv.org/pdf/2106.12929); [docs](https://lettucecfd.readthedocs.io/en/latest/readme.html)
    - Only TGV and turbulence examples. No car validation found.

12. **lbmpy / pystencils (FAU)**
    - Generates C or CUDA kernels for MRT, entropic and cumulant collision operators — [PyPI](https://pypi.org/project/lbmpy/1.3.6)
    - The stack reproduced the sphere drag crisis above Re 2e5 on GPUs with a non-uniform mesh (year unconfirmed) — [FAU thesis](https://open.fau.de/handle/openfau/33506)
    - A **Formula Student car** (EOS Racing) was simulated with lbmpy, but on the HSUper supercomputer — [HSU HPC](https://www.hsu-hh.de/hpc/?p=299)

13. **Taichi-LBM3D** — D3Q19 MRT on CPU/GPU, aimed at porous media. No STL car support found — [Cranfield](https://dspace.lib.cranfield.ac.uk/handle/1826/18328)

14. **VirtualFluids (TU Braunschweig)**
    - Open-source cumulant LBM with grid refinement, on GPU (CUDA) and CPU — [Mendeley](https://data.mendeley.com/datasets/tfzdnz7vwx); [README](https://git.rz.tu-bs.de/irmb/VirtualFluids/-/raw/df73235b915c6d1c1a80de2fefed1d6d3e0774cc/README.md)
    - The same group's cumulant GPU LBM DrivAer study showed "good agreement to experimental data" and ran "substantially faster than the FVM". Whether that study used VirtualFluids is unconfirmed — [Pasquali et al.](https://researchgate.net/profile/Andrea_Pasquali/publication/285587618_Simulation_of_external_aerodynamics_of_the_DrivAer_model_with_the_LBM_on_GPGPUs/links/56605c2808aebae678aa0ab5/Simulation-of-external-aerodynamics-of-the-DrivAer-model-with-the-LBM-on-GPGPUs.pdf)

15. **OpenLB**
    - Open C++ library with a CUDA GPU path — [OpenLB overview](https://www.openlb.net/overview/)
    - Speed: 24.8 GLUPs on one 4xA100 node, and a Smagorinsky LES nozzle at about 36 GLUPs on two nodes — [OpenLB performance](https://www.openlb.net/performance/); [HoreKa](https://www.openlb.net/?p=4058)
    - It is an HPC library, and the user may count it as a "standard LBM".

16. **Sailfish** (Python/CUDA multi-GPU LBM, 2013, likely unmaintained) — [arXiv 1311.2404](https://arxiv.org/pdf/1311.2404)

**C. Vortex particle / vortex-in-cell / panel hybrids**

17. **FLOWUnsteady (rVPM, Julia)**
    - rVPM is a meshless LES in vorticity form — [flow.byu.edu](https://flow.byu.edu/FLOWUnsteady)
    - Its own README states that viscous drag and separation are only captured through airfoil lookup tables, without attempting to shed separation wakes. Bluff bodies via a vortex sheet method are "under development" — [ecosyste.ms mirror](https://awesome.ecosyste.ms/projects/52127)
    - **Not a fit for a car wake.** No new bluff-body version found.

18. **DUST (PoliMi / A3 Airbus; boundary elements + vortex particles)**
    - Uses the Helmholtz decomposition. Validated on rotorcraft and tiltrotors — [PoliMi](https://re.public.polimi.it/bitstream/11311/1111911/1/MONTD02-19.pdf); [NLR](https://dspace-erf.nlr.nl/items/3dbaeb10-3530-4a1f-a3d6-217250751127)
    - I found no bluff-body separation model. The same limitation as FLOWUnsteady is likely, but that is an inference.

19. **Omega3D (Applied Scientific Research, Mark Stock)**
    - Vortex particle + BEM solver with a GUI, an O(N log N) velocity solver, a flow-over-sphere preset, and triangle-mesh reading via libigl — [GitHub](https://github.com/Applied-Scientific-Research/Omega3D)
    - Called "GPU-accelerated", but compute-shader evaluation is still a work item and BEM for moving bodies is open. No performance or validation data, and Linux/macOS build steps only.
    - The most unconventional candidate: a viscous vortex method with real bodies. Treat it as experimental.

20. **Remeshed vortex particle + Brinkman penalization on GPU (Rossinelli, Koumoutsakos, Cottet)**
    - 2D bluff bodies, up to 100x faster than CPU, with reduced accuracy at high Re from FP32 — [hgpu](https://hgpu.org/?p=1257); [Cottet ref50](https://membres-ljk.imag.fr/Georges-Henri.Cottet/ref50.pdf)
    - The 3D DNS past obstacles with a vortex penalization method is a CPU paper — [HAL 01855265](https://hal.archives-ouvertes.fr/hal-01855265)
    - Research codes only; I found no released 3D GPU package.

21. **3D GPU vortex-in-cell (Kosior & Kudela)** — 46x speed-up on GPU. Code release not found — [hgpu 8316](https://hgpu.org/?p=8316); [Silesian Univ.](https://delibra.bg.polsl.pl//Content/77279/BCPS-86583_2013_Fluid-motion-modelli_0000.pdf)

22. **OpenFPM** — open particle / particle-mesh framework with a vortex-in-cell example (periodic boundaries). GPU and Python support were not shown — [arXiv 1804.07598](https://arxiv.org/pdf/1804.07598)

23. **Separated-wake panel methods (historical or 2D)**
    - SAE 860218: an open-wheel race-car downforce panel model with separated body and wheel wakes, separation lines fixed from experiment, compared against F1 data — [SAE](https://saemobilus.sae.org/content/860218)
    - Carflow: panel method + 3D integral boundary layer driving separation, with free shear-layer wake panels — [SAE 960679](https://saemobilus.sae.org/papers/simulating-external-vehicle-aerodynamics-carflow-960679)
    - 2D source/vortex panel method with separation and a wake model for bluff bodies and trains in ground effect — [MDPI Appl. Sci. 12:9652](https://www.mdpi.com/2076-3417/12/19/9652)
    - Vortexje: open-source 3D panel code without a separated-wake model — [arXiv 1210.6956](https://arxiv.org/pdf/1210.6956)
    - These are not packaged open-source tools for cars.

**D. Other particle methods**

24. **DualSPHysics (GPU SPH, CUDA)**
    - Single NVIDIA GPU — [arXiv 2104.00537](https://arxiv.org/pdf/2104.00537); [CAKE](https://www.cake.ac.uk/landscape-tools/sph_solver/)
    - Weakly-compressible free-surface SPH. I found no external-aero use. A poor fit for aerodynamics (inference).

**E. Learned surrogates (seconds, not physics)**

25. **AB-UPT (Emmi AI / JKU)**
    - Predicts surface and volume fields "within seconds". Trained on one GPU in under a day — [arXiv 2502.09692](https://arxiv.org/pdf/2502.09692); [ICLR 2026](https://iclr.cc/virtual/2026/poster/10014061)
    - Vendor claims: inference under 34 s on a 45M-cell vehicle (H100), and sub-second force prediction from CAD — [Emmi news](https://www.emmi.ai/news/ab-upt-sets-new-benchmarks-cfd-datasets)

26. **DrivAerNet / RegDGCNN (MIT DeCoDE)**
    - 4000 car CFD cases with full 3D fields. Drag estimates "in seconds". Code is public — [arXiv 2403.08055](https://arxiv.org/html/2403.08055v2); [PDF](https://decode.mit.edu/assets/papers/DrivAerNet.pdf)

27. **NVIDIA PhysicsNeMo AeroGraphNet** — trained on DrivAerNet; predicts C_D, surface pressure and wall shear — [NVIDIA docs](https://docs.nvidia.com/physicsnemo/26.05/physicsnemo/examples/cfd/external_aerodynamics/aero_graph_net/README.html)

    Caveat for all three: they are trained on road cars (DrivAer family), not open-wheel F1 cars with a moving ground and varying attitude. Extrapolating to F1 is unvalidated (inference).

**F. GPU RANS**

28. **SU2 GPU** — a 2024 SU2 Conference prototype was *slower* than CPU because of host-device copies — [slides](https://docs.google.com/presentation/d/1EO5R7XcarBhiqOkh6fK40Qw96EyIvssH/htmlpresent)

29. **AmgX** — speeds up linear solves 2–5x per GPU, and up to 9x on an OpenFOAM pressure solve. This is not an end-to-end figure — [NVIDIA](https://research.nvidia.com/publication/2015-10_amgx-library-gpu-accelerated-algebraic-multigrid-and-preconditioned-iterative-methods); [NAFEMS](https://www.nafems.org/publications/resource_center/nwc21-262-b/)

30. **Full-GPU implicit RANS (TU Delft / VKI)** — 3.5x vs a 4-core CPU on turbomachinery — [TU Delft](https://research.tudelft.nl/en/publications/acceleration-of-turbomachinery-steady-simulations-on-gpu)

    RANS on GPU brings no clear laptop win.

**G. Accuracy references (Ahmed body)**
- LBM (PowerFLOW-era) Ahmed drag matched experiment across slant angles of 5–35 deg — [SAE 2008-01-0740](https://saemobilus.sae.org/papers/lattice-boltzmann-simulations-unsteady-flow-behind-ahmed-body-2008-01-0740)
- A GPU LBM Ahmed study (P100, bounce-back vs IBM) was validated against experiment and LES — [IIT Jodhpur](https://scholar.iitj.ac.in/entities/publication/43b59c4b-3e7e-4481-a4d0-6a904a678500)
- An FE-LES Ahmed 12.5 deg case gave C_D 0.2346 vs the experimental 0.2300 — [CIMEC](https://amcaonline.org.ar/foswiki/pub/Main/Cimec/AerodinamicaExteriorDeVehiculos/ahmed_gid.pdf)
- Validation set-up for the Pacefish LBM Ahmed 25 deg case — [SimScale](https://www.simscale.com/docs/validation-cases/aerodynamics-ahmed-body-lbm/)

**H. Laptop hardware notes**
- CFD is memory-bandwidth bound — [LEAP 2025](https://www.leapaust.com.au/blog/dem/how-to-approach-hardware-selection-in-2025/)
- A modern laptop with dual-channel DDR5 can match desktop run times — [CFD-Online](https://cfd-online.com/Forums/main/231320-using-laptop-cfd-simulations.html)

### Inferences
- **WaterLily on the RTX 4060 Laptop, rough estimate (not measured).** The 4060 Laptop has about 256–272 GB/s of memory bandwidth versus about 3.35 TB/s on an H100, from vendor specs I did not re-check this session. Since WaterLily is bandwidth-bound, expect roughly 10–15x the H100 cost, about 15–25 ns/DOF/step. A 20M-cell car box would then take about 0.3–0.5 s per step, so 2–3k steps (a few flow-throughs) is about 15–25 min per attitude. A ~6M-cell coarse grid would take a few minutes. Memory: 29 GB / 226M DOF is about 130 B/DOF, so 8 GB caps the run at about 55–60M cells.
- At those grids, a 5.6 m F1 car gets about 1–2 cm cells. The wake topology and ground-effect *trends* (rear wing and diffuser wakes, ride-height and pitch sensitivity) are plausible. Absolute downforce is not credible, because the boundary layer is not resolved; the sphere case already had only about 3 cells across it. The Re 3700 validation is far below car Re (about 1e7).
- **Moving ground + headwind + attitude change** maps naturally onto WaterLily. Set the inflow U equal to car speed and the floor velocity BC equal to U. Pitch, roll and yaw can go into the body SDF map, since `AutoBody` takes a coordinate map and supports moving bodies. STL needs converting to an SDF first (for example a mesh-to-SDF voxel grid, then interpolation). Whether the floor wall BC can be set as moving is an assumption to check.
- **XLB** is the Python route if staying in Python matters. Warp backend + KBC + trimesh voxelizer + PyVista output covers STL in and VTK out. LBM D3Q19 FP32 is about 80–160 B/cell, so 8 GB holds about 50–100M cells. Windows support via Warp is plausible but undocumented.
- Vortex-particle codes (FLOWUnsteady, DUST, VPM) are wrong for a car wake unless separation lines are imposed by hand. Omega3D is the only VPM+BEM code found that treats viscous bluff bodies, and it is immature.
- Surrogates are fast but would need retraining on F1-like geometries. They could be a later layer trained on WaterLily or XLB outputs.

### Gaps
- No measured single-GPU XLB, WaterLily or Basilisk car or Ahmed runtime found. WaterLily absolute GPU timings for the sphere are only in the paper's figures.
- No STL importer confirmed for WaterLily. Searches for a "MeshBodies" package returned nothing.
- Not covered or verified this session (background knowledge only): Trixi.jl (DG, compressible; IB support unclear), Oceananigans.jl (has an immersed-boundary grid but is ocean-oriented; search found nothing), PyFR (no Ahmed/DrivAer case found; GPU high-order LES, needs a curved unstructured mesh), HiFiLES, NekRS, Lethe, MFC, Exasim, NVIDIA Warp CFD samples, CubismUP-3D (search found nothing), Dedalus (spectral, no bodies), JAX-CFD (periodic, no bodies).
- Windows support is unverified for XLB, Omega3D, Basilisk and lbmpy. WaterLily runs wherever Julia + CUDA.jl run (Windows is likely; **[UNVERIFIED]**).
- No Reddit r/FSAE or r/CFD laptop benchmarks surfaced (search returned CFD-Online only).
- Free compute footnote (unresearched, **[UNVERIFIED]**): Kaggle and Colab give free T4/P100-class GPUs (16 GB) with session limits. That would roughly double WaterLily or XLB's memory ceiling, but runs inside Linux notebooks.

## Q2. What do the leading candidates offer on the requested criteria?

### Takeaway
Only WaterLily and XLB meet most of the requested criteria. WaterLily is GPU-native, has an LES-class wake, moving bodies, published validation and was profiled on this exact GPU. XLB adds Python, STL in and VTK out. Everything else fails on separation physics (VPM and panel codes), GPU or laptop practicality (PetIBM, OpenLB, ViCar3D, IB-Flows, AMReX), or validation (Omega3D, Lettuce, PhiFlow, TUCANGPU).

### Cited Findings
| Code | Method | Laptop runtime evidence | Memory | Validation | Windows | Python | STL | Output |
|---|---|---|---|---|---|---|---|---|
| WaterLily.jl | Cartesian BDIM iLES, GPU | profiled on RTX 4060 laptop; 1.44–1.57 ns/DOF/dt on H100 ([paper](https://arxiv.org/html/2407.16032v3)) | 29 GB / 226M DOF FP32 ([paper](https://arxiv.org/html/2407.16032v3)) | sphere Re 3700 C_D within 4% of DNS ([paper](https://arxiv.org/html/2407.16032v3)) | unverified | Julia | SDF only ([README](https://github.com/WaterLily-jl/WaterLily.jl)) | Julia arrays (VTK via WriteVTK, unverified) |
| XLB | LBM BGK/KBC + Smagorinsky; JAX/Warp | no single-GPU number ([GitHub](https://github.com/Autodesk/XLB)) | n/a | DrivAer showcase, no C_D found | not mentioned | yes | trimesh voxelizer | VTK, HDF5, images |
| Lettuce | PyTorch LBM | MLUPS script only ([docs](https://lettucecfd.readthedocs.io/en/latest/readme.html)) | n/a | TGV | likely via PyTorch (unverified) | yes | no | arrays |
| lbmpy | codegen LBM | FS car on supercomputer ([HSU](https://www.hsu-hh.de/hpc/?p=299)) | n/a | sphere drag crisis ([FAU](https://open.fau.de/handle/openfau/33506)) | unverified | yes | unverified | arrays/VTK |
| TUCANGPU | IBM FD, Numba | 34–54x vs 128-core CPU ([arXiv](https://arxiv.org/html/2406.19920v2)) | 12 GB GPU used | code-to-code only | unverified | yes | no | n/a |
| JAX-Fluids | compressible FV, level-set solids | <0.1 s/step at 4.2M cells on 8 GPUs ([arXiv](https://arxiv.org/pdf/2406.19494)) | n/a | n/a for bodies | JAX-on-Windows limited (unverified) | yes | level-set | HDF5 (unverified) |
| Omega3D | VPM + BEM | none ([GitHub](https://github.com/Applied-Scientific-Research/Omega3D)) | n/a | none | MSVC "should compile" | no | triangle mesh via libigl | GUI |
| FLOWUnsteady / DUST | rVPM / BEM+VPM | n/a | n/a | rotorcraft | n/a | Julia / Fortran | panels | VTK |
| AB-UPT / DrivAerNet | neural surrogate | seconds ([arXiv](https://arxiv.org/pdf/2502.09692); [arXiv](https://arxiv.org/html/2403.08055v2)) | GPU | vs DrivAer CFD | PyTorch | yes | mesh / point cloud | fields |

### Inferences
- Suggested pilot: WaterLily with a decimated car STL converted to an SDF, about 384x160x96 cells (about 6M), moving floor, Float32. Time it on the 4060 and compare against the user's earlier FP1 / CL_CORNER-scale numbers. Then run an Ahmed body at 25 deg as a sanity check against Ahmed (1984), using the references above.

### Gaps
- Per-cell memory for XLB Warp and real laptop throughput: not found.
- Whether any of these codes have documented Windows-native GPU installs: not confirmed this session.
