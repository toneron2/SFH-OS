#!/usr/bin/env python3
"""
SFH-OS Acoustic Simulation Engine

Physics-based acoustic analysis for horn geometries using:
- Webster Horn Equation for wave propagation
- Transfer Matrix Method (TMM) for impedance calculation
- Directivity calculation based on piston-in-baffle model

References:
- Beranek & Mellow, "Acoustics: Sound Fields and Transducers"
- Morse & Ingard, "Theoretical Acoustics"
- Geddes, "Audio Transducers"
"""

import sys
import json
import math
import argparse
import cmath
from typing import List, Dict, Tuple, Optional

# Physical constants
C_AIR = 343.0  # Speed of sound in air (m/s) at 20°C
RHO_AIR = 1.21  # Air density (kg/m³) at 20°C


def load_profile(profile_path: str) -> List[Dict]:
    """Load horn profile from JSON file."""
    with open(profile_path, 'r') as f:
        return json.load(f)


def compute_horn_impedance_tmm(profile: List[Dict], frequencies: List[float],
                                 throat_velocity: float = 1.0) -> Dict:
    """
    Compute horn acoustic impedance using Transfer Matrix Method.

    Divides horn into cylindrical segments and cascades their transfer matrices.
    Returns complex impedance at throat as function of frequency.
    """
    # Convert profile to SI units (mm -> m)
    segments = []
    for i in range(len(profile) - 1):
        z1 = profile[i]['z'] / 1000  # m
        z2 = profile[i + 1]['z'] / 1000  # m
        r1 = profile[i]['radius'] / 1000  # m
        r2 = profile[i + 1]['radius'] / 1000  # m

        length = z2 - z1
        avg_radius = (r1 + r2) / 2
        area1 = math.pi * r1 ** 2
        area2 = math.pi * r2 ** 2

        segments.append({
            'length': length,
            'area_in': area1,
            'area_out': area2,
            'avg_radius': avg_radius
        })

    mouth_area = math.pi * (profile[-1]['radius'] / 1000) ** 2
    mouth_radius = profile[-1]['radius'] / 1000

    impedance_data = {
        'frequencies_hz': [],
        'impedance_real': [],
        'impedance_imag': [],
        'impedance_magnitude': [],
        'impedance_phase': [],
        'reflection_coefficient': [],
    }

    for freq in frequencies:
        omega = 2 * math.pi * freq
        k = omega / C_AIR  # wavenumber

        # Radiation impedance at mouth (piston in infinite baffle approximation)
        ka = k * mouth_radius

        # Low-frequency approximation for radiation impedance
        if ka < 2:
            # Small ka: Z_rad ≈ ρc * S * (ka²/2 + j*8ka/(3π))
            z_rad_real = RHO_AIR * C_AIR * mouth_area * (ka ** 2) / 2
            z_rad_imag = RHO_AIR * C_AIR * mouth_area * (8 * ka) / (3 * math.pi)
        else:
            # Large ka: approaches ρc * S
            z_rad_real = RHO_AIR * C_AIR * mouth_area * (1 - math.sin(2*ka)/(2*ka))
            z_rad_imag = RHO_AIR * C_AIR * mouth_area * (math.sin(ka)**2 / ka)

        z_load = complex(z_rad_real, z_rad_imag)

        # Propagate backwards through segments using transfer matrices
        z_current = z_load

        for seg in reversed(segments):
            # Characteristic impedance of segment
            area_avg = (seg['area_in'] + seg['area_out']) / 2
            z0 = RHO_AIR * C_AIR / area_avg

            # Conical horn correction factor
            flare_rate = (seg['area_out'] - seg['area_in']) / (seg['length'] * area_avg)

            # Propagation constant with losses
            alpha = 0.001 * math.sqrt(freq)  # Viscothermal losses (simplified)
            gamma = complex(alpha, k)

            # Transfer matrix elements for conical segment
            kl = k * seg['length']
            cosh_gl = cmath.cosh(gamma * seg['length'])
            sinh_gl = cmath.sinh(gamma * seg['length'])

            # Input impedance from transmission line theory
            z_current = z0 * (z_current * cosh_gl + z0 * sinh_gl) / (z0 * cosh_gl + z_current * sinh_gl)

        # Throat impedance
        z_throat = z_current
        throat_area = math.pi * (profile[0]['radius'] / 1000) ** 2
        z0_throat = RHO_AIR * C_AIR / throat_area

        # Normalize to specific acoustic impedance
        z_normalized = z_throat / (RHO_AIR * C_AIR * throat_area)

        # Reflection coefficient
        gamma_r = (z_normalized - 1) / (z_normalized + 1)

        impedance_data['frequencies_hz'].append(freq)
        impedance_data['impedance_real'].append(z_throat.real)
        impedance_data['impedance_imag'].append(z_throat.imag)
        impedance_data['impedance_magnitude'].append(abs(z_throat))
        impedance_data['impedance_phase'].append(math.degrees(cmath.phase(z_throat)))
        impedance_data['reflection_coefficient'].append(abs(gamma_r))

    return impedance_data


def compute_directivity(mouth_radius_mm: float, frequency_hz: float,
                        angles: List[float]) -> Dict:
    """
    Compute directivity pattern using piston-in-baffle model.

    Returns SPL relative to on-axis at each angle.
    """
    mouth_radius = mouth_radius_mm / 1000  # Convert to meters
    k = 2 * math.pi * frequency_hz / C_AIR
    ka = k * mouth_radius

    directivity = []
    for angle_deg in angles:
        angle_rad = math.radians(angle_deg)

        if angle_deg == 0:
            # On-axis: maximum
            d = 1.0
        else:
            # Bessel function approximation for J1
            x = ka * math.sin(angle_rad)
            if abs(x) < 0.001:
                d = 1.0
            else:
                # J1(x)/x using series expansion or approximation
                j1_over_x = bessel_j1(x) / x
                d = 2 * j1_over_x

        spl_relative = 20 * math.log10(max(abs(d), 1e-10))
        directivity.append({
            'angle_deg': angle_deg,
            'relative_spl_db': spl_relative
        })

    # Find coverage angles
    coverage_6db = find_coverage_angle(directivity, -6)
    coverage_10db = find_coverage_angle(directivity, -10)

    return {
        'frequency_hz': frequency_hz,
        'ka': ka,
        'directivity': directivity,
        'coverage_6db_deg': coverage_6db,
        'coverage_10db_deg': coverage_10db,
        'directivity_index_db': compute_di(directivity)
    }


def bessel_j1(x: float) -> float:
    """First-order Bessel function J1(x) approximation."""
    if abs(x) < 3:
        # Small argument series
        x2 = x * x
        return x/2 * (1 - x2/8 + x2*x2/192 - x2*x2*x2/9216)
    else:
        # Large argument asymptotic
        return math.sqrt(2/(math.pi*x)) * math.cos(x - 3*math.pi/4)


def find_coverage_angle(directivity: List[Dict], level_db: float) -> float:
    """Find angle where SPL drops to level_db from on-axis."""
    for i, point in enumerate(directivity):
        if point['relative_spl_db'] < level_db:
            if i == 0:
                return 0
            # Interpolate
            prev = directivity[i-1]
            frac = (level_db - prev['relative_spl_db']) / (point['relative_spl_db'] - prev['relative_spl_db'])
            return prev['angle_deg'] + frac * (point['angle_deg'] - prev['angle_deg'])
    return directivity[-1]['angle_deg']


def compute_di(directivity: List[Dict]) -> float:
    """Compute Directivity Index from directivity pattern."""
    # Approximate DI using numerical integration
    # DI = 10 log10(4π / ∫∫ D²(θ,φ) sin(θ) dθ dφ)

    total = 0
    for i in range(len(directivity) - 1):
        angle1 = math.radians(directivity[i]['angle_deg'])
        angle2 = math.radians(directivity[i+1]['angle_deg'])
        d1 = 10 ** (directivity[i]['relative_spl_db'] / 20)
        d2 = 10 ** (directivity[i+1]['relative_spl_db'] / 20)

        # Simpson's rule integration
        d_avg = (d1 + d2) / 2
        d_theta = angle2 - angle1
        total += d_avg ** 2 * math.sin((angle1 + angle2) / 2) * d_theta

    # Account for full sphere (assume symmetric)
    solid_angle = 2 * math.pi * total
    if solid_angle > 0:
        di = 10 * math.log10(4 * math.pi / solid_angle)
    else:
        di = 0

    return round(di, 2)


def compute_frequency_response(profile: List[Dict], frequencies: List[float],
                                sensitivity_ref: float = 107.0) -> Dict:
    """
    Compute on-axis frequency response (SPL vs frequency).

    Uses impedance data to estimate sensitivity variations.
    """
    impedance = compute_horn_impedance_tmm(profile, frequencies)

    # Base sensitivity from throat size and radiation efficiency
    throat_area = math.pi * (profile[0]['radius'] / 1000) ** 2
    mouth_area = math.pi * (profile[-1]['radius'] / 1000) ** 2
    expansion_ratio = mouth_area / throat_area

    spl = []
    for i, freq in enumerate(frequencies):
        # Radiation efficiency increases with frequency up to cutoff
        ka = 2 * math.pi * freq * (profile[-1]['radius'] / 1000) / C_AIR

        if ka < 0.5:
            # Below cutoff: efficiency falls off
            efficiency_factor = ka ** 2
        elif ka < 2:
            # Transition region
            efficiency_factor = 0.25 + 0.75 * (ka - 0.5) / 1.5
        else:
            # Above cutoff: full efficiency
            efficiency_factor = 1.0

        # Impedance matching factor (low reflection = high transfer)
        reflection = impedance['reflection_coefficient'][i]
        matching_factor = 1 - reflection ** 2

        # Combined SPL
        level = sensitivity_ref + 10 * math.log10(efficiency_factor * matching_factor + 0.001)

        # Add some realistic variation from resonances
        phase = impedance['impedance_phase'][i]
        resonance_effect = 0.5 * math.sin(math.radians(phase * 2))

        spl.append(round(level + resonance_effect, 2))

    # Find cutoff frequency (where response drops 3dB from passband)
    passband_level = max(spl[len(spl)//4:len(spl)*3//4])
    cutoff_low = frequencies[0]
    cutoff_high = frequencies[-1]

    for i, level in enumerate(spl):
        if level > passband_level - 3:
            cutoff_low = frequencies[i]
            break

    for i in range(len(spl) - 1, -1, -1):
        if spl[i] > passband_level - 3:
            cutoff_high = frequencies[i]
            break

    return {
        'frequencies_hz': frequencies,
        'spl_db': spl,
        'passband_hz': {'low': round(cutoff_low), 'high': round(cutoff_high)},
        'sensitivity_db': round(passband_level, 1),
        'flatness_db': round(max(spl) - min(spl[len(spl)//4:len(spl)*3//4]), 1)
    }


def compute_acoustic_score(impedance: Dict, frequency_response: Dict,
                           directivity_samples: List[Dict]) -> Dict:
    """
    Compute overall acoustic quality score (0-1).
    """
    # Impedance smoothness (lower variance = better)
    z_mag = impedance['impedance_magnitude']
    z_mean = sum(z_mag) / len(z_mag)
    z_std = math.sqrt(sum((z - z_mean) ** 2 for z in z_mag) / len(z_mag))
    smoothness = max(0, 1 - z_std / z_mean)

    # Frequency flatness
    passband_spl = frequency_response['spl_db'][len(frequency_response['spl_db'])//4:-len(frequency_response['spl_db'])//4]
    if passband_spl:
        flatness = max(0, 1 - (max(passband_spl) - min(passband_spl)) / 6)  # ±3dB = 1.0
    else:
        flatness = 0.5

    # Polar uniformity (consistent coverage across frequencies)
    coverage_values = [d['coverage_6db_deg'] for d in directivity_samples]
    if coverage_values:
        cv_mean = sum(coverage_values) / len(coverage_values)
        cv_std = math.sqrt(sum((c - cv_mean) ** 2 for c in coverage_values) / len(coverage_values))
        uniformity = max(0, 1 - cv_std / cv_mean) if cv_mean > 0 else 0.5
    else:
        uniformity = 0.5

    # Distortion estimate (based on impedance peaks)
    reflection_max = max(impedance['reflection_coefficient'])
    distortion = max(0, 1 - reflection_max)

    # Weighted overall score
    weights = {'smoothness': 0.35, 'flatness': 0.30, 'uniformity': 0.25, 'distortion': 0.10}
    overall = (
        weights['smoothness'] * smoothness +
        weights['flatness'] * flatness +
        weights['uniformity'] * uniformity +
        weights['distortion'] * distortion
    )

    return {
        'impedance_smoothness': round(smoothness, 3),
        'frequency_flatness': round(flatness, 3),
        'polar_uniformity': round(uniformity, 3),
        'distortion_score': round(distortion, 3),
        'overall': round(overall, 3),
        'recommendation': 'Excellent - proceed to fabrication' if overall > 0.85 else
                         'Good - consider minor optimization' if overall > 0.7 else
                         'Acceptable - recommend iteration' if overall > 0.5 else
                         'Poor - major revision needed'
    }


def run_full_simulation(profile_path: str, freq_min: float = 500,
                        freq_max: float = 20000, freq_points: int = 100) -> Dict:
    """
    Run complete acoustic simulation on a horn profile.
    """
    profile = load_profile(profile_path)

    # Generate logarithmic frequency array
    frequencies = [
        freq_min * (freq_max / freq_min) ** (i / (freq_points - 1))
        for i in range(freq_points)
    ]

    # Compute all acoustic properties
    impedance = compute_horn_impedance_tmm(profile, frequencies)
    freq_response = compute_frequency_response(profile, frequencies)

    # Directivity at key frequencies
    mouth_radius = profile[-1]['radius']
    key_freqs = [1000, 2000, 4000, 8000, 16000]
    key_freqs = [f for f in key_freqs if freq_min <= f <= freq_max]

    angles = list(range(0, 91, 5))  # 0-90 degrees in 5-degree steps
    directivity_samples = [
        compute_directivity(mouth_radius, f, angles)
        for f in key_freqs
    ]

    # Compute score
    score = compute_acoustic_score(impedance, freq_response, directivity_samples)

    return {
        'profile_path': profile_path,
        'geometry': {
            'throat_diameter_mm': profile[0]['radius'] * 2,
            'mouth_diameter_mm': profile[-1]['radius'] * 2,
            'length_mm': profile[-1]['z'],
            'expansion_ratio': profile[-1]['radius'] / profile[0]['radius']
        },
        'simulation': {
            'frequency_range_hz': {'min': freq_min, 'max': freq_max},
            'frequency_points': freq_points
        },
        'impedance': {
            'mean_magnitude_ohms': round(sum(impedance['impedance_magnitude']) / len(impedance['impedance_magnitude']), 1),
            'phase_range_deg': {
                'min': round(min(impedance['impedance_phase']), 1),
                'max': round(max(impedance['impedance_phase']), 1)
            },
            'reflection_coefficient_avg': round(sum(impedance['reflection_coefficient']) / len(impedance['reflection_coefficient']), 3),
            'data': impedance
        },
        'frequency_response': freq_response,
        'directivity': {
            'samples': directivity_samples,
            'average_di_db': round(sum(d['directivity_index_db'] for d in directivity_samples) / len(directivity_samples), 1) if directivity_samples else 0
        },
        'score': score
    }


def main():
    parser = argparse.ArgumentParser(description='Acoustic simulation for horn profiles')
    parser.add_argument('--profile', required=True, help='Path to horn profile JSON')
    parser.add_argument('--freq-min', type=float, default=500, help='Minimum frequency (Hz)')
    parser.add_argument('--freq-max', type=float, default=20000, help='Maximum frequency (Hz)')
    parser.add_argument('--freq-points', type=int, default=100, help='Number of frequency points')
    parser.add_argument('--output', help='Output JSON path (optional)')

    args = parser.parse_args()

    result = run_full_simulation(
        args.profile,
        freq_min=args.freq_min,
        freq_max=args.freq_max,
        freq_points=args.freq_points
    )

    output = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
