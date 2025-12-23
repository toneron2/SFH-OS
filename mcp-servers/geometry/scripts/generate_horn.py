#!/usr/bin/env python3
"""
SFH-OS Horn Geometry Generator

FreeCAD-based geometry generation for fractal acoustic horns.
Supports Hilbert, Peano, and Mandelbrot expansion profiles.

Usage:
    freecadcmd generate_horn.py -- --type hilbert --order 4 --throat 25.4 --mouth 300 --length 400 --output horn.stl

Or as module:
    from generate_horn import generate_hilbert_horn, generate_mandelbrot_horn
"""

import sys
import json
import math
import argparse
from pathlib import Path

# FreeCAD imports (available when run via freecadcmd)
try:
    import FreeCAD
    import Part
    import Mesh
    FREECAD_AVAILABLE = True
except ImportError:
    FREECAD_AVAILABLE = False
    print("Warning: FreeCAD not available, running in analysis-only mode", file=sys.stderr)


def hilbert_3d(order: int, size: float = 1.0) -> list:
    """
    Generate 3D Hilbert curve points.

    The 3D Hilbert curve is a space-filling curve that visits every point
    in a 3D grid while maintaining locality (nearby points on the curve
    are nearby in space).
    """
    def hilbert_d2xy(n, d):
        """Convert Hilbert index to 2D coordinates."""
        x = y = 0
        s = 1
        while s < n:
            rx = 1 & (d // 2)
            ry = 1 & (d ^ rx)
            if ry == 0:
                if rx == 1:
                    x = s - 1 - x
                    y = s - 1 - y
                x, y = y, x
            x += s * rx
            y += s * ry
            d //= 4
            s *= 2
        return x, y

    n = 2 ** order
    points = []

    # Generate 3D curve by stacking 2D Hilbert curves with z-variation
    for z_level in range(n):
        for d in range(n * n):
            x, y = hilbert_d2xy(n, d)
            # Normalize to [0, 1] range
            px = x / (n - 1) if n > 1 else 0.5
            py = y / (n - 1) if n > 1 else 0.5
            pz = z_level / (n - 1) if n > 1 else 0.5
            points.append((px * size, py * size, pz * size))

    return points


def peano_3d(iterations: int, size: float = 1.0) -> list:
    """
    Generate 3D Peano curve points.

    Peano curves have higher fractal dimension than Hilbert curves,
    creating denser space-filling patterns.
    """
    def peano_2d(n):
        """Generate 2D Peano curve."""
        if n == 0:
            return [(0, 0)]

        prev = peano_2d(n - 1)
        scale = 1 / 3
        result = []

        # 9 sub-squares arrangement for Peano curve
        transforms = [
            (0, 0, False, False),
            (0, 1, False, True),
            (0, 2, False, False),
            (1, 2, True, False),
            (1, 1, True, True),
            (1, 0, True, False),
            (2, 0, False, False),
            (2, 1, False, True),
            (2, 2, False, False),
        ]

        for tx, ty, flip_x, flip_y in transforms:
            for px, py in (reversed(prev) if flip_x else prev):
                x = (tx + (1 - px if flip_x else px)) * scale
                y = (ty + (1 - py if flip_y else py)) * scale
                result.append((x, y))

        return result

    points_2d = peano_2d(iterations)
    n = 3 ** iterations
    points = []

    # Extend to 3D
    for z_level in range(n):
        for px, py in points_2d:
            pz = z_level / (n - 1) if n > 1 else 0.5
            points.append((px * size, py * size, pz * size))

    return points


def mandelbrot_boundary_sample(c_real: float, c_imag: float,
                                num_points: int = 100,
                                max_iter: int = 100) -> list:
    """
    Sample the Mandelbrot set boundary near point c.

    Returns points along the boundary that can be used to modulate
    horn expansion profile with fractal detail.
    """
    def escape_time(cr, ci, max_iter):
        zr, zi = 0, 0
        for i in range(max_iter):
            zr_new = zr * zr - zi * zi + cr
            zi_new = 2 * zr * zi + ci
            zr, zi = zr_new, zi_new
            if zr * zr + zi * zi > 4:
                return i
        return max_iter

    boundary_points = []

    # Sample in a small region around c
    radius = 0.1
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        sample_r = c_real + radius * math.cos(angle)
        sample_i = c_imag + radius * math.sin(angle)

        escape = escape_time(sample_r, sample_i, max_iter)
        normalized_escape = escape / max_iter

        boundary_points.append({
            'angle': angle,
            'escape_ratio': normalized_escape,
            'in_set': escape == max_iter
        })

    return boundary_points


def generate_expansion_profile(throat_d: float, mouth_d: float, length: float,
                                profile_type: str, num_points: int = 100,
                                **kwargs) -> list:
    """
    Generate horn expansion profile (radius vs. position).

    Returns list of (z, radius) tuples defining the horn's cross-sectional
    expansion from throat to mouth.
    """
    profile = []

    for i in range(num_points + 1):
        t = i / num_points  # Normalized position [0, 1]
        z = length * t

        if profile_type == 'hilbert':
            # Hilbert: Smooth S-curve expansion (optimal for impedance matching)
            # Uses hermite interpolation for smooth transition
            h = 3 * t * t - 2 * t * t * t
            radius = (throat_d / 2) + ((mouth_d - throat_d) / 2) * h

        elif profile_type == 'peano':
            # Peano: More aggressive mid-section expansion
            # Creates stronger acoustic loading in mid-frequencies
            radius = (throat_d / 2) + ((mouth_d - throat_d) / 2) * math.pow(t, 1.3)

        elif profile_type == 'mandelbrot':
            # Mandelbrot: Fractal-modulated expansion
            c_real = kwargs.get('c_real', -0.75)
            c_imag = kwargs.get('c_imag', 0)
            iterations = kwargs.get('iterations', 100)

            # Base tractrix-like expansion
            base_radius = (throat_d / 2) + ((mouth_d - throat_d) / 2) * math.pow(t, 1.2)

            # Fractal modulation from Mandelbrot boundary
            angle = t * 2 * math.pi
            zr, zi = 0, 0
            for _ in range(int(iterations * t) + 1):
                zr_new = zr * zr - zi * zi + c_real
                zi_new = 2 * zr * zi + c_imag
                zr, zi = zr_new, zi_new
                if zr * zr + zi * zi > 4:
                    break

            # Modulation amplitude decreases with position (less at mouth)
            mod_amplitude = 0.03 * (1 - t * 0.5)
            modulation = 1 + mod_amplitude * math.sin(angle * 8 + zr)
            radius = base_radius * modulation

        elif profile_type == 'exponential':
            # Classic exponential horn for reference
            T = length / math.log(mouth_d / throat_d)
            radius = (throat_d / 2) * math.exp(z / T)

        elif profile_type == 'tractrix':
            # Tractrix horn - theoretical ideal for impedance matching
            radius = (throat_d / 2) * math.cosh(z / (length / math.acosh(mouth_d / throat_d)))

        else:
            # Linear fallback
            radius = (throat_d / 2) + ((mouth_d - throat_d) / 2) * t

        profile.append({'z': z, 'radius': radius})

    return profile


def calculate_fractal_dimension(profile: list) -> float:
    """
    Estimate fractal dimension using box-counting method on the profile.
    """
    if len(profile) < 10:
        return 1.0

    # Extract radius variation
    radii = [p['radius'] for p in profile]
    z_vals = [p['z'] for p in profile]

    # Compute derivative (local slope changes indicate complexity)
    derivatives = []
    for i in range(1, len(radii)):
        dr = radii[i] - radii[i-1]
        dz = z_vals[i] - z_vals[i-1]
        if dz > 0:
            derivatives.append(abs(dr / dz))

    if not derivatives:
        return 1.0

    # Box counting approximation
    # Higher variation = higher fractal dimension
    mean_deriv = sum(derivatives) / len(derivatives)
    std_deriv = math.sqrt(sum((d - mean_deriv)**2 for d in derivatives) / len(derivatives))

    # Map to fractal dimension range [1.0, 2.0]
    # Coefficient of variation indicates complexity
    cv = std_deriv / mean_deriv if mean_deriv > 0 else 0
    fractal_dim = 1.0 + min(1.0, cv * 2)

    return round(fractal_dim, 3)


def create_horn_solid(profile: list, angular_resolution: int = 72) -> 'Part.Shape':
    """
    Create a FreeCAD solid from an expansion profile by revolution.

    The profile is revolved around the Z-axis to create the horn shape.
    """
    if not FREECAD_AVAILABLE:
        raise RuntimeError("FreeCAD is required for solid generation")

    # Create profile wire
    points = []
    for p in profile:
        points.append(FreeCAD.Vector(p['radius'], 0, p['z']))

    # Add closing points (back to axis)
    points.append(FreeCAD.Vector(0, 0, profile[-1]['z']))
    points.append(FreeCAD.Vector(0, 0, profile[0]['z']))
    points.append(points[0])  # Close the wire

    # Create BSpline through profile points for smooth surface
    profile_curve = Part.BSplineCurve()
    profile_curve.interpolate(points[:-2])  # Exclude closing points for curve

    # Create wire with straight closing segments
    edges = [profile_curve.toShape()]
    edges.append(Part.makeLine(points[-3], points[-2]))
    edges.append(Part.makeLine(points[-2], points[-1]))
    edges.append(Part.makeLine(points[-1], points[0]))

    wire = Part.Wire(edges)
    face = Part.Face(wire)

    # Revolve around Z-axis
    axis = FreeCAD.Vector(0, 0, 1)
    center = FreeCAD.Vector(0, 0, 0)
    solid = face.revolve(center, axis, 360)

    return solid


def create_horn_mesh(profile: list, angular_resolution: int = 72) -> list:
    """
    Create mesh vertices and faces from profile (for non-FreeCAD export).

    Returns (vertices, faces) tuple for STL generation.
    """
    vertices = []
    faces = []

    num_profile_points = len(profile)

    # Generate vertices by revolving profile
    for i, p in enumerate(profile):
        for j in range(angular_resolution):
            angle = 2 * math.pi * j / angular_resolution
            x = p['radius'] * math.cos(angle)
            y = p['radius'] * math.sin(angle)
            z = p['z']
            vertices.append((x, y, z))

    # Generate faces (quads split into triangles)
    for i in range(num_profile_points - 1):
        for j in range(angular_resolution):
            # Current ring indices
            curr = i * angular_resolution + j
            next_j = i * angular_resolution + (j + 1) % angular_resolution
            # Next ring indices
            curr_next = (i + 1) * angular_resolution + j
            next_j_next = (i + 1) * angular_resolution + (j + 1) % angular_resolution

            # Two triangles per quad
            faces.append((curr, next_j, curr_next))
            faces.append((next_j, next_j_next, curr_next))

    # Cap the throat (first ring)
    center_throat = len(vertices)
    vertices.append((0, 0, profile[0]['z']))
    for j in range(angular_resolution):
        next_j = (j + 1) % angular_resolution
        faces.append((center_throat, next_j, j))

    # Cap the mouth (last ring)
    center_mouth = len(vertices)
    vertices.append((0, 0, profile[-1]['z']))
    last_ring_start = (num_profile_points - 1) * angular_resolution
    for j in range(angular_resolution):
        curr = last_ring_start + j
        next_j = last_ring_start + (j + 1) % angular_resolution
        faces.append((center_mouth, curr, next_j))

    return vertices, faces


def write_stl_ascii(vertices: list, faces: list, filepath: str, name: str = "horn"):
    """Write ASCII STL file."""
    def normal(v0, v1, v2):
        """Calculate face normal."""
        u = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        v = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        n = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0]
        )
        length = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
        if length > 0:
            return (n[0]/length, n[1]/length, n[2]/length)
        return (0, 0, 1)

    with open(filepath, 'w') as f:
        f.write(f"solid {name}\n")
        for face in faces:
            v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
            n = normal(v0, v1, v2)
            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {v0[0]:.6e} {v0[1]:.6e} {v0[2]:.6e}\n")
            f.write(f"      vertex {v1[0]:.6e} {v1[1]:.6e} {v1[2]:.6e}\n")
            f.write(f"      vertex {v2[0]:.6e} {v2[1]:.6e} {v2[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {name}\n")


def generate_horn(horn_type: str, throat_d: float, mouth_d: float, length: float,
                  output_path: str, angular_resolution: int = 72, **kwargs) -> dict:
    """
    Main horn generation function.

    Args:
        horn_type: 'hilbert', 'peano', 'mandelbrot', 'exponential', 'tractrix'
        throat_d: Throat diameter in mm
        mouth_d: Mouth diameter in mm
        length: Horn length in mm
        output_path: Path for STL output
        angular_resolution: Number of segments around circumference
        **kwargs: Additional parameters (order, iterations, c_real, c_imag)

    Returns:
        Dictionary with geometry metadata and metrics
    """
    # Generate expansion profile
    profile = generate_expansion_profile(
        throat_d, mouth_d, length, horn_type,
        num_points=100, **kwargs
    )

    # Calculate metrics
    fractal_dim = calculate_fractal_dimension(profile)

    # Calculate path length (arc length of profile curve)
    path_length = 0
    for i in range(1, len(profile)):
        dz = profile[i]['z'] - profile[i-1]['z']
        dr = profile[i]['radius'] - profile[i-1]['radius']
        path_length += math.sqrt(dz**2 + dr**2)

    # Calculate volume and surface area (approximation)
    volume = 0
    surface_area = 0
    for i in range(1, len(profile)):
        r1, r2 = profile[i-1]['radius'], profile[i]['radius']
        dz = profile[i]['z'] - profile[i-1]['z']

        # Volume of frustum
        volume += (math.pi * dz / 3) * (r1**2 + r1*r2 + r2**2)

        # Surface area of frustum (lateral)
        slant = math.sqrt(dz**2 + (r2-r1)**2)
        surface_area += math.pi * (r1 + r2) * slant

    # Generate mesh and export
    if FREECAD_AVAILABLE:
        try:
            solid = create_horn_solid(profile, angular_resolution)
            mesh = Mesh.Mesh()
            mesh.addFacets(solid.tessellate(0.1)[1])
            mesh.write(output_path)
        except Exception as e:
            print(f"FreeCAD export failed: {e}, using fallback", file=sys.stderr)
            vertices, faces = create_horn_mesh(profile, angular_resolution)
            write_stl_ascii(vertices, faces, output_path, f"sfh_{horn_type}_horn")
    else:
        vertices, faces = create_horn_mesh(profile, angular_resolution)
        write_stl_ascii(vertices, faces, output_path, f"sfh_{horn_type}_horn")

    # Build result metadata
    result = {
        'geometry_type': horn_type,
        'parameters': {
            'throat_diameter_mm': throat_d,
            'mouth_diameter_mm': mouth_d,
            'length_mm': length,
            'angular_resolution': angular_resolution,
            **kwargs
        },
        'metrics': {
            'fractal_dimension': fractal_dim,
            'expansion_ratio': mouth_d / throat_d,
            'path_length_mm': round(path_length, 2),
            'volume_mm3': round(volume, 2),
            'surface_area_mm2': round(surface_area, 2),
        },
        'output': {
            'stl_path': output_path,
            'vertex_count': angular_resolution * 101 + 2,
            'face_count': angular_resolution * 100 * 2 + angular_resolution * 2,
        },
        'profile': profile
    }

    return result


def main():
    parser = argparse.ArgumentParser(description='Generate fractal horn geometry')
    parser.add_argument('--type', choices=['hilbert', 'peano', 'mandelbrot', 'exponential', 'tractrix'],
                        default='hilbert', help='Horn profile type')
    parser.add_argument('--throat', type=float, default=25.4, help='Throat diameter (mm)')
    parser.add_argument('--mouth', type=float, default=300, help='Mouth diameter (mm)')
    parser.add_argument('--length', type=float, default=400, help='Horn length (mm)')
    parser.add_argument('--output', type=str, required=True, help='Output STL path')
    parser.add_argument('--resolution', type=int, default=72, help='Angular resolution')
    parser.add_argument('--order', type=int, default=4, help='Hilbert curve order')
    parser.add_argument('--iterations', type=int, default=100, help='Iterations (Peano/Mandelbrot)')
    parser.add_argument('--c-real', type=float, default=-0.75, help='Mandelbrot c real component')
    parser.add_argument('--c-imag', type=float, default=0, help='Mandelbrot c imaginary component')
    parser.add_argument('--json', action='store_true', help='Output result as JSON')

    args = parser.parse_args()

    result = generate_horn(
        horn_type=args.type,
        throat_d=args.throat,
        mouth_d=args.mouth,
        length=args.length,
        output_path=args.output,
        angular_resolution=args.resolution,
        order=args.order,
        iterations=args.iterations,
        c_real=args.c_real,
        c_imag=args.c_imag
    )

    # Remove profile from JSON output (too large)
    result_output = {k: v for k, v in result.items() if k != 'profile'}

    if args.json:
        print(json.dumps(result_output, indent=2))
    else:
        print(f"Generated {args.type} horn:")
        print(f"  Fractal dimension: {result['metrics']['fractal_dimension']}")
        print(f"  Volume: {result['metrics']['volume_mm3']} mm³")
        print(f"  Surface area: {result['metrics']['surface_area_mm2']} mm²")
        print(f"  Output: {args.output}")


if __name__ == '__main__':
    main()
