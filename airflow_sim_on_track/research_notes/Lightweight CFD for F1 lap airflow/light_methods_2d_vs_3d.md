# Lightweight (non-LBM) airflow methods and 2D vs 3D for a top-down F1 lap airflow visualisation

Scope: cheaper alternatives to full OpenFOAM runs for one laptop (RTX 4060 Laptop 8 GB, i9-13950HX, 32 GB RAM); whether a 2D plan-view slice means anything physically; quasi-steady treatment over a lap; Reynolds scaling. Research budget was about 17 tool calls, so several items remain gaps (listed below).

## 1. Panel / vortex-lattice / vortex-particle methods (OpenVSP+VSPAERO, AVL, FLOWUnsteady, DUST, others)

### Takeaway
These tools are built for thin lifting surfaces with attached flow, plus wakes shed from trailing edges. Some can model a ground plane: AVL uses a mirror image, VSPAERO gained a ground-effect model in v4.1.1, and DUST and FLOWUnsteady are not documented as supporting one. None of them predicts the massively separated bluff-body wake of an F1 car (wheels, sidepods, rear end). They could draw plausible wing-tip and front-wing vortex trails for the wings only. They would not give a credible whole-car wake.

### Cited Findings
- **AVL ground plane:** AVL simulates ground effect with a mirror image: "Ground effect is simulated with iZsym = 1, and Zsym = location of ground". With iZsym = 1 the X-Y plane acts as a solid wall. A ground plane can also be modelled as a SURFACE with NOALBE/NOLOAD, and forces are not computed on image surfaces — [AVL documentation (Drela, MIT)](https://web.mit.edu/drela/Public/web/avl/avl_doc.txt)
- **AVL assumptions:** AVL suits "configurations which consist mainly of thin lifting surfaces" at "a reasonably small angle to the X axis". Its linearization "is not completely valid when velocity perturbations from the free-stream become large". Trailing legs are "assumed to be parallel to the x-axis", so the wake does not roll up. Being quasi-steady, it neglects "unsteady vorticity shedding". Bodies are slender-body source/doublet lines with a round cross-section, "experience with this model is relatively limited", and bodies should be "done with caution" — [AVL documentation](https://web.mit.edu/drela/Public/web/avl/avl_doc.txt)
- **AVL in ground effect, validated for aircraft only:** a WSEAS 2024 paper validated AVL vortex-lattice results in ground effect for a ground-effect aircraft wing (A-90 Ekranoplan). It does not cover race cars — [Cranfield repository](https://dspace.lib.cranfield.ac.uk/handle/1826/20872)
- **VSPAERO ground effect:** VSPAERO 4.1.1 "Added ground effect model", and VSPAERO 4.2 later fixed bugs in "ground effect, wakes and CG location" — [OpenVSP blog](https://openvsp.org/blogs/?p=559); [OpenVSP 3.13.3 release](https://openvsp.org/blogs/announcements/2017/09/16/openvsp-3-13-3-released)
- **VSPAERO v7:** OpenVSP v3.45 brought major solver changes with VSPAERO version 7, and NASA says tutorials for the latest version will be unavailable in the near term — [NASA NTRS VSPAERO guide](https://ntrs.nasa.gov/api/citations/20190027157/downloads/20190027157.pdf). (Uncertain: I did not find the exact name of the current v7 ground-height parameter. A thread titled "Ground Distance and angle of attack definition on Ground effect analysis" exists on the [OpenVSP Google Group](https://groups.google.com/g/openvsp), but only its title was seen.)
- **FLOWUnsteady (BYU, Julia, MIT licence):**
  - Built on the reformulated vortex particle method (rVPM), a meshless LES-filtered Navier-Stokes solver for the wake, with VLM, lifting-line and actuator-line/surface models for wings and rotors.
  - Bluff bodies via a vortex sheet method are listed as "coming soon".
  - Viscous drag and separation enter only through airfoil lookup tables, and "separation wakes are not shed".
  - Incompressible only. OpenMP on a single node, no MPI, ExaFMM acceleration, and no GPU mentioned.
  - It runs on Linux, macOS and Windows via WSL, and claims rVPM is about 100x faster than comparable mesh-based LES.
  - The docs do not mention ground effect.
  - [FLOWUnsteady docs](https://flow.byu.edu/FLOWUnsteady/)
- **DUST (Politecnico di Milano / A³ by Airbus, MIT licence):** a mid-fidelity solver combining thick surface panels, thin vortex-lattice and lifting-line elements, with a vortex-particle wake. It targets eVTOL and rotorcraft interactional aerodynamics, and release 0.7.2 added a non-linear VLM element — [PoliMi DUST project](https://www.aero.polimi.it/en/research-projects/dust); [Tugnoli et al. 2021](https://re.public.polimi.it/bitstream/11311/1173647/3/TUGNM_OA_01-21.pdf); [DUST 0.7.2 release](https://www.aero.polimi.it/it/magazine/dust-software-major-release-0-7-2)
- **General limits of panel methods:** panel methods are efficient, but their inviscid assumptions limit them for "highly turbulent flow with separations". The usual workaround is to couple an integral boundary-layer method, which predicts separation, with a shear-layer wake model. One such 2-D example was demonstrated for a train near the ground — [Applied Sciences 2022, 12(19) 9652](https://www.mdpi.com/2076-3417/12/19/9652)
- **Open-wheel racing car panel/vortex model (Katz, SAE 860218):** an aerodynamic model of wing-generated downforce on open-wheel racing cars modelled the body and wheel wakes, but "separation line locations were assumed to be known from experiments or observation and ... fixed throughout all computations" — [SAE 860218](https://saemobilus.sae.org/content/860218). (The search snippet does not make clear whether Katz authored it. The SAE record should be checked.)
- **Wake-model sensitivity:** in simple panel methods applied to separated flows, two wake models differed by about 5% in CL "with the reason unknown" — [Aeronautical Journal](https://resolve-he.cambridge.org/core/journals/aeronautical-journal/article/part-i-some-experiences-on-simple-panel-methods-applied-to-attached-and-separated-flows/ABC817E876F2085157A04AAD8032E9ED)
- **Discrete vortex methods on bluff bodies (2D):** discrete-vortex (vortex particle) methods have reproduced 2D bluff-body shedding (square and rectangular cylinders) in good agreement with experiment — [Glasgow thesis](https://theses.gla.ac.uk/3951). A moving ground has been modelled "by the absence of vorticity generation on it" — [ABCM ENCIT 2010](https://www.abcm.org.br/anais/encit/2010/PDF/ENC10-0112.pdf). A consistent treatment of viscous diffusion near the body is needed — [Cottet & Koumoutsakos, Vortex Methods (CUP)](https://www.cambridge.org/core/books/abs/vortex-methods/viscous-vortex-methods/2056BBC4D6C6A0AA8468219697514441)
- **Ground-effect physics (review):** the flow physics that lightweight methods would need to capture include:
  - wings and diffusers in ground effect have distinct force regimes: downforce enhancement, maximum downforce, and downforce reduction;
  - edge vortices play a key role in force enhancement;
  - wheel aerodynamics is significant.
  - [Zhang, Toet & Zerihan, "Ground effect aerodynamics of race cars", Applied Mechanics Reviews 59(1) 2006, DOI 10.1115/1.2110263](https://eprints.soton.ac.uk/42969)

### Inferences
- A VLM model (AVL or VSPAERO) of the front wing, rear wing and floor-as-lifting-surface over an image ground plane would run in seconds and could plot trailing-vortex lines. AVL's wake does not roll up and its trailing legs lie along x, so its "trails" would be straight lines, not realistic vortex paths. A free-wake or VPM code (FLOWUnsteady, DUST) would give rolled-up tip-vortex trails.
- Because FLOWUnsteady and DUST do not shed separation wakes from bluff bodies, the wheel wakes, which dominate the F1 wake and the dirty-air deficit (section 3), would be missing or would need ad hoc models. That conflicts with the "real simulation" requirement.
- Downforce from the underfloor and diffuser comes from a strongly viscous, vortex-dominated flow (Zhang et al.). A potential-flow model of the floor would be qualitative at best.

### Gaps
- No published laptop runtimes were found for VSPAERO, DUST or FLOWUnsteady on a car-like geometry.
- No validation of any of these codes on a full race car in ground effect was found.
- APAME was not researched (search budget).
- Whether the VSPAERO v7 ground model supports a moving ground or only an image plane is unconfirmed.

## 2. Lightweight classical CFD (coarse OpenFOAM/simpleFoam, SU2 and others): minimum credible setup

### Takeaway
The best published coarse-mesh number found is DrivAerNet++: a roughly 6M-cell mesh gave about 8.2% drag error, and about 24M cells gave about 2.2%. A coarse steady RANS of a road-car-sized body is therefore credible to within roughly 10% on integrated forces. Wall-clock figures for a laptop were not found. Steady RANS also does not resolve the unsteady separated wake. It gives a time-averaged field, which suits mean-flow streamlines and total-pressure slices.

### Cited Findings
- **DrivAerNet++ mesh study (fastback DrivAer):** coarse mesh about 6M cells, fine mesh about 24M cells. "The relative error in drag coefficient decreases from 8.21% to 2.17%", and "the computational time increases significantly with finer meshes" — [DrivAerNet++, arXiv 2406.09624](https://arxiv.org/pdf/2406.09624). (The PDF was too large to fetch, so core counts and timings were not extracted.)
- **Coarse meshes under-predict drag:** a DrivAer fastback study found all meshes under-predicted CD against experiment, with a coarsest mesh of 19M cells — [Semarak Ilmu journal](https://semarakilmu.com.my/journals/index.php/fluid_mechanics_thermal_sciences/article/download/2808/1555/14665)
- **Mesh type and density matter:** a study of OpenFOAM on DrivAer with ANSA-built meshes (hybrid penta/tetra, hexa-dominant, polyhedral) examined their effect on convergence and accuracy — [BETA CAE, Fotiadis](https://www.beta-cae.com/events/c6pdf/3B_2_Fotiadis.pdf)
- **simpleFoam scaling:** a 110M-cell case showed "almost linear speed-up ... from 64 to 1024 cores" — [OpenFOAM Workshop 13](https://dcwan.sjtu.edu.cn/OpenFOAM2018/wp-content/uploads/2018/06/OFW13-1-007.pdf). This is a large-mesh HPC result, not a laptop one.
- **Ahmed body coarse-to-fine validation (SimScale):**
  - At 60 m/s (Re about 4.29e6), simulated CD was 0.2915 against a reference of 0.2875 for the 25° slant, about 1.2% — [SimScale validation](https://www.simscale.com/docs/validation-cases/aerodynamics-flow-around-the-ahmed-body/).
  - Another SimScale page reports CD 0.304, a 1.94% error — [SimScale older validation](https://simscale.com/docs/content/validation/AhmedBody/AhmedBody.html).
  - The two pages disagree, so check which configuration each one uses.
- **F1 car in OpenFOAM:** Guerrero & Castilla (Energies, 2020) ran OpenFOAM CFD of a 2017-spec F1 car in free stream and in a wake. They report downforce-coefficient losses of about 23–62% in the wake — [DOAJ record](https://doaj.org/article/7a9564c4c00b4422afc77278fff11bbc); [UPC full text](https://upcommons.upc.edu/bitstreams/aef9425b-9bc7-4cdc-8719-71b759d4f25b/download). (The full text could not be fetched, so mesh size and runtime are unknown.)

### Inferences
- A 2–6M-cell steady RANS case (simpleFoam with k-omega SST, or SU2) is the smallest setup with a published error figure (about 8% CD at 6M on DrivAer). That is near what 32 GB RAM can hold: OpenFOAM needs very roughly 1–2 GB per million cells, which is an unsourced rule of thumb. Running one case per lap state is infeasible on a laptop. A small set of states plus interpolation (see section 4, aero maps) is the realistic pattern.
- An F1 car has far finer geometry (multi-element wings, bargeboards and floor edges, wheels) than DrivAer. A coarse mesh will smear the vortices that make the wake visual. This is an inference; no source quantifies it.

### Gaps
- No laptop wall-clock times were found for coarse DrivAer or Ahmed cases.
- SU2, Code_Saturne and Basilisk car examples were not researched (budget).
- Cloud and free options were not researched.

## 3. 2D vs 3D: is a top-down horizontal slice physically meaningful? What does an F1 wake look like?

### Takeaway
A 2D plan-view simulation is not physically meaningful for an F1 car. Downforce comes from vertical-plane pressure differences: wings, floor and diffuser in ground effect. The F1 wake is dominated by streamwise vortices and by upwash, which are 3D by nature. Even for a simple cylinder, 2D simulations of a turbulent wake are inaccurate. A meaningful top-down picture needs 3D data that are then projected. Examples are streamlines seen from above, or horizontal slices through a 3D solution at a chosen height. The standard engineering view is a cross-plane total-pressure slice behind the car.

### Cited Findings
- **2D fails on cylinder wakes:**
  - At Re = 1000, "the 2-D simulation gives inaccurate predictions". 3D runs agree with experiment once the spanwise length exceeds about twice the diameter — [Lei, Cheng & Kavanagh 2001, JCU](https://researchonline.jcu.edu.au/660/).
  - The wake becomes three-dimensional above Re of about 200 for a stationary cylinder — [arXiv 2411.06279](https://arxiv.org/pdf/2411.06279).
  - An F1 car runs at Re of order 10^7. That figure is an inference from length and speed, not sourced.
- **Ground-effect downforce depends on ride height and edge vortices:** downforce enhancement, maximum and reduction regimes depend on ground clearance, and edge vortices drive force enhancement — [Zhang, Toet & Zerihan 2006](https://eprints.soton.ac.uk/42969). Ride height is a vertical coordinate, so a horizontal 2D slice cannot represent it (inference from the cited physics).
- **What dominates dirty air:**
  - Newbon, Sims-Williams & Dominy (Durham, 2017) found the dynamic pressure deficit in the wake has the greatest effect on the following car's downforce.
  - Upwash and vortices matter less directly, but they redirect the deficit up and over the following car.
  - The authors suggest reducing wheel and underbody wakes, or using rear-wing upwash.
  - [Durham repository](https://durham-repository.worktribe.com/output/1374025/aerodynamic-analysis-of-grand-prix-cars-operating-in-wake-flows)
- **Rule changes and wake cleanliness:** the 2009 rules produced a cleaner wake but did not reliably reduce the following car's downforce loss — [Durham repository](https://durham-repository.worktribe.com/output/1374025/aerodynamic-analysis-of-grand-prix-cars-operating-in-wake-flows)
- **Size of the wake effect:** 2017-spec F1 car downforce losses in a wake were 23–62% (OpenFOAM) — [Guerrero & Castilla, Energies 2020](https://doaj.org/article/7a9564c4c00b4422afc77278fff11bbc)
- **Y250 vortex:** it is generated at the junction of the FIA-mandated neutral central 500 mm of the front wing. Teams manage it with extra vortices from the wing elements, and front-wheel wake is directed with further devices — [F1Technical forum](https://www.f1technical.net/forum/viewtopic.php?p=696768). This is a secondary forum source of low reliability.
- **Y250 research basis:**
  - Imperial College (Sherwin lab) lists a project on generating a Y250 vortex on a cut-down F1 model — [Sherwin lab projects](https://sherwinlab.ae.ic.ac.uk/projects/).
  - The Imperial Front Wing, derived from the McLaren 17D, has PIV and total-pressure data in Pegrum's PhD thesis — [ExaFLOW use cases](https://webarchiv.hlrs.de/sites/exaflow/index.php/use-cases/mclaren-front-wing.html).
  - High-order Nektar++ simulations of the Imperial Front Wing with a rotating wheel (Re = 2.2e5) were compared with PIV — [Khurana, Liosi, Sherwin et al., arXiv 2503.03035](https://arxiv.org/pdf/2503.03035).
  - At least fourth-order resolution is needed to capture the downstream vortical structures — [Nektar++ news](https://www.nektar.info/formula-one-front-wing-simulation-with-nektar/).
  - A wing-only LES of the IFW in ground effect gave CL = −8.33 and CD = 0.17 — [Slaughter, Moxey & Sherwin, Flow Turb. Combust. 2023](https://link.springer.com/article/10.1007/s10494-023-00404-7).
- **Total-pressure slices are the analysis currency:** a PhD researcher argues that the wake's key effect is the dynamic-pressure deficit, which makes total-pressure slices the relevant view — [F1Technical "aerodynamics of dirty air" thread](https://www.f1technical.net/forum/viewtopic.php?p=738361). This is a secondary, forum source. The thesis title cited there is "Aerodynamic Effects of the Salient Flow Features in Grand Prix Car Wakes" (no link found).

### Inferences
- **2.5D or quasi-3D options that stay honest:**
  - Compute or precompute a 3D steady field per state, then render it top-down (see section 4).
  - Seed 3D streamlines and particle tracers and view them from above.
  - Take horizontal slices of velocity or total pressure at several heights, for example floor height and rear-wing height.
  - Colour the top-down trails by a 3D quantity, such as total-pressure loss or vorticity magnitude.
  - A pure 2D Navier-Stokes plan-view solve would show von Kármán-like shedding behind a car silhouette. That is a different physical problem: an infinitely tall extruded body with no ground, no wings and no downforce.
- **Downforce through corners:** this has to come from a 3D source, such as a CFD aero map or the existing lap-sim CL model. It can then be overlaid on the top-down view as a number or colour; it cannot come from a 2D plan-view flow.

### Gaps
- No textbook quote was retrieved that directly says "2D plan-view car CFD is invalid". The conclusion rests on the cylinder 2D/3D literature plus ground-effect physics, and is partly inference.
- No peer-reviewed figure set of Y250 or rear-wing tip-vortex paths seen from above for a full modern F1 car was found. Katz's "Race Car Aerodynamics" was not accessed.

## 4. Quasi-steady assumption and cornering-simulation methods (yaw, curved flow, roll, steer, aero maps)

### Takeaway
Treating the lap as a sequence of steady states is standard industry practice: aero maps over ride height, pitch, roll, yaw and steer, built from CFD or wind-tunnel data. It is supported by a reduced-frequency threshold: transient-yaw work found quasi-steady behaviour holds below k ≈ 0.3. It breaks down for fast ride-height oscillations such as porpoising and kerb strikes. Cornering is modelled either by a yawed straight domain (simple, robust) or by a curved, rotating-reference-frame domain (more faithful).

### Cited Findings
- **Quasi-steady threshold:** in transient-yaw simulations, flow can be treated as quasi-steady for reduced frequency below 0.3. The largest dynamic changes occur for k of about 0.3–1.5, and the dynamic effects were largely independent of Reynolds number — [Mankowski et al., Durham](https://dro.dur.ac.uk/14888)
- **F1 underbody in heave:** for a 2022-style F1 underbody in pure heave, reduced frequencies of about 0.754–1.508 "significantly amplified" aerodynamic forces relative to the quasi-static assumption — [Pellizzari thesis, Padova](https://thesis.unipd.it/retrieve/166116a6-bd07-45b8-9cbe-8a080d8a9486/Pellizzari_Luca.pdf)
- **Inverted wing in ground effect (porpoising):** a quasi-steady model using static aero data predicted static deflection but missed changes in modal frequency and damping. Unsteady (flutter-derivative) terms are needed to predict instability onset — [Ucci thesis, Liège](https://matheo.uliege.be/handle/2268.2/26151)
- **Transient vs static coefficients:** for a race vehicle, transient coefficients differ noticeably from static ones, especially drag, lift and pitch moment — [UNC Charlotte](https://ninercommons.charlotte.edu/record/1416)
- **Cornering by curved flow:**
  - **IST Lisbon (Formula Student):** imposes an angular velocity on the air, in a partial hollow-cylinder domain, using STAR-CCM+ — [Carreira extended abstract](https://fenix.tecnico.ulisboa.pt/downloadFile/845043405586592/MiguelCarreira_ExtendedAbstract.pdf).
  - **CTU Prague:** uses a curved freestream plus a rotating ground plane — [CTU thesis](https://dspace.cvut.cz/handle/10467/125275?show=full).
  - **Chalmers (DrivAer):** uses a moving reference frame over 100–800 m radii. Drag rises at small radii, and left and right turns differ because of the asymmetric underbody — [Chalmers](https://research.chalmers.se/publication/503721/file/503721_Fulltext.pdf).
- **Cornering by yaw:**
  - A yawed inlet with a stationary car, moving ground and rotating wheels was described as simpler and more robust — [Ansys forum](https://innovationspace.ansys.com/forum/?p=454547) (informal source).
  - The alternative of a straight domain with roughly 5–20° yaw is also suggested — [SimScale forum](https://www.simscale.com/forum/t/cornering-flow-case-of-a-racecar-on-simscale/81560/2) (informal source).
  - Lin & Papadopoulos (2022) ran CFD at 7.5° yaw to represent cornering — [IJAE](https://doaj.org/article/d1fd828712be4f7bad4e89bc515a5b79).
  - CFD has been coupled to multibody dynamics with overset meshes plus an MRF for curved trajectories — [Energies 15(8) 2917](https://www.mdpi.com/1996-1073/15/8/2917).
- **Aero maps:**
  - **IST FST10e:** the map has 5 attitude parameters (front and rear ride height, roll, steer, yaw), more than 100 CFD points and a surrogate model. Yaw was the most impactful: a 16% downforce change across the interval. Ride height gave a 10% change in CD·A and 20% in −CL·A. Airspeed estimation on track was a large source of correlation uncertainty — [Carreira thesis](https://fenix.tecnico.ulisboa.pt/downloadFile/845043405586591/MiguelCarreira_Thesis.pdf).
  - **Dallara:** automated CFD ride-height maps let the team analyse the car "during the entire lap, from straight lines to cornering", including pitch sensitivity under braking — [BETA CAE, Dallara](https://www.beta-cae.com/events/c6pdf/7B_1_Dallara.pdf).
  - **Monash Motorsport:** automated Ansys runs build a comprehensive map because attitude changes with load transfer — [LEAP Australia](https://www.leapaust.com.au/blog/?p=4917).
  - **Polimi (Formula 4):** wind-tunnel setpoints are weighted by how likely each state is around a lap — [Polimi thesis](https://www.politesi.polimi.it/handle/10589/234015).

### Inferences
- **Reduced frequency for corner transitions:** k = πfL/U (definitions vary by a factor; unsourced here). Take L ≈ 5.6 m, U ≈ 30–90 m/s, and a corner transition of about 0.5–2 s (f ≈ 0.25–1 Hz). That gives k of roughly 0.01–0.3, below or at the 0.3 threshold. A quasi-steady sequence of states is therefore defensible for corner-to-corner changes.
- **Where quasi-steady fails:** kerb strikes and bouncing at several Hz would exceed the threshold, and the Pellizzari and Ucci results show quasi-steady is wrong there. These numbers are my calculation, not sourced.
- **Practical pipeline:** precompute a small 3D aero map (yaw × ride height × roll, a handful of states) with coarse RANS overnight. Each frame then interpolates or blends the precomputed fields and scales them by speed (section 5). Only the map, not a per-frame solve, runs on the laptop each weekend. This is an inference.

### Gaps
- No F1-specific published reduced-frequency threshold for pitch and roll transients over a lap was found.
- Commercial F1 team methods (for example, how teams build curved-flow aero maps) are not public.

## 5. Reynolds-number scaling: are coefficients and flow topology roughly speed-independent?

### Takeaway
For sharp-edged bluff bodies, drag coefficients become Reynolds-independent above a threshold. Ahmed-body experiments are deliberately run in that regime, and dynamic yaw effects were also found largely Re-independent. F1 testing is done at reduced scale and speed (60%, 50 m/s), which relies on the same idea. Under that assumption, a steady velocity field at one speed can be scaled linearly with speed: u(x) ≈ U·f(x). That is an approximation; the method rests on it but no source here proves it for an F1 car. Low-Re components, such as transitional flow on wing elements, are the exception.

### Cited Findings
- **Ahmed body:** results on a square-back Ahmed body were "obtained when the Reynolds number independency of the drag coefficient was reached" — [Lahaye, Leroy & Kourta 2014, HAL](https://hal.archives-ouvertes.fr/hal-00918917)
- **Ahmed body reference experiments** run at 60 m/s, with Re_L about 4.29e6 — [SimScale validation](https://www.simscale.com/docs/validation-cases/aerodynamics-flow-around-the-ahmed-body/)
- **Ahmed body wake topology is set by geometry:** above a critical slant angle the wake becomes fully separated because the C-pillar vortex fails to form, and the vortex drag that disappears is up to 33% of total drag — [Johnson PhD thesis, Monash 2005](https://eng-web77-v02.ocio.monash.edu/intranet/johnson_thesis_phd_2005.pdf)
- **Transient yaw:** dynamic effects were "largely independent of Reynolds number" — [Mankowski et al.](https://dro.dur.ac.uk/14888)
- **F1 testing limits:** wind-tunnel testing is limited to models no larger than 60% scale and speeds no higher than 50 m/s, at atmospheric pressure — [F1Technical news (2008 limits)](https://f1technical.net/news/7788); [F1Technical wind tunnel feature](https://www.f1technical.net/features/21646). (Uncertain: I did not verify these against the current FIA regulations text. A later quoted version adds a wind-speed rate limit of <4.5 m/s².)
- **Counterpoint, Re-sensitive parts:** IFW research runs at Re = 2.2e5 because element-level transition matters there, and the authors analyse transition mechanisms per element — [Slaughter, Moxey & Sherwin 2023](https://link.springer.com/article/10.1007/s10494-023-00404-7). Wing elements in ground effect therefore carry some Re sensitivity, at least at model scale.

### Inferences
- Over the speed range of a lap (about 80–340 km/h), Re changes by roughly a factor of 4. For the bluff, sharp-edged parts of the car the topology should be roughly constant. Using one precomputed field per attitude state, scaled by speed, is a reasonable approximation. Force scaling as ½ρU²·CL·A follows directly.
- This is not sourced for a full F1 car. No published Re sweep of a full-scale F1 car was found.

### Gaps
- No direct source gives a Re-independence threshold for open-wheel cars or rotating wheels.
- Wind-tunnel-to-track correlation literature was not found within budget.
- Katz "Race Car Aerodynamics" was not accessed. It likely covers these topics, but this could not be verified.
