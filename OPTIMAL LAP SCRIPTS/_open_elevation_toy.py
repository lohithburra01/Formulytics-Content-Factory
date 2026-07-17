"""Launcher used by open_elevation_3d.bat — builds the toy and sets up a nice
viewport. Not meant to be run standalone; use the .bat (or Run Script the toy)."""
import bpy

# clean the factory-startup default cube so it doesn't sit under the track
o = bpy.data.objects.get("Cube")
if o:
    bpy.data.objects.remove(o, do_unlink=True)

# build the elevated 3D Spa toy
exec(open(r"D:\f1_hot_lap\OPTIMAL LAP SCRIPTS\elevation_3d_toy.py").read())

# frame a good starting moment + material-preview shading so it looks right instantly
try:
    bpy.context.scene.frame_set(460)
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                for sp in area.spaces:
                    if sp.type == "VIEW_3D":
                        sp.shading.type = "MATERIAL"
                        sp.shading.use_scene_lights = True
    print("[launcher] ready — orbit with middle-mouse, press SPACE to play the lap")
except Exception as e:
    print("[launcher] viewport setup skipped:", e)
