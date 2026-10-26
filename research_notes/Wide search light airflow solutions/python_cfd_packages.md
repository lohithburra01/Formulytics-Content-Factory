# Python CFD packages for light (laptop) airflow around a 2D/3D obstacle

Scope: Python packages (pip/conda, or Python-scripted GPU code) that solve real fluid equations (NS, Euler, LBM, vortex, SPH, spectral) around obstacles, and that could run on an RTX 4060 Laptop (8 GB VRAM), i9-13950HX, 32 GB RAM, Windows 11, in seconds to minutes. Licensing, commercial tools, game engines and VFX are out of scope.

Method and verification status (research date 2026-10-26):
- Versions and release dates come from the PyPI JSON API (`https://pypi.org/pypi/<name>/json`), queried live this session.
- GitHub stars and last-push dates come from the GitHub REST API (`https://api.github.com/repos/<owner>/<repo>`), queried live this session.
- Feature claims tagged **[verified]** were read from the cited page this session.
- Claims tagged **[prior knowledge, unverified]** come from background knowledge and should be checked before anyone relies on them.
- The web-search budget ran out after about 30 calls. Some items (Basilisk Python, lettuce internals, Dedalus obstacle handling) could not be re-checked, and they are listed under Gaps.

## Q1. Catalogue: which Python packages can simulate real flow around an obstacle, and on what backend?

### Takeaway
Only a few packages combine real 3D flow, arbitrary solid geometry (STL, voxel mask or immersed boundary), a GPU backend that runs natively on Windows, and an LES or stabilised turbulence treatment. These are XLB (Warp backend), lettuce (PyTorch LBM), PhiFlow (PyTorch/JAX/TF grid NS), a Taichi LBM (taichi_LBM3D, or a hand-written Taichi or Warp D3Q19 kernel), and the tiny new Homebrew-CFD (Taichi LBM, F1-targeted, moving ground, still unproven). JAX-based solvers (XLB-JAX, JAX-Fluids, vivsim, JAX-CFD) are strong, but JAX GPU on Windows needs WSL2. Most of the remaining packages are 2D, periodic-only, CPU-bound, or heavy unstructured-mesh frameworks.

### Cited Findings

#### Tier A: GPU LBM, obstacle-capable, 3D (best fit for "light" external aero)

1. **XLB (Autodesk), Accelerated Lattice Boltzmann.** https://github.com/Autodesk/XLB
   - pip: `xlb`, latest 0.3.1 (2026-01-12, Python >=3.11) — [PyPI JSON](https://pypi.org/pypi/xlb/json)
   - Activity: 515 stars, last push 2026-09-16 — [GitHub API](https://api.github.com/repos/Autodesk/XLB)
   - Backends **[verified]**: JAX, NVIDIA Warp and Neon. Warp is the single-GPU backend. Neon is for multi-GPU and single-GPU multi-resolution, and is Linux-only — [GitHub](https://github.com/Autodesk/XLB)
   - Install **[verified]**: `pip install "xlb[warp]"` (single GPU) or `"xlb[cuda]"` (JAX) — [GitHub](https://github.com/Autodesk/XLB)
   - Geometry **[verified]**: a 3D mesh voxelizer using trimesh. Boundary conditions include half-way and full-way bounce-back, interpolated bounce-back, Zou-He, regularized, extrapolation outflow and hybrid — [GitHub](https://github.com/Autodesk/XLB)
   - Turbulence **[verified]**: Smagorinsky LES, plus BGK and KBC collision. The README says KBC is "unconditionally stable" for high Re, and KBC needs D3Q27 — [GitHub](https://github.com/Autodesk/XLB)
   - Car example **[verified]**: a DrivAer car in a wind tunnel with KBC at about 317M cells. Other showcases: an airfoil at about 10M cells and a cavity at Re 1e5 with about 25M cells. No timings are given — [XLB examples](https://xlb.readthedocs.io/en/latest/examples.html)
   - The paper claims "billions of cells" and "giga-scale lattice updates per second", with no single-GPU number in the abstract — [arXiv 2311.16080](https://arxiv.org/abs/2311.16080)
   - NVIDIA blog coverage of the Warp backend — [NVIDIA blog](https://developer.nvidia.com/blog/autodesk-research-brings-warp-speed-to-computational-fluid-dynamics-on-nvidia-gh200)
   - **Python API only**: all user code is Python. The kernels are JIT-compiled by JAX, Warp or Neon.

2. **lettuce, PyTorch LBM.** https://github.com/lettucecfd/lettuce
   - pip: `lettucecfd`, latest 0.3.0 (2026-10-06, Python >=3.12) — [PyPI JSON](https://pypi.org/pypi/lettucecfd/json)
   - Activity: 296 stars, last push 2026-10-06 — [GitHub API](https://api.github.com/repos/lettucecfd/lettuce)
   - **[verified]**: 2D and 3D, GPU through PyTorch, custom native CUDA kernels, tested on CUDA 12.4 to 13.0. A `lettuce benchmark` command reports MLUPS — [GitHub](https://github.com/lettucecfd/lettuce)
   - Speed **[verified, 2021 paper]**: on a V100 in FP64, about 140 MLUPS in 2D and 83 MLUPS in 3D (Taylor-Green). FP32 adds 60 to 75%. On a consumer RTX 2070S, 2D peaked at 58 MLUPS. This predates the native CUDA kernels — [arXiv 2106.12929](https://arxiv.org/pdf/2106.12929)
   - Obstacles and turbulence **[prior knowledge, unverified]**: an `Obstacle` flow class takes a boolean solid mask. Collision options include BGK, TRT, MRT, KBC, regularized and Smagorinsky. It ships a cylinder (Kármán street) example.
   - PyTorch CUDA wheels work on Windows **[prior knowledge]**.

3. **taichi_LBM3D (Taichi).** https://github.com/yjhp1016/taichi_LBM3D
   - Activity: 392 stars, last push 2025-04-07 — [GitHub API](https://api.github.com/repos/yjhp1016/taichi_LBM3D)
   - **[verified]**: D3Q19, MRT, sparse storage. Runs on CPU or GPU (CUDA, OpenGL). Single- and two-phase porous-media focus — [MDPI Fluids 2022](https://www2.mdpi.com/2311-5521/7/8/270)
   - Geometry is a voxel solid array (porous media). STL import is not confirmed — [Cranfield record](https://dspace.lib.cranfield.ac.uk/handle/1826/18328)
   - Taichi itself: pip `taichi` 1.7.4 (2025-07-31, Python <4.0) — [PyPI JSON](https://pypi.org/pypi/taichi/json). Activity: 28.4k stars, last push 2026-10-05 — [GitHub API](https://api.github.com/repos/taichi-dev/taichi). The PyPI release cadence has slowed (no release since mid-2025).

4. **Homebrew-CFD (Taichi LBM for external aero, F1 flagship).** https://github.com/JDavies101/Homebrew-CFD
   - Activity: 0 stars, last push 2026-10-15 — [GitHub API](https://api.github.com/repos/JDavies101/Homebrew-CFD)
   - Solver **[verified]**: a D3Q19 Taichi CUDA engine, with Warp named as fallback. Uses TRT or regularized collision, Smagorinsky then WALE LES, a log-law wall function and Bouzidi interpolated bounce-back.
   - Geometry and moving ground **[verified]**: STL voxelization (sphere Cd within 0.1%) and moving ground.
   - Validation **[verified]**: Ahmed body stable to Re_H 30k, cylinder St 0.171. Built on an RTX 3090 (24 GB). No full car run yet, and no MLUPS figures — [GitHub](https://github.com/JDavies101/Homebrew-CFD)
   - It is the closest match to the user's exact use case, but it is a single-author, unreviewed project.

5. **vivsim (JAX IB-LBM).** https://github.com/haimingz/vivsim
   - Install from source with `pip install -e .[cuda12]`. Not on PyPI ([PyPI JSON](https://pypi.org/pypi/vivsim/json) returned not found).
   - Activity: 47 stars, last push 2026-10-06 — [GitHub API](https://api.github.com/repos/haimingz/vivsim)
   - **[verified]**: D2Q9 and D3Q19. Collision options are BGK, MRT, KBC and regularized. Immersed boundary uses Peskin kernels with multi-direct forcing, plus bounce-back obstacles.
   - Examples **[verified]**: 2D VIV cylinder at Re 1e2 and 1e4, a 3D oscillating cylinder and a 3D sphere.
   - Benchmarks on an RTX 4090 **[verified]**: on a 128³ grid, streaming takes 0.81 ms and BGK collision 0.63 ms. On a 1024² grid, streaming takes 72 µs. No LES — [GitHub](https://github.com/haimingz/vivsim)

6. **lbmpy plus pystencils (FAU, code generation).** https://i10git.cs.fau.de/pycodegen/lbmpy
   - pip: `lbmpy` 2.1.1 (2026-09-30) and `pystencils` 2.1 (2026-09-29), both Python >=3.12 — [PyPI lbmpy](https://pypi.org/pypi/lbmpy/json), [PyPI pystencils](https://pypi.org/pypi/pystencils/json)
   - **[verified]**: generates C or CUDA LB kernels from symbolic collision operators. GPU is used via `Target.GPU` (CuPy arrays) — [lbmpy paper](https://arxiv.org/pdf/2001.11806); [tutorial](https://pycodegen.pages.i10git.cs.fau.de/lbmpy/notebooks/01_tutorial_predefinedScenarios.html)
   - Has predefined scenarios such as channel and obstacle flows. Collision options include cumulant, MRT, entropic and Smagorinsky **[prior knowledge, unverified]**.

7. **pylbm.** https://github.com/pylbm/pylbm
   - pip or conda-forge: `pylbm` 0.11.0 (2026-05-14) — [PyPI JSON](https://pypi.org/pypi/pylbm/json)
   - Activity: 170 stars, last push 2026-10-16 — [GitHub API](https://api.github.com/repos/pylbm/pylbm)
   - **[verified]**: 1D, 2D and 3D, d'Humières MRT, geometry built from simple shapes (circles, spheres), backends Cython, NumPy and Loo.py, MPI via mpi4py — [pylbm docs](https://pylbm.readthedocs.io/)
   - Not built for arbitrary STL. GPU support via Loo.py/OpenCL is uncertain.

8. **Sailfish (old Python LBM that generated CUDA/OpenCL).** https://github.com/sailfish-team/sailfish
   - Activity: 255 stars, last push 2022-02-03, so inactive — [GitHub API](https://api.github.com/repos/sailfish-team/sailfish)
   - **[verified]**: Python generates CUDA or OpenCL code, with D3Q19 support — [Palabos forum announcement](https://palabos-forum.unige.ch/t/announcing-project-sailfish/507)
   - Historical interest only.

#### Tier B: GPU or differentiable grid Navier-Stokes solvers

9. **PhiFlow (TUM).** https://github.com/tum-pbs/PhiFlow
   - pip: `phiflow` 3.4.0 (2025-08-02) and its core `phiml` 1.16.1 (2026-05-31) — [PyPI phiflow](https://pypi.org/pypi/phiflow/json), [PyPI phiml](https://pypi.org/pypi/phiml/json)
   - Activity: 1,950 stars, last push 2026-07-16 — [GitHub API](https://api.github.com/repos/tum-pbs/PhiFlow)
   - **[verified]**: backends NumPy, PyTorch, JAX and TensorFlow. The same code runs in 2D or 3D. Demos include wake flow, moving obstacles, a rotating bar, variable boundaries and a cylinder wake on a GMsh mesh. Optional custom CUDA ops — [GitHub](https://github.com/tum-pbs/PhiFlow)
   - Incompressible NS on staggered grids with obstacles as geometry masks **[prior knowledge]**. No dedicated turbulence model **[prior knowledge, unverified]**.

10. **PICT (TUM), PyTorch PISO solver.** https://github.com/tum-pbs/PICT
    - Activity: 58 stars, last push 2026-10-20 — [GitHub API](https://api.github.com/repos/tum-pbs/PICT)
    - **[verified]**: a differentiable incompressible PISO solver with custom CUDA ops, adaptive multi-block grids and generalized coordinates. Validated on cavity and turbulent channel flows, including a learned SGS model in 3D — [arXiv 2505.16992](https://arxiv.org/pdf/2505.16992); [ICML 2024](https://icml.cc/virtual/2024/37252)
    - Multi-block body-fitted grids can wrap a cylinder or airfoil, but not an arbitrary STL car.
    - The PyPI name `pict` (1.0.0, 2024-09-06) may be an unrelated package. Install from GitHub — [PyPI JSON](https://pypi.org/pypi/pict/json)

11. **JAX-Fluids (TUM AER), compressible.** https://github.com/tumaer/JAXFLUIDS
    - Activity: 660 stars, last push 2026-08-28 — [GitHub API](https://api.github.com/repos/tumaer/JAXFLUIDS)
    - Not on PyPI as `jaxfluids` ([PyPI JSON](https://pypi.org/pypi/jaxfluids/json) returned not found). Install from GitHub.
    - **[verified]**: immersed solid boundaries via a level-set method. Version 2.0 scales to 512 A100 GPUs and 1024 TPU v3 cores. Compressible two-phase focus — [JAX-Fluids 2.0, TUM](https://portal.fis.tum.de/en/publications/jax-fluids-20-towards-hpc-for-differentiable-cfd-of-compressible-/); [GitHub](https://github.com/tumaer/jaxfluids)
    - No IB-specific GPU throughput figure was found.
    - Compressible solvers need small time steps at low Mach. That makes them costly for road-car speeds (Mach about 0.1 to 0.3) **[inference]**.

12. **JAX-CFD (Google).** https://github.com/google/jax-cfd
    - pip: `jax-cfd` 0.2.1 (2024-05-13) — [PyPI JSON](https://pypi.org/pypi/jax-cfd/json)
    - **[verified]**: "no longer maintained". Finite volume on a staggered grid, plus pseudospectral, 2D demos. **Periodic boundaries only, so no obstacles**. The maintainers recommend JAX-Fluids, PhiFlow or Exponax instead — [GitHub](https://github.com/google/jax-cfd)
    - The GitHub API still shows a push on 2026-10-25 — [GitHub API](https://api.github.com/repos/google/jax-cfd)

13. **torch-cfd (a PyTorch port of JAX-CFD).** https://github.com/scaomath/torch-cfd
    - pip: `torch-cfd` 0.2.6 (2025-06-26) — [PyPI JSON](https://pypi.org/pypi/torch-cfd/json)
    - Activity: 88 stars, last push 2025-11-21 — [GitHub API](https://api.github.com/repos/scaomath/torch-cfd)
    - **[verified]**: a PyTorch port of JAX-CFD built from `nn.Module` pieces with batching, plus a neural-operator-assisted NS solver (ICLR 2025) — [libraries.io](https://libraries.io/pypi/torch-cfd)
    - Inherits JAX-CFD's periodic-domain focus **[inference]**.

14. **NVIDIA Warp (`warp-lang`).** https://github.com/NVIDIA/warp
    - pip: 1.18.0 (2026-10-05) — [PyPI JSON](https://pypi.org/pypi/warp-lang/json)
    - Activity: 7.2k stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/NVIDIA/warp)
    - Examples **[verified]**: `warp.fem` ships `example_navier_stokes.py` (2D unsteady NS, mixed Pk/Pk-1 elements, semi-Lagrangian advection) and `example_taylor_green.py` — [Warp FEM docs](https://nvidia.github.io/warp/latest/domain_modules/fem.html)
    - A 2D Eulerian `example_fluid.py` (stable-fluids type) exists — [mirror copy](https://huggingface.co/spaces/qbhf2/GarmentCode/blob/main/NvidiaWarp-GarmentCode/examples/example_fluid.py)
    - No official Warp LBM example was found. XLB is the Warp-based LBM.
    - Warp has native Windows CUDA wheels **[prior knowledge]**.

15. **Exponax (JAX ETDRK pseudo-spectral).** https://github.com/Ceyron/exponax
    - pip: `exponax` 0.2.0 (2026-02-20) — [PyPI JSON](https://pypi.org/pypi/exponax/json)
    - Activity: 233 stars, last push 2026-06-01 — [GitHub API](https://api.github.com/repos/Ceyron/exponax)
    - **[verified]**: **periodic domains only**, 1D, 2D and 3D, differentiable. Used by APEBench (46 PDEs) — [APEBench arXiv](https://arxiv.org/pdf/2411.00180)
    - Has no obstacle support, so it is not suitable here.

16. **2d-fluid-simulator (Taichi).** https://github.com/takah29/2d-fluid-simulator
    - Activity: 144 stars, last push 2025-08 — [GitHub topic](https://github.com/topics/navier-stokes?l=python&o=desc&s=stars)
    - **[verified]**: 2D incompressible finite-difference MAC solver. Advection options are upwind, Kawamura-Kuwahara and CIP. Has vorticity confinement, 6 boundary-condition presets, and CPU or GPU runs (GTX 1080 or better recommended) — [GitHub](https://github.com/takah29/2d-fluid-simulator)
    - Obstacle presets are likely but not documented.

17. **LBM_Taichi (hietwll).** https://github.com/hietwll/LBM_Taichi
    - Activity: 243 stars, last push 2023-06-18 — [GitHub API](https://api.github.com/repos/hietwll/LBM_Taichi)
    - A 2D Taichi LBM with a cylinder (Kármán) case **[prior knowledge, unverified]**.

#### Tier C: unstructured high-order and FEM/FV frameworks (accurate but heavier)

18. **PyFR.** https://github.com/PyFR/PyFR
    - pip: `pyfr` 3.1 (2026-03-13) — [PyPI JSON](https://pypi.org/pypi/pyfr/json)
    - Activity: 580 stars, last push 2026-10-21 — [GitHub API](https://api.github.com/repos/PyFR/PyFR)
    - **[verified]**: high-order flux reconstruction for compressible and artificial-compressibility incompressible NS. Backends include CUDA (`-b cuda`), plus HIP, OpenCL and OpenMP **[prior knowledge for the full list]**. Ships a tutorial: 2D incompressible cylinder on a mixed Gmsh mesh — [PyFR examples](https://pyfr.readthedocs.io/en/v3.1/_sources/examples.rst.txt)
    - Turbulence is ILES (Re 3900 cylinder study) — [PyFR heterogeneous paper](https://ar5iv.arxiv.org/html/1409.0405)
    - Needs a body-fitted unstructured mesh (Gmsh), so a full-car mesh workflow is heavy. No laptop timing was found.

19. **FEniCSx / DOLFINx.** https://github.com/FEniCS/dolfinx
    - 1,239 stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/FEniCS/dolfinx)
    - Python FEM. NS around a cylinder is a standard tutorial **[prior knowledge]**.
    - On Windows it effectively needs conda or WSL **[prior knowledge]**. CPU only (PETSc), so 3D car cases are slow.
    - Related: cbcflow, an older FEniCS NS framework with a FlowAroundCylinder demo — [cbcflow docs](https://cbcflow.readthedocs.io/en/stable/Demos/FlowAroundCylinder/documentation.html)

20. **Firedrake.** https://github.com/firedrakeproject/firedrake
    - 681 stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/firedrakeproject/firedrake)
    - Automated FEM. CPU, PETSc. Linux, macOS or WSL **[prior knowledge]**.

21. **PyMFEM (`mfem`).** https://github.com/mfem/PyMFEM
    - pip: `mfem` 4.10.0 (2026-09-21) — [PyPI JSON](https://pypi.org/pypi/mfem/json)
    - Activity: 301 stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/mfem/PyMFEM)
    - A Python wrapper for MFEM, which has a C++ NS miniapp. The pip wheel is CPU **[prior knowledge, unverified]**.

22. **scikit-fem.** https://github.com/kinnala/scikit-fem
    - pip: `scikit-fem` 12.0.2 (2026-06-05) — [PyPI JSON](https://pypi.org/pypi/scikit-fem/json)
    - Pure-NumPy FEM assembly. Steady NS or Stokes around obstacles is possible in 2D, but this is a toolkit, not a ready flow solver **[prior knowledge]**.
    - Listed in awesome-fluid-dynamics — [awesome-fluid-dynamics](https://github.com/lento234/awesome-fluid-dynamics)

23. **Kratos Multiphysics (FluidDynamicsApplication).** https://github.com/KratosMultiphysics/Kratos
    - pip: `KratosMultiphysics` and `KratosFluidDynamicsApplication` 10.4.4 (2026-09-28) — [PyPI JSON](https://pypi.org/pypi/KratosFluidDynamicsApplication/json)
    - Activity: 1,390 stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/KratosMultiphysics/Kratos)
    - C++ FEM scripted from Python. Supports embedded or immersed (level-set) bodies, VMS stabilisation and Windows wheels **[prior knowledge, unverified]**. CPU only.

24. **FiPy (NIST).** https://github.com/usnistgov/fipy
    - pip: `fipy` 4.0.3 (2026-06-18) — [PyPI JSON](https://pypi.org/pypi/fipy/json)
    - Activity: 643 stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/usnistgov/fipy)
    - A finite-volume PDE toolkit. Not designed for NS or obstacle flow (no built-in pressure-velocity coupling solver) **[prior knowledge]**. Poor fit.

25. **Dedalus (spectral).** https://github.com/DedalusProject/dedalus
    - pip: `dedalus` 3.0.5 (2026-01-31) — [PyPI JSON](https://pypi.org/pypi/dedalus/json)
    - Activity: 711 stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/DedalusProject/dedalus)
    - Spectral, CPU, MPI. Obstacles are possible only through volume penalization masks **[prior knowledge, unverified]**. Not suited to bluff-body car flow.

26. **Shenfun (spectral Galerkin).** https://github.com/spectralDNS/shenfun
    - pip or conda: `shenfun` 4.3.0 (2026-06-03) — [PyPI JSON](https://pypi.org/pypi/shenfun/json)
    - Activity: 232 stars, last push 2026-10-14 — [GitHub API](https://api.github.com/repos/spectralDNS/shenfun)
    - Simple tensor-product domains (channel, periodic box). No obstacles **[prior knowledge]**.

27. **FluidSim (fluiddyn).** https://github.com/fluiddyn/fluidsim
    - pip: `fluidsim` 26.10.0 (2026-10-09) — [PyPI JSON](https://pypi.org/pypi/fluidsim/json)
    - Activity: 80 stars, last push 2026-10-23 — [GitHub API](https://api.github.com/repos/fluiddyn/fluidsim)
    - Pseudo-spectral periodic solvers (ns2d, ns3d, stratified) accelerated with Pythran — [FluidSim paper](https://arxiv.org/pdf/1807.01769)
    - No solid obstacles **[prior knowledge]**.

28. **Clawpack / PyClaw.** https://github.com/clawpack/pyclaw
    - pip: `clawpack` 5.14.0 (2026-01-27) — [PyPI JSON](https://pypi.org/pypi/clawpack/json)
    - PyClaw: 187 stars, last push 2026-10-16 — [GitHub API](https://api.github.com/repos/clawpack/pyclaw)
    - Finite-volume hyperbolic solvers (Euler and shallow water), Fortran kernels, CPU. Inviscid, with no general embedded-body support **[prior knowledge]**.
    - The PyPI name `pyclaw` (0.0.3) is a different, unrelated package — [PyPI JSON](https://pypi.org/pypi/pyclaw/json)

29. **pyro2 (python-hydro).** https://github.com/python-hydro/pyro2
    - Activity: 335 stars, last push 2026-10-14 — [GitHub API](https://api.github.com/repos/python-hydro/pyro2)
    - A teaching hydro code (compressible, incompressible, low-Mach), 2D and CPU. The PyPI name `pyro2` was not found; it may be published as `pyro-hydro` **[unverified]**.

30. **SU2 (Python wrapper) and code_saturne.** These are C++ codes with Python scripting, listed in awesome-fluid-dynamics — [awesome-fluid-dynamics](https://github.com/lento234/awesome-fluid-dynamics)
    - They are full RANS solvers and as heavy as OpenFOAM. Noted for completeness only.

#### Tier D: particle and vortex methods

31. **PySPH.** https://github.com/pypr/pysph
    - pip: `pysph` 1.0b2 (2025-05-23) — [PyPI JSON](https://pypi.org/pypi/pysph/json)
    - Activity: 549 stars, last push 2026-08-23 — [GitHub API](https://api.github.com/repos/pypr/pysph)
    - **[verified]**: has a "flow past a circular cylinder" example in 2D with open boundaries — [PySPH examples](https://pysph.readthedocs.io/en/main/examples/index.html)
    - GPU via OpenCL or CUDA through compyle **[prior knowledge, unverified]**.
    - Weakly compressible SPH needs many particles for aero-quality wakes **[inference]**.

32. **Omega2D and Omega3D (Mark Stock), vortex particle methods.**
    - [Omega2D](https://github.com/Applied-Scientific-Research/Omega2D): 2D vortex particles plus boundary-element method, GUI. 36 stars, last push 2025-02-15.
    - [Omega3D](https://github.com/Applied-Scientific-Research/Omega3D): GPU 3D vortex methods. 21 stars, last push 2024-10-26.
    - Both from the [GitHub API](https://api.github.com/repos/Applied-Scientific-Research/Omega3D).
    - These are **C++, not Python**. They are listed because no maintained pip vortex-particle package was found.

33. **viVorticity2D.** A Python/Cython 2D variational vorticity integrator. Built with make, inactive — [GitHub](https://github.com/DDMGNI/viVorticity2D)

34. **CVortex.jl.** A GPU (OpenCL) 3D vortex particle and filament library. Julia only, on Windows or Linux 64-bit — [docs](https://docs.juliahub.com/General/CVortex/stable/)
    - No Python binding was found.

35. **PteraSoftware** (pip `pterasoftware` 5.1.0, 2026-07-15) — [PyPI JSON](https://pypi.org/pypi/pterasoftware/json)
    - An unsteady vortex-lattice method (potential flow with wake shedding). It is not a viscous bluff-body solver, but its wakes could look plausible. Listed in awesome-fluid-dynamics — [awesome-fluid-dynamics](https://github.com/lento234/awesome-fluid-dynamics)

#### Tier E: teaching codes, small scripts, RL environments

36. **CFDPython (Barba, "12 steps to NS").** https://github.com/barbagroup/CFDPython
    - 4,190 stars, last push 2024-03-19 — [GitHub API](https://api.github.com/repos/barbagroup/CFDPython)
    - Teaching notebooks, NumPy. No obstacle solver.

37. **jviquerat/lbm.** https://github.com/jviquerat/lbm
    - A full-Python 2D LBM with obstacles (cylinder, random shapes). 210 stars, last push 2023-04-28 — [GitHub API](https://api.github.com/repos/jviquerat/lbm)
    - Obstacle details are **[prior knowledge]**.

38. **pmocz/latticeboltzmann-python.** https://github.com/pmocz/latticeboltzmann-python
    - A roughly 100-line NumPy D2Q9 cylinder demo. 236 stars, last push 2025-05-08 — [GitHub API](https://api.github.com/repos/pmocz/latticeboltzmann-python)

39. **GregTJ/stable-fluids.** A minimal NumPy stable-fluids solver. 215 stars, last push 2022 — [GitHub API](https://api.github.com/repos/GregTJ/stable-fluids)

40. **PyFluidDynamics.** 2D incompressible NS by finite differences. 108 stars, last push 2026-09-01 — [GitHub API](https://api.github.com/repos/Ali-Marandi/PyFluidDynamics)

41. **Fluid2d.** A Python-Fortran 2D solver for many flow types. 69 stars, last push 2024-05-09 — [GitHub API](https://api.github.com/repos/pvthinker/Fluid2d)

42. **HydroGym.** https://github.com/dynamicslab/hydrogym
    - pip: `hydrogym` 1.0.0 (2026-04-24) — [PyPI JSON](https://pypi.org/pypi/hydrogym/json)
    - Activity: 557 stars, last push 2026-10-26 — [GitHub API](https://api.github.com/repos/dynamicslab/hydrogym)
    - An RL gym around flow-control benchmarks such as the cylinder wake and pinball, built on Firedrake FEM **[prior knowledge for the backend]**.

43. **OpenSBLI.** https://github.com/opensbli/opensbli
    - A Python code generator for finite-difference compressible solvers (OPS backend). 113 stars, updated 2026-10 — [GitHub topic](https://github.com/topics/computational-fluid-dynamics?l=python&o=desc&s=stars)
    - Heavy HPC orientation.

44. **Recent small GPU LBM repos** from a sweep of the Python lattice-boltzmann topic. All have 0 to 3 stars and are unreviewed — [GitHub topic sweep](https://github.com/topics/lattice-boltzmann?l=python&o=desc&s=updated)
    - fluxlb (PyTorch, differentiable LBM)
    - washout (GPU LBM wind tunnel combined with a vortex-lattice method for flying wings)
    - urbancool-jax (JAX thermal LBM)
    - gelb (LBM DSL that generates CUDA)

45. **Kummerländer symlbm_playground.** A Python, SymPy and PyOpenCL LBM including a 3D benchmark. Hosted on a personal git server — [code.kummerlaender.eu](https://code.kummerlaender.eu/symlbm_playground/plain/ldc_3d_benchmark.py)
    - Obstacle and interactive details are **[prior knowledge, unverified]**.

46. **2d-lb (btweinstein).** A Cython and pyOpenCL D2Q9 code, about 325 MLUPS on a GTX Titan Black — [GitHub](https://github.com/btweinstein/2d-lb)

#### Noted only (other agents cover these, or they are out of scope)

- **AeroSandbox** (`aerosandbox` 4.2.10, 2026-07-05) and **NeuralFoil** (`neuralfoil` 0.3.3, 2026-07-11) — [PyPI aerosandbox](https://pypi.org/pypi/aerosandbox/json), [PyPI neuralfoil](https://pypi.org/pypi/neuralfoil/json)
  - These are aero-design tools (VLM, panel, neural airfoil), not field solvers.
- **Genesis** (`genesis-world` 1.4.5, 2026-10-22) — [PyPI JSON](https://pypi.org/pypi/genesis-world/json)
  - A physics or robotics engine with an SPH fluid module. It is borderline "engine" and out of scope.
- **ML surrogates and data**, not physics solvers:
  - DrivAerNet: a car CFD dataset, 555 stars — [GitHub topic](https://github.com/topics/computational-fluid-dynamics?l=python&o=desc&s=stars)
  - PaddleCFD, CFDBench and DeepXDE.
- **Not found or not existing as Python packages:** TCLB-python (TCLB is C++ and R; no Python package seen), "pyCFD" (no notable maintained package found), "pyvortex" (no maintained package found), Basilisk Python (could not verify this session).

### Inferences
- **Windows constraint.** JAX publishes CUDA wheels for Linux only, so XLB-JAX, JAX-Fluids, vivsim and Exponax need WSL2 for GPU on Windows 11 **[prior knowledge, high confidence]**. Warp, PyTorch, Taichi and CuPy run CUDA natively on Windows. On this laptop, that makes **XLB with the Warp backend, lettuce (PyTorch) and Taichi-based LBM** the lowest-friction GPU options.
- **Memory budget.** A D3Q19 FP32 LBM with two populations is about 19 × 4 B × 2 = 152 B per cell. With macroscopic fields and mask added, that is roughly 160 to 200 B per cell. 8 GB VRAM therefore caps out at about 40 to 50M cells. At a 1 cm cell, a 5.6 × 2 × 1 m car needs a domain of about 1,100 × 400 × 150 cells, which is about 66M cells and too big. **5 to 10M cells (2 to 3 cm cells) are realistic.** That is a coarse "visual-grade" wake, not a converged downforce number.
- **Speed estimate.** The RTX 4060 Laptop has about 256 GB/s memory bandwidth **[prior knowledge]**. Bandwidth-bound LBM then gives an ideal ceiling of about 1.5 GLUPS, and realistic Python-JIT LBM (Warp or Taichi) reaches about 0.4 to 1 GLUPS.
  - A 10M-cell grid then runs about 50 to 100 steps per second.
  - The flow needs about 3 to 5 domain flow-throughs to develop, which is roughly 5,000 to 20,000 steps.
  - That makes **about 1 to 5 minutes per attitude snapshot** plausible. This is an extrapolation, not a measured figure.
- **Lap workflow.** For a lap sequence, the most efficient pattern is one long run with time-varying inflow speed and yaw, plus a voxel mask that is re-rasterized for ride height and pitch. This avoids separate steady runs per corner.
- **Moving ground** is a simple moving-wall (Zou-He or equilibrium velocity) boundary condition on the floor in any LBM package. Homebrew-CFD advertises it explicitly. In XLB it would be an equilibrium or regularized boundary with a tangential velocity **[inference]**.
- **For a top-down 2D visual,** a 2D LBM slice (D2Q9 with KBC or Smagorinsky) at 4096 × 1024 runs at real-time-ish rates on this GPU (vivsim's 1024² streaming step takes 72 µs on a 4090). It is not a physically valid 3D downforce result, but it is extremely cheap.

### Gaps
- No published MLUPS figure was found for XLB-Warp, lettuce native-CUDA, Taichi LBM or PhiFlow on an RTX 4060 Laptop or similar GPU. Benchmarks need to be run locally (`lettuce benchmark`, XLB examples, vivsim `benchmark3d.py`).
- Lettuce obstacle and collision features, lbmpy collision list, PySPH GPU backend, Kratos embedded-body support and Dedalus penalization were not re-verified this session because the search budget was exhausted.
- Basilisk's Python interface was not checked. Basilisk is a C code with an optional, poorly documented Python/SWIG interface **[prior knowledge, low confidence]**.
- The Taichi PyPI release cadence has stalled (1.7.4 in July 2025). Its long-term maintenance status is unclear.
- The XLB-Warp backend on Windows is not explicitly documented. The README mentions only Linux for Neon and macOS CPU.
- The GitHub topic pages only showed the first 20 results each. The lattice-boltzmann topic has 61 Python repos, navier-stokes has 120 and fluid-simulation has 119, so the long tail is unexplored.
- The r/CFD and r/Python sweep was not performed, because the search budget ran out.

## Q2. Which packages are the shortlist for the user's F1 top-down use case?

### Takeaway
Ranked by fit (3D external aero, STL car, moving ground, high Re, laptop GPU, Windows, Python):

1. **XLB (`xlb[warp]`)** has KBC plus Smagorinsky, a trimesh voxelizer, a DrivAer showcase and maintained industrial backing.
2. **lettuce** is pure pip on Windows via PyTorch and has native CUDA kernels.
3. **A hand-rolled Warp or Taichi D3Q19 kernel** (about 300 lines) gives full control over the treadmill floor and time-varying inflow. Homebrew-CFD is a reference implementation of exactly this.
4. **PhiFlow** is easier for 2D top-down slices and differentiable experiments, but slower and without a turbulence model.

### Cited Findings
- XLB features (KBC, Smagorinsky, trimesh voxelizer, Warp single-GPU) — [GitHub](https://github.com/Autodesk/XLB)
- XLB DrivAer showcase — [examples](https://xlb.readthedocs.io/en/latest/examples.html)
- lettuce pip install, 2D/3D, native CUDA — [GitHub](https://github.com/lettucecfd/lettuce)
- Lettuce 2021 speeds — [arXiv](https://arxiv.org/pdf/2106.12929)
- Homebrew-CFD (Taichi D3Q19, WALE LES, Bouzidi, STL, moving ground, F1 target) — [GitHub](https://github.com/JDavies101/Homebrew-CFD)
- PhiFlow obstacles and wake demos — [GitHub](https://github.com/tum-pbs/PhiFlow)
- JAX-CFD deprecated, periodic only — [GitHub](https://github.com/google/jax-cfd)

### Inferences
- The packages that are pure-periodic or spectral should be ruled out for obstacle aero: Exponax, JAX-CFD, torch-cfd, FluidSim, Shenfun and largely Dedalus.
- CPU FEM frameworks are too slow for per-weekend 3D car runs: FEniCSx, Firedrake, PyMFEM, Kratos and scikit-fem.
- PyFR is accurate but needs a body-fitted car mesh, which brings back the heavy mesh workflow the user wants to avoid.
- Any of these gives a qualitative wake and relative downforce trends at 5 to 10M cells. Absolute downforce values will not match real F1 figures without calibration.

### Gaps
- No package was found that already implements "car fixed, rolling road, lap-varying attitude" end to end. Homebrew-CFD claims the pieces, but no full car has been run yet.
- No head-to-head benchmark across XLB, lettuce and Taichi on the same GPU was found.
