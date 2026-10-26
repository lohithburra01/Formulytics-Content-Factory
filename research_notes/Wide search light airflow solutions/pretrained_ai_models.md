# Pretrained AI / ML aerodynamics models usable now (car 3D flow fields / forces in seconds, 8 GB laptop GPU)

Research date: 2026-10-26. About 30 tool calls. Hugging Face hub was queried directly through its API (`/api/models?search=...`) for DrivAer, transolver, cfd, domino, physicsnemo, airfrans, meshgraph, GINO, AB-UPT, racecar and similar terms. Licensing is out of scope and is noted only in passing.

## Q1. Which models have open, downloadable pretrained weights that predict 3D car flow fields or forces?

### Takeaway
The biggest find: since 2026-05-01 NVIDIA hosts five free PhysicsNeMo checkpoints on Hugging Face, all trained on DrivAerML. They are DoMINO, Transolver, GeoTransolver, X-MeshGraphNet and FIGConvNet. DoMINO, Transolver and GeoTransolver predict both surface fields and the volume velocity/pressure field. Each file is only 50-120 MB (10-29 M parameters), which is small enough that 8 GB inference with point-chunking looks feasible. Emmi AI's AB-UPT also has a public DrivAerML tutorial checkpoint. Every one of these was trained on a road car (DrivAer notchback) at a single operating condition. None was trained on yaw, pitch, roll, ride-height sweeps or an open-wheel car.

### Cited Findings

**1. NVIDIA DoMINO DrivAerML (HF, open checkpoint)**
- Predicts surface pressure and wall shear stress, plus volume velocity, pressure and turbulent viscosity. Input is a point cloud from an STL with an SDF. 19.7 M parameters. Separate surface and volume checkpoints. Released 05/01/2026. Card lists test hardware as H100 and GB200, and the OS as Linux only. — [HF nvidia/domino_drivaerml](https://huggingface.co/nvidia/domino_drivaerml)
- File sizes from the HF API: volume `DoMINO.0.501.mdlus` is 48 MB and `checkpoint.0.501.pt` is 91 MB. — [HF API tree](https://huggingface.co/api/models/nvidia/domino_drivaerml)
- Trained on 436 DrivAerML cases (about 150 M volume cells and 10 M surface cells each) for up to 500 epochs on a GB200 node. — [HF card](https://huggingface.co/nvidia/domino_drivaerml)
- Code: [physicsnemo/examples/cfd/external_aerodynamics/domino](https://github.com/NVIDIA/physicsnemo/tree/main/examples/cfd/external_aerodynamics/domino). Paper: [arXiv 2501.13350](https://arxiv.org/abs/2501.13350)

**2. NVIDIA Transolver DrivAerML (HF, open checkpoint)**
- Physics-Attention transformer with 10 M parameters and 8 layers. Predicts surface p and WSS, plus volume velocity and p. Surface and volume checkpoints. — [HF nvidia/transolver_drivaerml](https://huggingface.co/nvidia/transolver_drivaerml)
- Inference timing is published in the PhysicsNeMo recipe. Full-resolution DrivAerML surface validation cases are chunked and stitched, taking about 1.8 s mean per car (0.7-8.1 s), with drag R² 0.990 and lift R² 0.982. The GPU for that table is not stated, but is probably datacenter-class. — [PhysicsNeMo transformer_models README](https://github.com/NVIDIA/physicsnemo/tree/main/examples/cfd/external_aerodynamics/transformer_models)
- The README says that "to enable the mesh to fit into GPU memory, the mesh is chunked into pieces", and that resolution can be lowered (for example to 51,200 points) "to fit in GPU memory". — [same README](https://github.com/NVIDIA/physicsnemo/tree/main/examples/cfd/external_aerodynamics/transformer_models)

**3. NVIDIA GeoTransolver DrivAerML (HF, open checkpoint)**
- 29 M parameters (20 GALE layers). Uses multi-scale ball-query geometry context and takes global boundary-condition / operating-regime parameters as input (`d_p`), which matters for future fine-tuning on speed or attitude. Predicts surface p and WSS, plus volume velocity and p. The volume checkpoint is 118 MB. — [HF nvidia/geotransolver_drivaerml](https://huggingface.co/nvidia/geotransolver_drivaerml); paper [arXiv 2512.20399](https://arxiv.org/abs/2512.20399)

**4. NVIDIA X-MeshGraphNet DrivAerML surface (HF, open checkpoint)**
- GNN with 12 M parameters. Builds its graph directly from the STL (kNN), handles large graphs by partitioning with halos, and is multi-scale. Surface p and WSS only. Test hardware A100. — [HF nvidia/xmgn_drivaerml_surface](https://huggingface.co/nvidia/xmgn_drivaerml_surface); paper [arXiv 2411.17164](https://arxiv.org/pdf/2411.17164)

**5. NVIDIA FIGConvNet DrivAerML surface (HF, open checkpoint)**
- 6.6 M parameters, U-Net with factorized implicit global convolutions. Typical input is 500k surface points. Outputs p and 3 WSS components. Test hardware A100. — [HF nvidia/figconvnet_drivaerml_surface](https://huggingface.co/nvidia/figconvnet_drivaerml_surface); paper [arXiv 2502.04317](https://arxiv.org/abs/2502.04317)

**6. NVIDIA DoMINO-Automotive-Aero NIM (NGC container, hosted/self-hosted)**
- Prebuilt inference microservice. The support matrix lists 40 GB GPU memory for the non-optimized config (FP32), with optimized configs on 40-96 GB cards. Docs say smaller GPUs can run it if the point cloud size is reduced at runtime. Minimum compute capability fell to 7.5 from v2.0.0. — [NIM support matrix 2.1.0](https://docs.nvidia.com/nim/physicsnemo/domino-automotive-aero/2.1.0/support-matrix.html)
- Timing: 3.6-4.2 s per request for a 500k-point cloud on H100, A100 or L40S (v1.0 and v2.0 docs). The "latest" docs give about 7-8 s for a 50k cloud, so the two doc versions conflict. — [perf 1.0.0](https://docs.nvidia.com/nim/physicsnemo/domino-automotive-aero/1.0.0/performance.html); [perf latest](https://docs.nvidia.com/nim/physicsnemo/domino-automotive-aero/latest/performance.html)
- A fine-tuning recipe on the NIM checkpoint (`domino-drivesim-recent.pt`, NGC key required) was validated with only 16 training and 8 test DrivAerML samples, with results labelled "preliminary". — [DoMINO NIM fine-tuning](https://docs.nvidia.com/physicsnemo/26.05/physicsnemo/examples/cfd/external_aerodynamics/domino_nim_finetuning/README.html)

**7. Emmi AI AB-UPT (HF tutorial checkpoint + GitHub)**
- `EmmiAI/AB-UPT` contains `ab-upt-drivaerml-tutorial.th` (created 2025-06-23), trained on DrivAerML. The card says input should be "similar to the ones from the DrivAerML dataset". — [HF EmmiAI/AB-UPT](https://huggingface.co/EmmiAI/AB-UPT)
- The tutorial repo runs inference in a Colab notebook and computes drag/lift and "streamline velocity visualizations", which implies volume velocity. No timing or memory is stated. — [GitHub Emmi-AI/AB-UPT](https://github.com/Emmi-AI/AB-UPT)
- The paper claims models "can be trained on a single GPU in less than a day" and "predict industry-standard surface and volume fields within seconds", and that inference can run "from a CAD geometry alone" with no meshing. — [arXiv 2502.09692](https://arxiv.org/abs/2502.09692)
- Emmi announced end-to-end inference on 9 M surface plus 140 M volume cells on a single GPU. — [Emmi news](https://www.emmi.ai/news/ab-upt-scaling-neural-surrogates-100m-cfd-meshes)
- The Noether framework provides recipes (AB-UPT, UPT, Transformer, Transolver) for ShapeNet-Car, AhmedML, DrivAerML, DrivAerNet++ and Emmi-Wing, with VTK export and UQ recipes. — [Noether recipe zoo](https://noether-docs.emmi.ai/noether/recipe_zoo.html); [GitHub recipes](https://github.com/Emmi-AI/noether/tree/main/recipes)
- Emmi AI was reportedly acquired by Mistral AI in May 2026. I did not verify this beyond the headline. — [Emmi news URL](https://www.emmi.ai/news/mistral-ai-acquires-emmi-ai)

**8. OneScience Transolver-Car-Design / MeshGraphNet mirrors (HF)**
- Model cards for a Transolver/Transolver++ car model trained on ShapeNet-Car. The search summary says the weights are "to be uploaded" and that users train their own `Transolver_plus.pth`. There is also an `OneScience-Group/MeshGraphNet` repo and an `OneScience-Group/CFD_Benchmark`. — [HF OneScience/Transolver-Car-Design](https://huggingface.co/OneScience/Transolver-Car-Design); HF search results (`OneScience-Group/MeshGraphNet`)

**9. PaddleScience DrivAerNet / DrivAerNet++ checkpoints (drag only)**
- Pretrained RegDGCNN drag model (`CdPrediction_DrivAerNet_r2_100epochs_5k_best_model.pdparams`, R² 88.2%) and RegPointNet on DrivAerNet++ (R² 91.9%). These are PaddlePaddle format and predict a scalar Cd only. — [PaddleScience DrivAerNet](https://paddlescience-docs.readthedocs.io/zh-cn/latest/en/examples/drivaernet/); [DrivAerNet++ example](https://paddlescience-docs.readthedocs.io/zh-cn/latest/en/examples/drivaernetplusplus/)
- The original DrivAerNet repo releases code, data and splits. — [GitHub DrivAerNet](https://github.com/mohamedelrefaie/drivaernet)

**10. Small community checkpoints found on HF (low maturity)**
- `BettyChiou25/geotransolver_drivAerML`, `xFetrax/airfRANS_VAE_256`, `xFetrax/10M_airfRANS_MLP_256`, `zacheryasc/airfrans-frontier-checkpoints` (AirfRANS is 2D airfoils), `harshaperla/fan-design-surrogate-physicsnemo`, `KC206/CCA_drone_Transolver`. All have 0-5 downloads and are not evaluated here. — HF API search, e.g. [huggingface.co/api/models?search=airfrans](https://huggingface.co/api/models?search=airfrans)

### Inferences
- The most practical drop-in today is `nvidia/transolver_drivaerml` or `nvidia/domino_drivaerml` (volume checkpoint), which gives a 3D velocity field around a car in a few seconds. With 10-20 M parameters the weights fit easily in 8 GB, and activations are controlled by chunking the query points (the README does this already). This is my inference: no source states 8 GB timing.
- The official PhysicsNeMo docs list Linux only. On Windows 11, WSL2 or Docker is the likely route. NVIDIA Warp ball queries used by DoMINO may need WSL. Not verified.
- Applied to an F1 car, these models are badly out-of-distribution: DrivAer is a closed-wheel road sedan at one condition. Usable for an F1 car only after fine-tuning on F1 CFD cases.

### Gaps
- No source gives inference memory or time on an 8 GB consumer GPU for any of these checkpoints.
- The GPU used for the Transolver 1.8 s/case table is unstated.
- I could not confirm whether the AB-UPT tutorial checkpoint includes volume outputs, or its size and memory needs. The Colab notebook would show this.

## Q2. Hosted platforms, services and demos (commercial or closed weights)

### Takeaway
Many vendors offer seconds-to-minutes aero prediction, but all are closed platforms trained on your own CFD. The only free public demos are aerospace (PhysicsX Ai.rplane) and NVIDIA's blueprint. Neural Concept and BeyondMath are the vendors with actual F1-team use.

### Cited Findings

**11. Luminary Cloud SHIFT models (open datasets; weights not public on HF)**
- The `luminary-shift` HF org shows "None public yet" for models. It hosts 15 datasets, including SUV, SUV-sample, WING, Truck, Crash, Pump, Battery and Submarine. — [HF luminary-shift](https://huggingface.co/luminary-shift)
- SHIFT-SUV was trained on more than 1,000 transient DES runs on morphed AeroSUV using PhysicsNeMo DoMINO. SHIFT-Truck uses more than 700 DDES runs with the Luminary-SMART architecture. SHIFT-Wing uses more than 3,000 RANS runs with DoMINO. Others are CCA, Missile, Submarine and Pump. The page says the models are "reference models built for exploration and benchmarking — not production-ready". — [luminary.ai/models](https://luminary.ai/models)
- The press calls SHIFT-SUV an "open-source foundation model", built with Honda and NVIDIA. HF shows only datasets, so the sources conflict on whether weights are downloadable. — [Luminary press release](https://www.luminarycloud.com/resources/luminary-cloud-unveils-first-physics-ai-open-source-automotive-foundation-model-for-suv-aerodynamics-in-collaboration-with-honda-and-nvidia); [engineering.com](https://engineering.com/luminary-cloud-releases-open-source-physics-ai-model-with-honda-nvidia/)

**12. NVIDIA Omniverse Blueprint: digital twins for fluid simulation (virtual wind tunnel)**
- A reference workflow combining CUDA-X solvers, PhysicsNeMo and Omniverse rendering for real-time external aero. Demonstrated at SC24 with Luminary Cloud, where the car could be changed interactively. — [GitHub blueprint](https://github.com/NVIDIA-Omniverse-blueprints/digital-twins-for-fluid-simulation); [build.nvidia.com card](https://build.nvidia.com/nvidia/digital-twins-for-fluid-simulation/blueprintcard); [NVIDIA blog](https://developer.nvidia.com/blog/rapidly-create-real-time-physics-digital-twins-with-nvidia-omniverse-blueprints)
- Runs on DGX Cloud and major clouds. Ansys used it with Fluent. — [etcentric](https://www.etcentric.org/?p=189080)

**13. PhysicsX LGM-Aero + Ai.rplane (free public demo, aerospace)**
- Large Geometry Model with about 100 M parameters, trained on more than 25 M meshes and tens of thousands of CFD/FEA runs. Ai.rplane is a free public demo that generates aircraft shapes and predicts aero in under a second. Can be fine-tuned with "a few tens of simulations" on the PhysicsX platform. — [PhysicsX launch](https://www.physicsx.ai/newsroom/introducing-lgm-aero-genai-for-aero-engineering-and-airplane-showcase-application-for-aerostructures); [automation.com](https://www.automation.com/article/siemens-physicsx-build-ai-deep-physics-simulation); [PhysicsX research post](https://www.physicsx.ai/newsroom/building-beyond-human-imagination-with-foundation-models-for-geometry-and-physics); [Siemens news](https://news.siemens.com/fr-fr/siemens-physicsx)

**14. Neural Concept (commercial; used by F1 teams)**
- Official supplier to the Racing Bulls (VCARB) F1 team since June 2025. Williams reportedly also uses it. One report claims that "up to 40%" of the grid use it, which is unverified. — [Neural Concept VCARB](https://www.neuralconcept.com/post/visa-cash-app-racing-bulls-vcarb-formula-one-tm-team-accelerates-racing-car-design-with-neural-concepts-engineering-ai); [TechCrunch 2024](https://techcrunch.com/2024/04/14/how-neural-concepts-aerodynamic-ai-is-shaping-formula-one); [techinformed](https://techinformed.com/formula-one-team-accelerates-car-design-with-ai-platform/)

**15. BeyondMath "digital wind tunnel" (commercial; F1 proof point)**
- Generative physics foundation model with F1 car simulation in "moments". Claims full 3D transient simulations at more than 200 M cells. These are company claims only. — [TechCrunch 2024](https://techcrunch.com/2024/08/20/beyond-maths-digital-wind-tunnel-puts-a-physics-based-ai-simulation-to-work-on-f1-cars); [SAE 2026-26-0372](https://saemobilus.sae.org/papers/use-digital-wind-tunnel-improved-aerodynamic-prediction-2026-26-0372)

**16. Ansys SimAI (commercial cloud)**
- Predicts the full 3D response of a new design "in minutes" and is 10-100x faster than the solver. The customer trains it on their own simulations. No yaw-specific information found. — [Ansys blog](https://www.ansys.com/en-gb/blog/accelerating-automotive-safety-through-ai-powered-design); [Synopsys/Sumitomo Riko PR](https://news.synopsys.com/2025-10-08-Sumitomo-Riko-Leverages-Ansys-AI-Technology-to-Accelerate-Simulation-Over-10x-for-Automotive-Component-Design-and-Manufacturing?asPDF=1)

**17. Siemens Simcenter PhysicsAI (STAR-CCM+ add-on, May 2026)**
- Geometric deep learning surrogates trained on your existing STAR-CCM+ results, with GPU predictions up to 100x faster than CPU. — [Siemens news](https://news.siemens.com/nl-nl/siemens-simcenter-physicsai/); [automation.com](https://www.automation.com/article/siemens-simcenter-physicsai-add-on-ai-powered-cfd-design-exploration)
- Altair (physicsAI) is now part of the Siemens ecosystem, according to the same release. — [Siemens news](https://news.siemens.com/nl-nl/siemens-simcenter-physicsai/)

**18. Altair physicsAI, Monolith AI, Navasto**
- My searches returned no primary pages for these three. Their specs are therefore not cited here (see Gaps).

### Inferences
- None of the hosted services suits "run every race weekend on one laptop": they need the cloud, enterprise licensing, or your own CFD training data. They would add nothing over fine-tuning the open NVIDIA checkpoints yourself.

### Gaps
- No primary source for Altair physicsAI, Monolith or Navasto specs in this pass (searches surfaced none).
- No public timing for Neural Concept, BeyondMath or SimAI per full-car prediction.

## Q3. Racing / open-wheel / attitude-varying (yaw, pitch, roll, ride height) ML aero work, and fine-tuning with few CFD cases

### Takeaway
The only public neural surrogate trained on a race car across attitude "map points" is IBM Research and Dallara's GIST (LMP2), which has no weights or data released. Every open checkpoint is single-condition road-car. For the user's use case, the realistic path is to fine-tune GeoTransolver or DoMINO, or train AB-UPT or Transolver from scratch, on a small set of their own F1 CFD cases spanning speed, yaw, pitch, roll and ride height. NVIDIA reports that DoMINO fine-tuning works with 16 cases (preliminary).

### Cited Findings
- **IBM Research + Dallara, "Faster by Design" (arXiv 2604.18491, 2026):** Uses the GIST graph neural operator on a parametric LMP2 race car with 625 samples, each with about 4.8 M points. Six map points per configuration combine heave, pitch, yaw, roll and steer for straight and cornering conditions. Mean errors are Cd 0.6% and Cl (downforce) 0.7%, against 1.2%/1.2% for Transolver. The underfloor runs "in ground effect". The authors say "no existing public automotive CFD dataset covers multiple operating conditions". A full sweep runs "in seconds on a single GPU". No code, data or weights are released. — [arXiv 2604.18491](https://arxiv.org/html/2604.18491); GIST method [arXiv 2603.16849](https://arxiv.org/abs/2603.16849)
- **F1 front-wing PINN (arXiv 2509.01963):** A single-author high-school paper using SimScale CFD data, reporting R² 0.968 for Cd and 0.981 for Cl. Treat as weak evidence. — [arXiv 2509.01963](https://arxiv.org/html/2509.01963v1)
- **CarBench (arXiv 2512.07847):** Benchmarks 11 models on about 8,150 DrivAerNet++ geometries. Transformer neural solvers score best, and errors concentrate at high-curvature and separation zones. — [arXiv 2512.07847](https://arxiv.org/pdf/2512.07847)
- **Emmi-Wing / transonic wing (arXiv 2511.21474):** About 30,000 3D-wing CFD samples with varying geometry and inflow. AB-UPT reproduces drag-lift Pareto fronts on unseen wings. The dataset is open, at [HF EmmiAI/Emmi-Wing](https://huggingface.co/datasets/EmmiAI/Emmi-Wing). — [arXiv 2511.21474](https://arxiv.org/abs/2511.21474)
- **GINO (NeurIPS 2023):** Results on Ahmed body (551 shapes, inlet velocity varied, 8.31% error) and ShapeNet-Car (7.12%), with a 26,000x speed-up for drag versus GPU CFD. No pretrained checkpoint was found. — [arXiv 2309.00583](https://arxiv.org/abs/2309.00583)
- **Ground effect in volume datasets:** DrivAerML cases contain about 150 M volume cells and are hybrid RANS/LES (HRLES) time-averaged runs. — [HF domino card](https://huggingface.co/nvidia/domino_drivaerml). Whether the boundary conditions include a moving ground or rotating wheels was not verified in this pass.
- **Conditioning input:** GeoTransolver explicitly concatenates "global boundary condition parameters" into its geometry context, so a speed, yaw or ride-height vector can be added when fine-tuning. — [HF geotransolver card](https://huggingface.co/nvidia/geotransolver_drivaerml)
- **Few-case fine-tuning:** The DoMINO NIM fine-tuning recipe used 16 training cases and is labelled preliminary. — [NVIDIA docs](https://docs.nvidia.com/physicsnemo/26.05/physicsnemo/examples/cfd/external_aerodynamics/domino_nim_finetuning/README.html). PhysicsX claims LGM-Aero can be fine-tuned with "a few tens" of simulations. — [automation.com](https://www.automation.com/article/siemens-physicsx-build-ai-deep-physics-simulation)

### Inferences
- Attitude can be handled two ways: (a) rotate and translate the car geometry relative to the ground and freestream, so that yaw, pitch, roll and ride height become geometry changes, which point-cloud models like DoMINO and Transolver accept natively; or (b) feed the condition vector into GeoTransolver. Either way, ground-relative attitude needs training CFD with a ground plane. A road-car checkpoint will not extrapolate to F1 diffuser and wing ground effect.
- Per-lap use: a lap needs perhaps 50-200 attitude/speed states, each taking a few seconds. Precompute once per weekend, interpolate between states, and render wake streamlines from the predicted volume velocity field.
- No open F1 or open-wheel CFD dataset or model exists, which matches the earlier search.

### Gaps
- Exact Dallara map-point values and GPU are not given. Whether the IBM/Dallara code will be released is unknown.
- I found no Formula Student public ML-aero model or dataset.
- No public F1-team technical talks (GTC etc.) with downloadable artifacts were found in this budget.
- DrivAerML boundary conditions (yaw, moving ground, wheel rotation) are not verified here.
- AirfRANS (2D airfoil RANS benchmark) is known to exist (HF community checkpoints above) but is 2D and was not researched further.
