p="make_bahrain_2026_what_could_have_been.bat"; s=open(p).read()
a=s.index("echo === Stage 1"); b=s.index("copy /Y")
new=open("cache/bahrain/v2/_stages.txt").read()
s=s[:a]+new+s[b:]
s=s.replace("--t0 85.5 --dur 2.8","--t0 13 --dur 2.8 --p-from 1240 1550 --p-to -160 300")
s=s.replace("rem cda 0.777 cl 4.200 rho 1.2242 -> 1:31.28, gate 8/9 (GAIN cap, as v1).","rem v2b (current): apex-touch line, cda 0.787 cl 3.639 rho 1.2242 -> 1:32.20, gate 8/9 (GAIN cap, as v1).")
open(p,"w").write(s)
