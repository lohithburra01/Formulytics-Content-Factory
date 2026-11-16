# car_sim() shared by the spike scripts (copied from bench.jl)
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

