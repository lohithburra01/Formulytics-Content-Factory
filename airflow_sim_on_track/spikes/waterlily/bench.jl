# THROWAWAY SPIKE: does WaterLily.jl run a car-sized bluff body over a moving ground on this laptop, and how fast?
# Body = Ahmed-proportion rounded box (1044 x 389 x 288 mm, 50 mm clearance), ground = plane moving at U (treadmill).
# Usage: julia --project=. bench.jl [n1 n2 ...]   (n = domain length in cells; domain n x n/2 x n/4)
using WaterLily, StaticArrays, CUDA, Printf

function car_sim(n; U=1f0, Re=1f5, T=Float32, mem=CuArray)
    L = n / 4f0                                   # body length in cells
    hx, hy, hz = 0.5f0L, 0.5f0 * 0.373f0L, 0.5f0 * 0.276f0L
    r = 0.1f0L                                    # nose/edge rounding
    c = SA[T(1.0L), T(n / 4), T(0.048f0L + hz)]   # body centre; wall at z=0 is the ground
    function box(x, t)
        q = abs.(x .- c) .- SA[hx - r, hy - r, hz - r]
        √sum(abs2, max.(q, 0)) + min(maximum(q), 0) - r
    end
    body = AutoBody(box) + AutoBody((x, t) -> x[3] - 1f0, (x, t) -> x .- SA[U * t, 0, 0])  # ground plane, moving at U
    Simulation((n, n ÷ 2, n ÷ 4), (U, 0, 0), L; ν=U * L / Re, body, T, mem)
end

gpu_stats() = try
    strip(read(`nvidia-smi --query-gpu=temperature.gpu,power.draw,memory.used --format=csv,noheader`, String))
catch
    "n/a"
end

sizes = isempty(ARGS) ? [128, 256, 384, 512] : parse.(Int, ARGS)
println("GPU: ", CUDA.name(CUDA.device()))
for n in sizes
    sim = car_sim(n)
    cells = n * (n ÷ 2) * (n ÷ 4)
    for _ in 1:5; sim_step!(sim; remeasure=false); end      # warm-up / compile
    CUDA.synchronize()
    nsteps = 100
    t0 = time()
    for _ in 1:nsteps; sim_step!(sim; remeasure=false); end
    CUDA.synchronize()
    dt = time() - t0
    conv = sim_time(sim)                                    # convective time units (body lengths travelled)
    f = try; WaterLily.pressure_force(sim) ./ (0.5f0 * sim.L^2); catch; [NaN, NaN, NaN]; end
    @printf("n=%4d cells=%6.2fM  %.1f ms/step  %.2f ns/cell/step  conv_time=%.2f L  Cd~%.3f Cl~%.3f  [temp,W,mem] %s\n",
        n, cells / 1e6, 1e3dt / nsteps, 1e9dt / nsteps / cells, conv, f[1], f[3], gpu_stats())
    flush(stdout)
    sim = nothing; GC.gc(); CUDA.reclaim()
end
