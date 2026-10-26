# THROWAWAY SPIKE: run the box-over-moving-ground case until the wake settles, save velocity slices for plotting.
# Usage: julia --project=. wake_picture.jl [n] [conv_lengths]
using WaterLily, StaticArrays, CUDA, Printf
include("bench_body.jl")

n = length(ARGS) >= 1 ? parse(Int, ARGS[1]) : 256
tend = length(ARGS) >= 2 ? parse(Float32, ARGS[2]) : 8f0
sim = car_sim(n)
t0 = time()
sim_step!(sim, tend; remeasure=false)
CUDA.synchronize()
@printf("n=%d settled to %.1f body lengths in %.1f s\n", n, sim_time(sim), time() - t0)

u = Array(sim.flow.u)                                  # (nx+2, ny+2, nz+2, 3), ghost cells included
speed = sqrt.(sum(abs2, u; dims=4))[:, :, :, 1] ./ sim.U
L = sim.L
kz = round(Int, 0.048 * L + 0.276 * L * 0.5) + 2       # mid-height of the body
jy = n ÷ 4 + 1                                          # centreline
open("wake_$(n).bin", "w") do io
    write(io, Int32[size(speed)..., kz, jy]); write(io, Float32(L)); write(io, Float32.(speed))
end
println("saved wake_$(n).bin")
