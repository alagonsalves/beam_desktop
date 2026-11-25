# Beam Designer Validation Report

## Method

These values were produced directly by `beam_calculations.calculate` with the
same models used by the Tkinter application. Internal moments are in kip-in
and deflections use kip-in unit consistency; table values below convert moments
to kip-ft by dividing by 12.

## Expected versus actual

| Case | Result | Expected | Actual | Tolerance | Status |
|---|---|---:|---:|---:|---|
| 1 | Left reaction | 10.000 k | 10.000 k | 0.010 k | PASS |
| 1 | Right reaction | 10.000 k | 10.000 k | 0.010 k | PASS |
| 1 | Max shear | 10.000 k | 10.000 k | 0.010 k | PASS |
| 1 | Max moment | 50.000 kip-ft | 50.000 kip-ft | 0.010 kip-ft | PASS |
| 1 | Bending stress | 17.960 ksi | 17.964 ksi | 0.010 ksi | PASS |
| 1 | Deflection | 0.609 in | 0.609 in | 0.001 in | PASS |
| 1 | L/360 limit | 0.667 in | 0.667 in | 0.001 in | PASS |
| 2 | Left reaction | 7.500 k | 7.500 k | 0.010 k | PASS |
| 2 | Right reaction | 2.500 k | 2.500 k | 0.010 k | PASS |
| 2 | Max moment | 37.500 kip-ft | 37.500 kip-ft | 0.010 kip-ft | PASS |
| 2 | Deflection location | 8.820 ft | 8.8125 ft | 0.010 ft | PASS |
| 2 | Bending stress | 13.470 ksi | 13.473 ksi | 0.010 ksi | PASS |
| 2 | Deflection | 0.340 in | 0.340 in | 0.001 in | PASS |
| 3 | Reaction | 5.000 k | 5.000 k | 0.010 k | PASS |
| 3 | Fixed-end moment | 50.000 kip-ft | 50.000 kip-ft | 0.010 kip-ft | PASS |
| 3 | Deflection | 0.487 in | 0.487 in | 0.001 in | PASS |
| 3 | L/360 limit | 0.333 in | 0.333 in | 0.001 in | PASS |
| 3 | Deflection check | FAIL | FAIL | -- | PASS |
| 4 | Max moment | 0.900 kip-ft | 0.900 kip-ft | 0.010 kip-ft | PASS |
| 4 | Bending stress | 0.505 ksi | 0.505 ksi | 0.010 ksi | PASS |
| 4 | Deflection | 0.147 in | 0.147 in | 0.001 in | PASS |
| 5 | Left reaction | 0.260 k | 0.260 k | 0.010 k | PASS |
| 5 | Right reaction | 0.260 k | 0.260 k | 0.010 k | PASS |
| 5 | Max moment | 1.300 kip-ft | 1.300 kip-ft | 0.010 kip-ft | PASS |
| 5 | Bending stress | 0.467 ksi | 0.467 ksi | 0.010 ksi | PASS |
| 5 | Deflection | 0.016 in | 0.016 in | 0.001 in | PASS |
| 6 | Left reaction | 10.260 k | 10.260 k | 0.010 k | PASS |
| 6 | Right reaction | 10.260 k | 10.260 k | 0.010 k | PASS |
| 6 | Max moment | 51.300 kip-ft | 51.300 kip-ft | 0.010 kip-ft | PASS |
| 6 | Bending stress | 18.430 ksi | 18.431 ksi | 0.010 ksi | PASS |
| 6 | Deflection | 0.624 in | 0.624 in | 0.001 in | PASS |
| 7 | Reaction | 0.260 k | 0.260 k | 0.010 k | PASS |
| 7 | Fixed-end moment | 1.300 kip-ft | 1.300 kip-ft | 0.010 kip-ft | PASS |
| 7 | Deflection | 0.009 in | 0.009493 in | 0.001 in | PASS |
| 8 | W12x26 moment | 1.300 kip-ft | 1.300 kip-ft | 0.010 kip-ft | PASS |
| 8 | W12x26 bending stress | 0.467 ksi | 0.467 ksi | 0.010 ksi | PASS |
| 8 | W12x26 deflection | 0.016 in | 0.016 in | 0.001 in | PASS |
| 8 | W10x12 moment | 0.600 kip-ft | 0.600 kip-ft | 0.010 kip-ft | PASS |
| 8 | W10x12 bending stress | 0.661 ksi | 0.661 ksi | 0.010 ksi | PASS |
| 8 | W10x12 deflection | 0.028 in | 0.027689 in | 0.001 in | PASS |
| 9 | Max moment | 0.900 kip-ft | 0.900 kip-ft | 0.010 kip-ft | PASS |
| 9 | Bending stress | 0.505 ksi | 0.505 ksi | 0.010 ksi | PASS |
| 9 | Deflection | 0.147 in | 0.147 in | 0.001 in | PASS |

## Work

- Reactions and shear use statics from the combined point and uniform load model.
- For simply supported beams:
  `M(x) = R_left*x - sum(P*(x-a)) - sum(w*(x-start)^2/2)`.
- Bending stress is
  `|M_max|_kip-in / Sx`.
- Deflection is obtained by integrating `M/EI` twice and enforcing support
  boundary conditions, with no E factor of 144.
- Steel self-weight is added as `weight_lb_ft / 1000 kips/ft` over the full
  span only; it is removed and excluded when the lumber material is selected.

**Overall: all nine specification cases pass their stated tolerances.**
