# Scene validation

The saved Blender model, exported FBX, imported Unreal assets, and interactive scene were validated together on 2026-10-01.

## Geometry

- The saved Blender scene was reopened and inspected: 47 mesh objects, approximately 2.10 million triangles, and surface UVs on every mesh.
- The widest tower floor spans approximately 60.93 m, compared with the original report's approximately 200 ft / 60.96 m reference. The roof elevation is approximately 43.51 m above the model origin; the forum grade is 10 m.
- The generated Snake Path centerline measures 170.688 m, with a documented width reference of 3.048 m.
- The garden coil has one connected paving region surrounding one planted opening of approximately 62.15 m². Saved paving triangles face upward, and all 62 coil centerline samples lie within the paved surface.
- Contacting parts of the coil share a merged paving footprint. Overlapping slate tiles are clipped, and perimeter lines follow the merged outer boundary and garden boundary.
- The two terrace-height bollards above the sunken south entrance have been removed. Saved-mesh ray checks confirm both former positions are clear.
- The two unsupported concrete frames beside the lower Snake Path approach have been removed from the generator and saved Blender scene.

## Unreal import and runtime

- Unreal Engine 5.7 imported 48 meshes, 51 materials, and 81 material slots. The imported FBX checksum matches `SourceAssets/GeiselSite.fbx`.
- The saved level is `/Game/Geisel/Maps/L_GeiselLibrary`.
- Runtime assertions passed for initial view, flight movement, viewpoint switching, lighting presets, ground traces, grounded walking, walking movement, and interface visibility.
- Both former floating-bollard positions passed runtime clearance traces. No imported concrete-frame mesh remains in the level or asset directory.
- Focused south-entrance and north/south approach captures were visually inspected. The three review views supplement the coil review view; the four keyboard-selectable visitor viewpoints are unchanged.
- All **62 / 62** garden-coil probes hit Snake Path paving rather than the terrain beneath it.
- A dedicated coil viewpoint produced the runtime capture published as [Snake-Path.png](../Previews/Snake-Path.png). It was visually inspected for the complete garden enclosure and continuous contact.
- PowerShell and Python source syntax checks passed.

## Reproducing the checks

Run the rebuild and self-test workflow documented in the [README](../README.md). The Blender rebuild includes saved-artifact audits. The Unreal self-test refreshes the curated runtime previews after all assertions pass.

Machine-readable records:

- [GeometryValidation.json](GeometryValidation.json): saved Blender scene audit.
- [SnakePathValidation.json](SnakePathValidation.json): paving topology, orientation, overlap tolerance, and coil probes.
- [RuntimeValidation.json](RuntimeValidation.json): import checksum, runtime assertions, and published captures.

## Fidelity and performance limits

This is a reference-guided exterior reconstruction. Terrain elevations, planting, minor facade dimensions, and surrounding context are estimates rather than survey measurements. The distant ground is simplified environmental context.

Validation used Windows 64-bit with an NVIDIA RTX 4070 Laptop GPU. Large foliage shadows can produce virtual-shadow-map task-queue warnings; the tested movement, collision checks, and captures still passed. Other hardware configurations have not been comprehensively tested.
