# Open F1 / open-wheel geometries for CFD, and prior art for airflow-over-a-lap visualisation

Researched 2026-10-26. Licence status is reported exactly as found. "Not stated" means the page showed no licence; it does not mean the model is free to use.

## Q1. Which open, CFD-ready F1 or open-wheel geometries exist, and under what licences?

### Takeaway
There is no public, openly licensed, regulation-accurate F1 car. The FIA's 2026 reference geometry is CAD that only F1 teams can download. Every F1-looking model I found has either no stated licence or a restrictive one (non-commercial, no derivatives, or a custom licence). The models that are clearly licensed are generic baselines: DrivAer, Ahmed and Windsor bodies. A genuine F1-shaped geometry therefore means one of three things: (a) build a simplified car yourself from the published 2026 FIA rule text; (b) clear the licence of a hobbyist model with its author; or (c) accept the licence risk, which matters because the content is for YouTube.

### Cited Findings

**FIA / official geometry**
- In the 2026 F1 Technical Regulations (Section C, Issue 17, 28 April 2026), Appendix 1.6 says the CAD models of all reference volumes and surfaces "are available for F1 Teams or PU Manufacturers to download". Appendix 2.1 says the legality volumes are "defined exclusively by CAD data and are available to download from the FIA's CAD Portal". There is no public release. — [FIA 2026 Section C Iss.17](https://api.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_c_technical_-_iss_17_-_2026-04-28.pdf)
- The FIA and F1 built a 2021/22 concept car for their CFD work on AWS. Press coverage did not report any public release of that model. — [Amazon press release](https://press.aboutamazon.com/2019/12/formula-1-works-with-aws-to-develop-next-generation-race-car); [search summary of engineering.com](https://www.engineering.com/?p=43773). Uncertainty: absence is inferred from no release being found.
- From 2022, some parts are "Open Source Components" that teams must publish on an FIA-hosted server. That is a regulatory sharing mechanism between teams, not a public licence. — [The Race explainer](https://www.the-race.com/formula-1/f1s-move-to-encourage-copying-of-rival-designs-explained.md) (seen only as a search snippet).

**F1-looking hobbyist and student models**
- **Mercedes F1 W14 (2023) by "3dblenderlol"**, from downloadfree3d.com. This is the model FluidX3D's own F1 example uses. It was made in Blender, is tagged .glb, is a 7 MB zip and has separate wheel meshes. The page states **no licence and no commercial or personal-use terms**. — [downloadfree3d page](https://downloadfree3d.com/3d-models/vehicles/sports-car/mercedes-f1-w14/)
  - FluidX3D's setup.cpp notes how the author prepared it for LBM: "wheels separated, decals removed and converted to .stl in Microsoft 3D Builder" and "to avoid instability from too small gaps: remove front wheel fenders and move out right back wheel a bit". — [FluidX3D src/setup.cpp](https://github.com/ProjectPhysX/FluidX3D/blob/master/src/setup.cpp)
- **LEAF1 F1 in Schools 2022/23 (Printables)**. The team published its CAD, CAM and CFD files, including a simplified "Car for CFD" body for SimScale. No licence appeared in the search snippet, and the page returned HTTP 403 when fetched, so the **licence is unverified**. This is a small CO2-dragster competition car, not a full-size F1 car. — [Printables](https://www.printables.com/model/381830-leaf1-f1-in-schools-20222023-season-upload)
- **PERRINN F1 car (Onshape public documents)**. PERRINN calls its designs "open-access" rather than open source, because it vets who may contribute. **No licence was found** in the sources. — [Onshape blog](https://www.onshape.com/en/blog/using-onshapes-free-plan-to-design-a-race-car); [GfxSpeak](https://gfxspeak.com/archives/formula-designer-engineering/)
- **CAEdevice "Formula CFD" reference car (MVRC spin-off)**. A STEP model with boundary conditions, shared on a forum and described as open. **No formal licence**, and the author calls it a realistic reference rather than a detailed car. — [F1Technical forum](https://f1technical.net/forum/viewtopic.php?p=963120)
- **2026-era hobby models**:
  - Sketchfab account "excalibur" lists an F1 2026 Ferrari SF-26 and an Audi R26; the licence was not visible. [Sketchfab](https://sketchfab.com/excalibur)
  - CGTrader "F1 2026 Release Car" is free but under a Custom Licence (no AI, credit the designer). [CGTrader](https://www.cgtrader.com/free-3d-models/car/racing-car/f1-2026-release-car)
  - The CGTrader Audi R26 is paid. [CGTrader](https://www.cgtrader.com/3d-models/car/racing-car/f1-2026-audi-r26-formula-1-race-car-3d-model)
  - The MakerWorld "2026 F1 Car Template" restricts sharing and derivatives. [MakerWorld](https://makerworld.com/models/2527485)
  - An itch.io F1 2026 Blender FBX is a purchase. [itch.io](https://campiaogames.itch.io/f1-2026-car-made-with-blenderfbx)
  - All of these licence details come from search snippets; individual pages were not opened.
- **Community 2026 CFD car: Emil Qvist's model, simulated on AirShaper**. About 100M cells; reported Cd 0.797, Cl −2.398, L/D −3.0. These figures come from a LinkedIn post and are **unverified**. The geometry licence is unknown. — [LinkedIn, Emil Qvist](https://se.linkedin.com/in/emil-qvist)
- **Maya HTT** built a "simplified CFD-ready CAD model" from the FIA 2026 regulations in Siemens NX, with the new front and rear wings in cornering and straight-line modes, and ran steady RANS. The page returned 403, so whether the geometry is shared is **unknown**. — [Maya HTT blog](https://www.mayahtt.com/blog/chasing-400-kmh-how-fast-will-the-2026-f1-cars-be/)
- **UPC Barcelona thesis**. A 2026 car built in CATIA and simulated in SimScale, with front wing, floor, rear wing and full car in X and Z mode. Geometry availability and licence were not checked. — [UPC thesis PDF](https://upcommons.upc.edu/bitstreams/268a2d46-f8df-4e01-9baf-e2b775c879c9/download)
- **Public SimScale projects** include "F1 2022 regulations", "f1_2026_regulation_car" and "F126 project". SimScale public projects can be copied. Licence terms were not checked. — [SimScale 2022](https://www.simscale.com/projects/mmassimo/formula_1_2022_cfd_simulation_-_copy/); [SimScale 2026](https://www.simscale.com/projects/reesewu2005/f1_regulation_car/)

**Generic baselines (clearly licensed or freely available)**
- **DrivAer (TU Munich)**, a road-car body.
  - Availability: the main TUM page says the geometry can be downloaded, while the geometry page says "available on request". Formats are .IGES or .STEP. There are 18 mock-up configurations (fastback, notchback, estate; smooth or detailed underbody; with or without mirrors and wheels).
  - **No licence text** appears on the geometry page; contact aerodynamik@tum.de.
  - Sources: [TUM geometry page](https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/geometry/); [TUM DrivAer](https://www.epc.ed.tum.de/en/aer/research-groups/automotive/drivaer/). A Cranfield copy also offers STL and Parasolid. [figshare](https://figshare.com/articles/_Cranfield_DrivAer_CAD_Pack_2_Rear-end_Standard_DrivAer_/6086822)
- **DrivAerNet** (parametric DrivAer dataset) is **CC BY-NC**, which does not permit commercial use, according to the AhmedML paper's comparison. — [AhmedML arXiv 2407.20801](https://export.arxiv.org/pdf/2407.20801); [DrivAerNet GitHub](https://github.com/mohamedelrefaie/drivaernet)
- **AhmedML**: 500 Ahmed-body variants, about 20M-cell hybrid RANS-LES in OpenFOAM, with the case setup included. **CC-BY-SA**. — [arXiv 2407.20801](https://arxiv.org/html/2407.20801v1)
- **WindsorML**: 355 Windsor-body variants, wall-modelled LES with more than 280M cells. The paper calls the licence "permissive open-source" (CC-BY-SA according to the AhmedML/WindsorML papers). — [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/42a59a5f35b1b3c3fd648397c88a7164-Abstract.html); [arXiv 2407.19320](https://arxiv.org/html/2407.19320v4)

**2026 regulation facts that matter for the airflow (FIA and F1 primary sources)**
- **Headline changes**: 30% less downforce and 55% less drag. Maximum wheelbase 3400 mm (−200 mm), maximum width 1900 mm (−100 mm), minimum mass 768 kg (−30 kg). 18-inch wheels retained. Front tyres 25 mm narrower, rears 30 mm narrower. — [Formula1.com FIA unveil](https://www.formula1.com/en/latest/article/fia-unveils-formula-1-regulations-for-2026-and-beyond-featuring-more-agile.75qJiYOHXgeJqsVQtDr2UB)
- **Front wing (C3.10.10)**:
  - The FW Primary Flap and FW Secondary Flap switch between a "Corner Mode" position and a "Straight Mode" position. Straight Mode gives "a decrease in incidence", and the size of that decrease must stay constant.
  - Maximum transition time is **400 ms**. Up to two actuators. Symmetric about Y=0.
  - On failure the wing returns to Corner Mode.
  - The wing may be deployed only when the car is stationary or fully inside an Activation Zone (B7.1.1(d)).
  - Source: [FIA Section C Iss.17](https://api.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_c_technical_-_iss_17_-_2026-04-28.pdf)
- **Rear wing (C3.11.6)**:
  - The "RW Flap" rotates about a fixed axis aligned with the Y-axis. In Corner Mode that axis lies within RV-RW-PROFILES, between the rearmost point and the mid-chord of the flap at Y=50.
  - Straight Mode gives a decrease in incidence whose size "must always remain identical".
  - Maximum transition time is 400 ms. Single actuator. The flap fails safe to Corner Mode.
  - Source: same FIA PDF.
- **Naming**: the official text says "Corner Mode" and "Straight Mode". Press used "Z-mode" (high downforce) and "X-mode" (low drag), and Racer reports a two-element active front wing with a three-element active rear wing. — [F1Technical F1MATHS](https://www.f1technical.net/news/28129); [Racer](https://racer.com/2024/06/06/why-active-aero-is-part-of-the-2026-f1-regulations/)
- **No flap angle in degrees** is fixed in the extracted rule text. The magnitude is the team's choice, limited by the physical stops and RV-FW-PROFILES. — [FIA Section C Iss.17](https://api.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_c_technical_-_iss_17_-_2026-04-28.pdf). This comes from my reading of the extracted text; a closer search of the PDF might still find one.

### Inferences
- For a YouTube-safe 2026 car, the cleanest route is a self-built, simplified, rules-informed body: the published dimensions, two-mode front and rear flaps, and an approximate floor and diffuser. You hold the rights, and the Corner/Straight flap rotation can be modelled exactly as the rules describe (a fixed rotation about one axis, over 400 ms or less). The Maya HTT and UPC projects show this approach is the accepted one.
- The W14 model that FluidX3D uses is technically proven for LBM, but it has no licence. Publishing videos of it is a copyright risk, and the team livery or branding adds trademark risk.

### Gaps
- Exact licences for LEAF1 (Printables returned 403), the Sketchfab "excalibur" F1 2026 models, PERRINN and the TUM DrivAer download page could not be confirmed.
- Not searched in depth: GrabCAD F1 models, Thingiverse F1 models (the stlfinder listing "f1" by karthikv, thing 5044800, has no licence information), and open Formula Student car models such as team GitHub CAD releases.
- I could not find whether any of the hobby models are watertight. This has to be checked per mesh with the tools in Q2.

## Q2. Which tools repair meshes for CFD and LBM voxelisation?

### Takeaway
FluidX3D needs binary STL that is **watertight, with outward-facing normals**. PyMeshFix (open source) and ManifoldPlus (non-commercial only) automate repair, and the FluidX3D author recommends Microsoft 3D Builder or Blender. LBM's voxelisation hides small surface defects but not open holes or flipped normals.

### Cited Findings
- FluidX3D: "Only binary .stl files are supported. Meshes must be watertight (no holes) and all triangles must be oriented such that their normals point to the outside." For converting and splitting, it recommends Microsoft 3D Builder (Windows) or Blender. Rotating parts such as wheels must be revoxelised every 1–10 steps; alternatively, the `voxelize_mesh_on_device(..., omega)` moving-boundary option gives wheels a surface velocity. — [FluidX3D DOCUMENTATION.md](https://github.com/ProjectPhysX/FluidX3D/blob/master/DOCUMENTATION.md)
- **PyMeshFix** is a Python wrapper of Marco Attene's MeshFix and outputs a single watertight triangle mesh. It assumes the input is a single closed solid, and it may give coarse results on tessellated CAD. It installs from PyPI. — [pymeshfix docs](https://pymeshfix.pyvista.org/); [GitHub](https://github.com/pyvista/pymeshfix)
- **ManifoldPlus** turns triangle soups into watertight manifolds through voxel-boundary extraction and projection. Input is OBJ or OFF; output is OBJ. Usage: `--depth 8`. The licence is **free for non-commercial use only**. — [GitHub hjwdzh/ManifoldPlus](https://github.com/hjwdzh/manifoldplus); [arXiv 2005.11621](https://arxiv.org/pdf/2005.11621)

### Inferences
- The content goes to monetised YouTube, so ManifoldPlus's non-commercial licence makes it a risk for production use. PyMeshFix, Blender (GPL; its output is yours) and 3D Builder avoid that problem.

### Gaps
- Licences and capabilities of MeshLab, Blender's 3D-Print Toolbox and the `manifold` library were not fetched in this pass. As general knowledge, which I did not verify here: MeshLab is GPL and Blender is GPL.

## Q3. Prior art: who has published F1 airflow simulations, with what tools, and how did they visualise them?

### Takeaway
The closest technical match is FluidX3D, a GPU lattice-Boltzmann code. It has a ready-made "Mercedes F1 W14" setup with rotating wheels, moving ground and Q-criterion rendering at a few-GB VRAM size, and its author published a 10-billion-voxel Ferrari SF71H run. **Its licence prohibits commercial use**, which matters for monetised YouTube. I found no published work that simulates attitude or speed changes through a real lap. Lap-related aero work in industry and academia uses aero maps (ride height, roll, yaw and steer sweeps fed into a surrogate model), not time-resolved CFD.

### Cited Findings
- **FluidX3D (Moritz Lehmann / ProjectPhysX)**:
  - OpenCL LBM. It voxelises STL meshes on the GPU and renders in VRAM: flag surface, velocity, streamlines, velocity-coloured Q-criterion isosurfaces, and raytraced free surfaces. — [GitHub FluidX3D](https://github.com/ProjectPhysX/FluidX3D)
  - The built-in "Mercedes F1 W14 car" setup has: a box with aspect 1:2:0.5 at 4000 MB VRAM; 100 km/h inflow; 0.25 s simulated; extensions FP16S, EQUILIBRIUM_BOUNDARIES, MOVING_BOUNDARIES and SUBGRID; rotating wheels through moving boundaries; a solid floor (z=0) with the flow initialised at inflow speed; and `VIS_FLAG_SURFACE|VIS_Q_CRITERION`, rendered from four cameras including an orbit. — [FluidX3D setup.cpp](https://github.com/ProjectPhysX/FluidX3D/blob/master/src/setup.cpp)
  - Ferrari SF71H (2018) video: a 2152×4304×1076 grid (about 10 billion cells) and 217k time steps. The simulation plus rendering of three 20 s 4K60 videos took 14 hours. Re = 3.75 million, Smagorinsky-Lilly subgrid model, velocity-coloured Q-criterion isosurfaces built with marching cubes. Source: a forum re-post of the video description; **the original YouTube page was not verified**. — [sg.hu forum](https://sg.hu/forum/uzenet/962870403/180824)
  - **Licence**: "Commercial use is not allowed." This includes providing a product or service "for a fee or other consideration" that derives value from the software. Military use is prohibited. If you publish results from an *altered* version, its source must be made public. Scientific publications must cite the listed papers. The licence does not explicitly cover monetised videos made with the unmodified code; that is ambiguous and needs an answer from the author. — [FluidX3D LICENSE.md](https://github.com/ProjectPhysX/FluidX3D/blob/master/LICENSE.md)
- **F1 / FIA with AWS (2019)**: CFD of one car in another car's wake for the 2021/22 rules. Over 1,150 cores, "550 million data points" (the release does not say cells), run time cut from 60 h to 18 h, six months of work on EC2 c5n. — [Amazon press release](https://press.aboutamazon.com/2019/12/formula-1-works-with-aws-to-develop-next-generation-race-car); [About Amazon](https://aboutamazon.com/news/aws/formula-1-uses-aws-to-develop-next-generation-race-car). Validated later in the wind tunnel. — [Formula1.com wind tunnel](https://www.formula1.com/en/latest/article/first-look-formula-1s-2021-car-in-the-wind-tunnel.6ye3S7Pb8NRX1K7PjTBxtS.html)
- **AirShaper / Voyager-AirShaper F1 challenge**: public, crowd-iterated aero updates on a non-regulation styling model. The team corrected its own downforce gain from 64% to 44%. — [Race Engine Technology](https://www.raceenginetechnology.com/News/improving-f1-aerodynamics-using-airshaper-cfd-simulations-the-voyager-airshaper-f1-challenge). A Buchan Motorsport video compared 2026 concepts using AirShaper results (LinkedIn, unverified). — [LinkedIn](https://se.linkedin.com/in/emil-qvist)
- **Helmut Schmidt University (HSU) Hamburg**: "Lattice Boltzmann Racecar Airflow Simulation on HSUper", an LBM racecar run on an HPC cluster. Details were not fetched. — [HSU HPC](https://www.hsu-hh.de/hpc/?p=299)
- **Dassault Systèmes (PowerFLOW LBM)** paper on unsteady and dynamic vehicle simulations, i.e. moving-attitude LBM. Not read in detail. — [3ds.com PDF](https://www.3ds.com/assets/invest/2024-02/unsteady_and_dynamic_vehicle_simulations_using_a_lattice-boltzmann_method_01.pdf)
- **Attitude effects through corners (aero-map approach)**:
  - A Formula Student CFD study (IST Lisbon) varied front and rear ride height, roll, steer and yaw. Yaw had the largest effect, about 16% on downforce. More than 100 CFD points fed a surrogate aero map. — [ulisboa dissertation](https://fenix.tecnico.ulisboa.pt/departamentos/dem/dissertacao/565303595503481); [Carreira extended abstract](https://fenix.tecnico.ulisboa.pt/downloadFile/845043405586592/MiguelCarreira_ExtendedAbstract.pdf)
  - Monash Motorsport automated Ansys CFD aero maps (ride height, yaw, steer, roll). — [LEAP Australia](https://www.leapaust.com.au/blog/?p=4917)
  - Michelin ran 2,000 lap simulations with gradient and wind at Spa. — [Michelin Canopy](https://simulation.michelin.com/canopy/technical-articles/wind-and-gradient-at-the-belgium-gp)
  - An active-aero review notes that yaw and cornering cause large flow changes that need higher-fidelity unsteady simulation. — [core.ac.uk](https://core.ac.uk/outputs/673178651)
  - An F1Technical thread cites a team study that held ride height constant and so struggled to match track data. — [F1Technical](https://f1technical.net/forum/viewtopic.php?p=107492)

### Inferences
- A practical laptop pipeline mirrors the industry aero-map method. Run a small set of steady LBM cases (speed bins × Corner/Straight mode × a few ride-height, yaw and roll points), then play them back along the lap from telemetry. Time-resolved CFD of a full lap on one laptop is far beyond the scale of the 14-hour, 10-billion-cell Ferrari run.
- FluidX3D's ready-made F1 setup is the fastest way to a prototype. Before monetising, either get written permission from the author or use an open-licence LBM code instead (not researched here).

### Gaps
- I did not verify claims about F1 TV / AWS "F1 Insights" aero graphics, Chain Bear, ex-aerodynamicist YouTube channels, Luminary Cloud F1 demos, Ansys or SimScale showcases, or Racecar Engineering features. Searches returned nothing usable within the tool budget.
- I found no published simulation of an F1 car's changing attitude and speed over a whole lap.
- I found no open-source project that couples lap telemetry with aero visualisation; the search turned up none.
