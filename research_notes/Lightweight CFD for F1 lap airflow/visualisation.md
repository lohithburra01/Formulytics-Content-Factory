# Visualising CFD airflow as top-down, car-locked trail videos (tools, techniques, performance)

Scope: open tools and techniques for turning CFD velocity fields into clear, fast-to-render airflow trail visuals. The camera is top-down and locked on an F1 car, the track moves underneath, and the target machine is an RTX 4060 Laptop (8 GB), i9-13950HX, 32 GB RAM, Windows 11. Researched 2026-10-26. About 20 tool calls; some pages were truncated or unreachable, and those points are listed under Gaps.

## Which line type is physically correct for a "smoke trail" in a car-fixed frame?

### Takeaway
Smoke or dye released at a fixed point traces a **streakline**. In a frame where the flow is steady, streamlines, pathlines and streaklines are the same curves. In a car-fixed frame with a steady (RANS-type) solution per corner, plain streamlines are therefore physically equivalent to smoke trails. If the field is unsteady (transient wake shedding, or a field that changes along the lap), use streaklines: particles continuously emitted from fixed seed points and advected with the time-varying field.

### Cited Findings
- Streamline: a curve tangent to the velocity field at one instant. Streamlines at the same instant do not intersect. — [Wikipedia: Streamlines, streaklines, and pathlines](https://en.wikipedia.org/wiki/Streamlines,_streaklines,_and_pathlines)
- Streakline: the locus of all fluid particles that have passed continuously through a particular spatial point. Dye injected steadily at a fixed point traces a streakline. — [Wikipedia](https://en.wikipedia.org/wiki/Streamlines,_streaklines,_and_pathlines)
- Pathline: the trajectory of an individual fluid particle over time. — [Wikipedia](https://en.wikipedia.org/wiki/Streamlines,_streaklines,_and_pathlines)
- In steady flow, streamlines, pathlines and streaklines coincide. Experimenters therefore use streaklines (smoke or dye) to show the streamline pattern of steady flows. — [Wikipedia](https://en.wikipedia.org/wiki/Streamlines,_streaklines,_and_pathlines)
- Streamlines depend on the reference frame. In the aircraft example, passengers see steady flow around the wing while a ground observer sees unsteady flow, so fluid dynamicists look for a frame in which the flow is steady. — [Wikipedia](https://en.wikipedia.org/wiki/Streamlines,_streaklines,_and_pathlines)
- Dye can be used to create **timelines**, which are lines of particles marked at the same instant and then advected. The fetched article mentions timelines but does not define them formally. — [Wikipedia](https://en.wikipedia.org/wiki/Streamlines,_streaklines,_and_pathlines). The Cambridge engineering page that also defines timelines ([Cambridge MDP](https://www-mdp.eng.cam.ac.uk/web/library/enginfo/aerothermal_dvd_only/aero/fprops/cvanalysis/node8.html)) refused the connection, so its text was not verified.

### Inferences
- The car-fixed frame is the frame in which car aero is normally solved: the car is stationary, and air and ground move at -V. For a steady solution at each lap sample (speed, yaw, ride height), animated "flowing" streamlines are physically honest smoke trails. Using the car-fixed frame matches the treadmill concept.
- When the field changes along the lap (speed or downforce changes through a corner), particles emitted at different times feel different fields. A true streakline then needs time-dependent advection that interpolates between lap-sample fields. Visually this shows the wake bending and lengthening, which is the "real" effect.
- The trail moves at flow speed in the car frame. The track texture under the car moves at -V_car. In the car frame, free-stream air and road move at the same velocity, so far-field particles should travel exactly with the track texture. This is a useful consistency check for the composite.

### Gaps
- No formal timeline definition was retrieved from a fetched page (the Cambridge page was unreachable).

## Tools: capabilities, licences, Windows support

### Takeaway
Best fits for a scripted Windows laptop pipeline: **ParaView/pvpython** (BSD-3, StreakLine/ParticleTracer filters, batch SaveAnimation) for physically correct traces, and **NVIDIA Warp** (Apache-2.0, NanoVDB volume sampling on CUDA) or **Taichi** (Apache-2.0) for very fast custom GPU particle advection. Render the result in the existing matplotlib/ffmpeg compositor or in Blender. **FluidX3D** has the most turnkey CFD-plus-render path (built-in streamline, Q-criterion and slice rendering, frame export) but is free for non-commercial use only. **Manim** StreamLines takes only an analytic Python callable and runs its whole integration at creation, so it suits explainer graphics rather than real CFD data. That last point is an inference from the API docs.

### Cited Findings
**ParaView / pvpython / pvbatch**
- ParaView is distributed under the OSI-approved BSD 3-clause licence. — [paraview.org/license](https://www.paraview.org/license/); conda-forge also lists BSD-3-Clause — [anaconda.org](https://anaconda.org/conda-forge/paraview)
- pvbatch accepts commands only from input scripts and runs in parallel when built with MPI. The tutorial shows `SaveAnimation(path, renderView, ImageResolution=[...], FrameWindow=[0, 43])`. — [ParaView docs: pvpython and pvbatch](https://docs.paraview.org/en/latest/Tutorials/ClassroomTutorials/pythonAndBatchPvpythonAndPvbatch.html)
- Pitfall: offscreen pvbatch without an explicit view size produced a bad .avi (reported against 5.4.1). Set `renderView.ViewSize`. — [ParaView GitLab #17914](https://gitlab.kitware.com/paraview/paraview/issues/17914)
- The StreakLine/particle trace filters compute traces from seed points in a vector field. They need point-centred vectors, output polylines, and expose `ComputeVorticity`, `DisableResetCache`, `ForceReinjectionEveryNSteps` and an `InterpolatorType` option (one faster, one more robust at cell location). — [paraview.simple.StreakLine (latest)](https://www.paraview.org/paraview-docs/latest/python/paraview.simple.StreakLine.html)
- `ForceReinjectionEveryNSteps` makes the seed source re-emit particles every Nth step, which keeps smoke continuous. It is redundant if the seed source is itself animated. Seeds can be a point cloud or a line. — [paraview.simple.StreakLine](https://www.paraview.org/paraview-docs/latest/python/paraview.simple.StreakLine.html)
- The ParticlePath, ParticleTracer and StreakLine entries had identical GUI help text in v5.10-RC1, which confused users. — [ParaView GitLab #21063](https://gitlab.kitware.com/paraview/paraview/-/issues/21063)
- ParaView 6.0 C++ docs list `vtkLegacyStreaklineFilter`, "A Parallel Particle tracer for unsteady vector fields". This suggests the old implementation was renamed legacy; I found no migration notes. — [vtkLegacyStreaklineFilter](https://www.paraview.org/paraview-docs/v6.0.0/cxx/classvtkLegacyStreaklineFilter.html)
- There is no built-in particle lifetime. Developers suggested applying a Threshold on particle age after the tracer (2014 thread). — [ParaView mailing list](https://public.kitware.com/pipermail/paraview/2014-January/030319.html)
- Users report that reinjection over long runs makes the video messier, and that streaklines crashed ParaView 5.8 when integration time equalled the final simulation time. — [ParaView Discourse](https://discourse.paraview.org/t/help-to-plot-the-streaklines-from-openfoam-simulation/6047); [CFD Online](https://cfd-online.com/Forums/paraview/224722-generating-streaklines.html)
- OpenFOAM wiki particle-tracer workflow: seed from point, line or plane sources, and use the Temporal Interpolator when sparse time steps make the animation choppy. — [OpenFOAM wiki](https://www.openfoamwiki.net/index.php/HowTo_use_particle_tracer_in_paraFoam)
- An animated "Stream Lines" representation (random seeding, particles respawn when they die) was proposed as a WIP merge request. Whether it ships in current ParaView builds was not verified. — [ParaView MR 1255](https://gitlab.kitware.com/paraview/paraview/-/merge_requests/1255); a Discourse thread asks how to reproduce the NVIDIA Omniverse streamline demo — [Discourse](https://discourse.paraview.org/t/how-to-create-streamlines-animation-as-the-nvidia-omniverse-demo-video/7899)

**NVIDIA IndeX (ParaView plugin)**
- Free for workstation or single-server-node use. The cluster edition is free for academics and licensed for commercial users. — [NVIDIA IndeX for ParaView](https://nvidia.com/en-us/data-center/index-paraview-plugin/); default licence covers a single GPU — [UiO user guide 5.8](https://mn.uio.no/astro/english/services/it/help/visualization/paraview/nvidia-index-paraview-plugin-user-guide-5.8.pdf); 5.12 licensing update — [Kitware blog](https://www.kitware.com/nvidia-index-plugin-for-paraview-5-12-feature-updates-and-new-licensing/)

**VTK / PyVista**
- `streamlines_from_source` uses the points of any source dataset as seeds, defaults to Runge-Kutta 45, and supports `surface_streamlines` to constrain integration to 2D cell surfaces. — [PyVista streamlines_from_source](https://docs.pyvista.org/api/core/_autosummary/pyvista.DataSetFilters.streamlines_from_source.html)
- `streamlines_evenly_spaced_2D` works only on datasets in the xy plane (z=0), and `separating_distance` must be chosen carefully to avoid excessive memory use. The example says the result is only approximately evenly spaced. — [PyVista evenly_spaced_2D](https://docs.pyvista.org/api/core/_autosummary/pyvista.datasetfilters.streamlines_evenly_spaced_2d); [2D streamlines example](https://docs.pyvista.org/examples/01-filter/streamlines_2d)

**matplotlib streamplot**
- `x` and `y` must be evenly spaced, strictly increasing arrays. Signature includes `density`, `start_points`, `maxlength=4.0`, `integration_direction='both'`, `broken_streamlines=True`, `integration_max_step_scale`, `num_arrows`. — [matplotlib.pyplot.streamplot](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.streamplot.html)
- Unverified (the fetched page was truncated before the parameter text): streamplot is 2D only, has no time parameter, and integrates in pure Python, so animating means re-running it every frame.

**Manim (Community)**
- `StreamLines(func, ...)`: `func` maps a position to a vector, and only callables are documented. Options: `x_range`, `y_range` and `z_range` (setting z enables 3D), `dt`, `virtual_time` (the full simulation runs at creation), `max_anchors_per_line`, `noise_factor`, `n_repeats`, `color_scheme`. `start_animation(warm_up, flow_speed, time_width=0.3)` gives a continuous flowing effect via `ShowPassingFlash`. Performance guidance in the docs is limited to "fewer anchors" and the upfront cost of `virtual_time`. — [Manim StreamLines](https://docs.manim.community/en/stable/reference/manim.mobject.vector_field.StreamLines.html)
- ManimGL, a separate API, has `StreamLines` and `AnimatedStreamLines`. — [ManimGL vector fields (Tessl mirror)](https://tessl.io/registry/tessl/pypi-manimgl/1.7.0/files/docs/vector-fields.md)
- The `ArrowVectorField` page itself was not fetched. It appears in the Manim reference sidebar next to StreamLines. — [Manim docs](https://docs.manim.community/en/stable/reference/manim.mobject.vector_field.StreamLines.html)

**Blender**
- Cycles motion blur can read velocity from imported VDB volumes. The velocity grid name is set per volume object, and split x/y/z grids are auto-detected. — [Blender search result summary, projects.blender.org archive](https://projects.blender.org/archive/blender-archive/src/commit/6d9268c2c7362ec772a3ff956ee888e877682a01/release)
- Geometry Nodes gained an experimental Sample Volume node that samples a volume grid at a position field (2023). — [commit 3195c1a669](https://projects.blender.org/archive/blender-archive/commit/3195c1a669); "Sample grid node" PR — [#118397](https://projects.blender.org/blender/blender/pulls/118397); Volume Grid sockets — [#115270](https://projects.blender.org/blender/blender/pulls/115270) (float and float3 grids only in the WIP branch — [#116021](https://projects.blender.org/blender/blender/pulls/116021))
- Blender 5.3 release notes list new quadratic and cubic modes for grid sampling, plus Deactivate Voxels and Grid Topology Boolean nodes. — [Blender 5.3 Geometry Nodes notes](https://developer.blender.org/docs/release_notes/5.3/geometry_nodes/)
- BVTKNodes, an experimental add-on, imports VTK/VTU data into Blender, including converting point data into a particle system with glyphs. — [BVTKNodes gallery](https://blenderartists.org/t/bvtknodes-gallery/1161079?page=3)
- Paid Blender add-ons generate "airflow trails" around meshes. These are artistic, not CFD-driven. — [Superhive: Aerodynamic Streamlines Simulator](https://superhivemarket.com/products/streamlines); [Gumroad Stream Lines](https://kennyphases.gumroad.com/l/dxzegy)

**NVIDIA Warp**
- Apache License 2.0 (Warp was previously under a proprietary NVIDIA licence). — [github.com/nvidia/warp](https://www.github.com/nvidia/warp); [heise report](https://heise.de/-10381872); old PyPI 1.1.0 metadata still shows the NVIDIA licence — [PyPI](https://pypi.org/project/warp-lang/1.1.0)
- `wp.volume_sample_f(id, uvw, sampling_mode)` samples a NanoVDB volume in local space with closest or linear sampling. There is also `volume_sample_grad_f`. — [Warp volume_sample_f](https://nvidia.github.io/warp/latest/language_reference/_generated/warp.volume_sample_f.html); [volume_sample_grad_f](https://nvidia.github.io/warp/latest/language_reference/_generated/warp.volume_sample_grad_f.html)
- Warp's NanoVDB example runs a particle kernel that samples a NanoVDB field per particle (SDF collision). The copy seen was a mirror. — [example_nvdb.py mirror](https://huggingface.co/spaces/qbhf2/GarmentCode/blob/main/NvidiaWarp-GarmentCode/examples/example_nvdb.py); Warp 1.16 adds in-place rebuild of fixed-capacity NanoVDB volumes — [Warp v1.16.0 release](https://github.com/NVIDIA/warp/discussions/1716)

**Taichi**
- Apache-2.0 licence. — [Taichi README mirror](https://gitee.com/rickqi/taichi) (mirror lists Python 3.6–3.10 and may be outdated)
- Official docs claim an MPM simulation of more than 400 million particles on a single GPU. That is not a real-time render figure. — [Taichi docs overview](https://docs.taichi-lang.org/docs/overview)
- GGUI renders triangle meshes and particles in real time. — [Medium tutorial](https://medium.com/parallel-programming-in-python/head-first-taichi-a-beginners-guide-to-high-performance-computing-in-python-be6afc5db93e)

**FluidX3D**
- "Free for non-commercial use". The full LICENSE.md was not read. — [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
- Built-in GPU (OpenCL) rendering directly from VRAM: velocity field, streamlines, and velocity-coloured Q-criterion isosurface, with slice modes for field and streamlines. Rasterised and raytraced free surfaces. — [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
- Frame export to PNG/QOI/BMP via `lbm.graphics.next_frame(...)`, spline camera flights (v2.19), an ASCII mode for headless or SSH use, and binary .vtk export of volumes and meshes in SI units. — [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
- Force and torque on objects (GPU summation since v3.2). Surface pressure visualisation works when the force field is enabled and `calculate_force_on_boundaries()` is called. Moving and rotating geometry is supported through velocity voxelization (aircraft examples: Cessna 172 and Bell 222 with moving parts). There is an Ahmed body force/drag example. — [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
- Runs on Windows and Linux on any OpenCL GPU, including Nvidia. — [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
- v3.7 (May 2026) optimised the Q-criterion isosurface render kernel. This comes from a secondary news source. — [foro3d](https://foro3d.com/de/2026/mayo/fluidx3d-37-optimiza-memoria-local-en-renderizado-de-isosuperficies.html)

### Inferences
- Simplest physically correct route: export per-lap-sample car-frame fields to VTK, run pvpython StreakLine with an upstream seed rake and reinjection, write polylines or particle positions per frame, and draw them in the existing matplotlib/ffmpeg compositor over the moving track. The alternative is to let ParaView render and composite later.
- Fastest route: put the fields on the GPU (Warp NanoVDB or a dense 3D array/texture) and advect about 10^5–10^6 particles per frame with RK2/RK4. Store a short history ring buffer per particle for streaks, then rasterise. All the pieces are Apache-2.0 or BSD and run on Windows with CUDA.
- FluidX3D's 8 GB budget: at about 55 bytes per cell, 8 GB holds roughly 140 M cells (the README claims about 19 M cells per GB). That covers a car-scale domain on one 4060 Laptop. Its built-in renderer can output streamline or Q-criterion frames directly, but the licence restricts commercial use.

### Gaps
- Omniverse licensing for individuals: no source was found.
- Manim `ArrowVectorField` docs were not fetched. Manim's handling of array or grid data (it needs an interpolating callable) is undocumented.
- The PyVista core streamlines doc page fetch returned only navigation, so pathline/time-varying support was not verified. VTK's temporal particle tracers (vtkParticleTracer and similar) were not directly sourced here.
- Whether Blender's Geometry Nodes "Sample Grid" can be used inside a Simulation Zone to advect points through an imported velocity VDB in a production-ready way. The parts exist (volume grid sockets, sample grid, simulation zones), but I found no tutorial or docs page confirming the end-to-end workflow.

## Techniques: seeding, LIC, Q-criterion, total-pressure slices, Cp, showing downforce

### Takeaway
Motorsport CFD standard visuals: **total-pressure-coefficient (CpT / Cp0) slices** to show wake and vortex energy, **surface Cp** contours for where downforce comes from (suction on wing undersides and underbody), **Q-criterion isosurfaces** coloured by velocity for vortices, and **LIC on slices** to show simulated oil flow. For top-down legibility, a horizontal slice near ride height with LIC or streaks, plus colour by speed or CpT, gives a dense 2D picture of 3D flow.

### Cited Findings
- An F1 spectral/hp study uses total pressure coefficient (Cp0) on x-normal slices to locate vortex cores and track their strength and path, and Cp0 = 0 isocontours coloured by Cp to show vortex breakdown. The main vortex is deflected by the wheel wake. — [arXiv 2503.03035](https://arxiv.org/pdf/2503.03035)
- F1 configuration: surface Cp shows high pressure at the nose and tyre faces and low pressure on wing suction sides and the underbody. These are paired with transverse wake planes coloured by velocity magnitude and Q-criterion isosurfaces. — [arXiv 2602.05563](https://arxiv.org/pdf/2602.05563)
- Willem Toet (former F1 head of aerodynamics) describes longitudinal sections of total pressure (CpT) to see where high-energy air remains for aero devices, and adding line integral convolution on those planes to show simulated oil flow. — [Racecar Engineering / RaceTech](https://www.racetechmag.com/?p=5484)
- Typical post-processing: slices with pressure on the body and streamlines or velocity on the slice. — [SimScale CFD post-processing guide](https://www.simscale.com/forum/t/cfd-post-processing-guide-for-simscale/39541/1)
- Line integral convolution (Cabral & Leedom, SIGGRAPH '93): filters a white-noise texture along streamlines of a vector field to produce a dense per-pixel image of the flow. — [SIGGRAPH History Archive](https://history.siggraph.org/?p=118617); [Auckland LIC page](https://www.cs.auckland.ac.nz/~burkhard/PhD/img10.html)
- Fast LIC (Stalling & Hege, 1995) reduces computation by about an order of magnitude and is resolution-independent. — [SIGGRAPH History Archive](https://history.siggraph.org/?p=118741)
- FluidX3D natively renders velocity-coloured Q-criterion isosurfaces and field or streamline slices, and can show surface pressure when forces are computed. — [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
- GPU particle systems for flow visualisation (Krüger et al., IEEE TVCG 2005) keep particle positions in GPU memory and render without CPU readback. They advect and render millions of particles interactively for steady 3D flow on uniform grids. — [TUM tvcg05.pdf](https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Publications/2005/A_Particle_System/tvcg05.pdf); [TUM Virtual Wind Tunnel project](https://www.cs.cit.tum.de/cg/research/projects/projects/the-virtual-windtunnel/)

### Inferences
- Showing downforce in top view: tint the car body or underfloor footprint by surface Cp (blue suction under floor and wings), and add a vertical-force bar or arrow scaled to the integrated Fz. Integrated Fz is what FluidX3D's force functions or a ParaView IntegrateVariables pass would give. In corners the suction region and the wake (CpT deficit) visibly change.
- Seeding for clarity: an upstream rake (a line or plane of seeds across the car width at a few heights, e.g. front-wing, mid and rear-wing height), coloured by seed height or by local speed. A rake at floor height and one at rear-wing height make the two main wakes (diffuser/floor and rear-wing upwash/tip vortices) separable from above. This seeding practice is an inference, not directly sourced.
- Depth cues for projected 3D lines from above: colour or opacity by height (z), thinner and fainter lines for lower particles, and halos or dark outlines to separate overlapping lines. Halos as a depth cue were not directly sourced here (see Gaps).

### Gaps
- No IEEE VIS source was retrieved for depth cues, halos or illuminated streamlines in 3D-from-top projection.
- No public F1 team footage or repo of animated car-frame streaklines was found with a reproducible pipeline.

## Performance: render times, GPU advection throughput, storage formats

### Takeaway
Hard throughput numbers for laptop GPU particle advection were not found from primary sources in this pass. The literature establishes that GPU advection keeps millions of particles interactive, and FluidX3D gives a solver-side reference: RTX 4090 at 11,496 MLUPs/s and about 55 bytes per cell. For storage, FluidX3D-style FP16 or NanoVDB-type sparse grids are the compact options. Thousands of frames are dominated by I/O and line rasterisation, not by advection. That last point is an inference.

### Cited Findings
- FluidX3D memory: about 55 bytes per cell (FP32 arithmetic, FP16 storage) versus about 344 bytes per cell for FP64 LBM, which is roughly 19 M cells per GB. RTX 4090 runs 11,496 MLUPs/s. — [FluidX3D GitHub](https://github.com/ProjectPhysX/FluidX3D)
- A GPU particle system achieves interactive streaming and rendering of millions of particles. An earlier GPU method from the same line of work ran at 41 fps against 0.5 fps on the CPU (a frame rate, not particles/s). — [Krüger et al. TVCG 2005](https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Publications/2005/A_Particle_System/tvcg05.pdf) (PDF text not extracted locally, figures from the search summary)
- Particle advection is embarrassingly parallel, with one GPU thread per particle. — [A Guide to Particle Advection Performance (arXiv 2201.08440)](https://arxiv.org/pdf/2201.08440)
- Large-scale study: Lagrangian flow maps with up to 67 M particle trajectories over 500 cycles on up to 2048 GPUs. — [EGPGV / search summary](https://diglib.eg.org/handle/10.2312/EGPGV.EGPGV13.001-008)
- VTK-m provides performance-portable particle advection. — [Performance-Portable Particle Advection with VTK-m (EGPGV 2018)](https://unpaywall.org/10.2312%2FPGV.20181094)
- Warp samples NanoVDB volumes on GPU via `volume_sample_f`. — [Warp docs](https://nvidia.github.io/warp/latest/language_reference/_generated/warp.volume_sample_f.html)

### Inferences
- Sizing: a 256×128×64 car-frame box is 2.1 M cells. A float16 velocity vec3 takes 6 B per cell, about 12.6 MB per lap sample, so 100 lap samples is about 1.3 GB. That fits on the 8 GB GPU for in-VRAM time interpolation, or in NPZ on disk. This is arithmetic, not a sourced benchmark.
- Advecting 10^6 particles with RK4 (4 trilinear samples each) is about 4×10^6 texture-like fetches per step. That is trivially small for a modern GPU, so expect advection well under a frame budget. Unverified: no RTX 4060 measurement found.
- ParaView StreakLine on CPU for thousands of frames will be slower than custom GPU advection but scriptable and correct. Its rendering via pvbatch SaveAnimation at fixed ViewSize is the bottleneck. No timing numbers found.

### Gaps
- No primary benchmark of particles/second for Warp, Taichi, ModernGL or Vispy on an RTX 4060-class laptop.
- No measured pvbatch render times per frame for streakline animations.
- VTK vs VDB vs NPZ compression comparisons for velocity fields were not found. The NanoVDB/OpenVDB float16 and compression options were not sourced in this pass.
