"""
End-to-end smoke test for the SFH-OS geometry -> acoustics pipeline.

Runs with the standard library only:

    python3 -m unittest discover -s tests -v

It exercises the two Python engines the MCP servers shell out to, so it
catches the failure modes found in review: the generator not emitting a
profile, and the simulator scoring every horn identically.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GENERATOR = REPO / "mcp-servers" / "geometry" / "scripts" / "generate_horn.py"
SIMULATOR = REPO / "mcp-servers" / "acoustics" / "scripts" / "acoustic_sim.py"

PROFILE_TYPES = ["hilbert", "peano", "mandelbrot", "exponential", "tractrix"]


def run_json(script: Path, *args: str) -> dict:
    """Run a script with -I (isolated) and parse its JSON stdout."""
    proc = subprocess.run(
        [sys.executable, "-I", str(script), *args],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(f"{script.name} failed ({proc.returncode}):\n{proc.stderr}")
    start = proc.stdout.index("{")
    return json.loads(proc.stdout[start:])


class PipelineSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.generated = {}
        for t in PROFILE_TYPES:
            stl = cls.out / f"{t}.stl"
            cls.generated[t] = run_json(
                GENERATOR, "--type", t, "--output", str(stl), "--json",
                "--throat", "25.4", "--mouth", "300", "--length", "400",
            )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_generator_writes_mesh_and_profile(self):
        for t, result in self.generated.items():
            with self.subTest(profile=t):
                stl = Path(result["output"]["stl_path"])
                profile = Path(result["output"]["profile_path"])
                self.assertTrue(stl.exists(), f"missing mesh for {t}")
                self.assertTrue(profile.exists(), f"missing profile for {t}")
                self.assertEqual(profile, stl.with_suffix("").with_name(stl.stem + "_profile.json"))
                points = json.loads(profile.read_text())
                self.assertGreater(len(points), 10)
                self.assertEqual(set(points[0]), {"z", "radius"})
                # monotone z, throat at the start, mouth at the end
                zs = [p["z"] for p in points]
                self.assertEqual(zs, sorted(zs))
                # The mandelbrot profile applies its ripple at the throat too, so
                # allow a few percent at both ends rather than exact equality.
                self.assertAlmostEqual(points[0]["radius"] * 2, 25.4, delta=25.4 * 0.05)
                self.assertAlmostEqual(points[-1]["radius"] * 2, 300.0, delta=300 * 0.05)

    def test_stl_is_well_formed(self):
        stl = Path(self.generated["hilbert"]["output"]["stl_path"]).read_text()
        self.assertTrue(stl.startswith("solid "))
        self.assertTrue(stl.rstrip().endswith("endsolid sfh_hilbert_horn"))
        expected_faces = self.generated["hilbert"]["output"]["face_count"]
        self.assertEqual(stl.count("facet normal"), expected_faces)

    def test_simulation_runs_on_emitted_profile(self):
        profile = self.generated["hilbert"]["output"]["profile_path"]
        result = run_json(SIMULATOR, "--profile", profile, "--freq-points", "50")
        self.assertIn("score", result)
        score = result["score"]
        for key in ("impedance_smoothness", "frequency_flatness", "overall"):
            self.assertGreaterEqual(score[key], 0.0)
            self.assertLessEqual(score[key], 1.0)
        # A horn that is matched at all should not reflect everything.
        refl = result["impedance"]["data"]["reflection_coefficient"]
        self.assertLess(min(refl), 0.5, "reflection never drops below 0.5: unit mismatch?")
        self.assertLess(result["impedance"]["reflection_coefficient_avg"], 0.9)

    def test_scores_differ_across_profile_types(self):
        scores = {}
        for t, result in self.generated.items():
            sim = run_json(SIMULATOR, "--profile", result["output"]["profile_path"], "--freq-points", "50")
            scores[t] = sim["score"]["overall"]
        self.assertGreater(
            len(set(scores.values())), 1,
            f"every profile type scored identically: {scores}",
        )
        # The reference horns with the same endpoints must not all be "Poor".
        self.assertGreater(max(scores.values()), 0.3, scores)


if __name__ == "__main__":
    unittest.main()
