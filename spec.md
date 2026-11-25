# Beam Designer

## Platform
A cross-platform desktop engineering application written in Python using
Tkinter and Tkinter's themed widgets (`ttk`). It uses a native Tk window,
controls, file dialogs, drawing canvas, and print/save workflow. The application
is self-contained and requires no web browser or external runtime framework.

## Purpose
A beam design tool for engineers and students. The user sets up a beam,
places loads on it, and picks a steel or lumber section. The app shows the
shear, moment, and deflection diagrams and checks whether the beam is strong
and stiff enough, updating immediately as any input changes.

## Users
A civil engineering student checking a homework beam, or an engineer sizing a
floor beam or deck joist.

## Desktop Interface
- Open in a native Tkinter window with an example already loaded: a 20 ft
  simply supported W12x26 with a 1 kip/ft uniform load over the full span.
- Provide a File menu with Open and Save options. Open and Save use native
  Tkinter file dialogs and JSON files.
- Save support type, span, material, section, deflection limit, self-weight
  setting, point loads, and uniform loads. Opening restores those inputs,
  recalculates, and redraws immediately.
- Report invalid or unreadable design files with a clear dialog and leave the
  current design unchanged.
- Use `ttk` themed controls for consistency on Windows, macOS, and Linux.
- Place inputs in a left-hand panel and the beam, diagrams, and checks in a
  right-hand results area. Arrange panels vertically on narrow windows.
- Use a light background, white panels, soft borders, one accent color, and a
  clear, modern system font.
- Use Tkinter scales and spin/entry controls for numeric values. Keep the span
  slider and number entry synchronized.
- Use a `Canvas` widget for the beam drawing, shear, moment, and deflection
  diagrams.
- Store layout dimensions in logical pixels and redraw all canvas content on
  resize or input change.

## Inputs
- Support type: Simply supported or Cantilever (fixed at the left end).
- Span: 4 to 40 ft.
- Loads, listed in an editable panel:
  - Point loads: magnitude (kips, downward positive) and position (ft).
  - Uniform loads: magnitude (kips/ft) and start and end positions (ft).
  - `Add point load` and `Add uniform load` buttons.
  - Point loads may be dragged on the beam drawing and snap to 0.25 ft.
  - Point-load positions are restricted to 0 through the span.
  - Uniform-load endpoints are clamped to 0 and the span. If start exceeds end,
    swap the endpoints.
  - Reject negative point-load and uniform-load magnitudes.
- Material and section:
  - Steel W-shapes use E = 29,000 ksi and allowable bending stress
    Fb = 30 ksi.
  - Douglas Fir-Larch No. 2 lumber uses E = 1,600 ksi and allowable bending
    stress Fb = 0.900 ksi.
  - The material control is a dropdown. The section control contains only
    sections for the selected material.
- Deflection limit: L/240 or L/360, defaulting to L/360.
- Steel beam self-weight is optional and off by default. When enabled, include
  the selected steel section's tabulated weight as a downward uniform load over
  the full span.
- Switching to lumber disables and hides or clearly disables the steel
  self-weight control.

## Steel Sections
| Section | Ix (in^4) | Sx (in^3) | Weight (lb/ft) |
|---------|-----------|-----------|----------------|
| W8x10   | 30.8      | 7.81      | 10 |
| W10x12  | 53.8      | 10.9      | 12 |
| W12x26  | 204       | 33.4      | 26 |
| W14x22  | 199       | 29.0      | 22 |
| W16x26  | 301       | 38.4      | 26 |
| W18x35  | 510       | 57.6      | 35 |
| W21x44  | 843       | 81.6      | 44 |
| W24x55  | 1350      | 114       | 55 |

## Lumber Sections
| Section | Ix (in^4) | Sx (in^3) |
|---------|-----------|-----------|
| 2x8     | 47.63     | 13.14     |
| 2x10    | 98.93     | 21.39     |
| 2x12    | 177.98    | 31.64     |

## Calculations
- Perform reactions from statics. Upward reactions are positive.
- Use upward reaction minus downward loads to the left for positive shear.
  Sagging moment is positive; hogging moment is negative.
- Cantilevers are fixed at x = 0 and free at x = L. Report the fixed-end
  reaction moment as a positive magnitude while plotting its negative moment.
- Sample shear and moment at 0.25 ft or finer and at every support, load point,
  and uniform-load endpoint. Include both sides of shear discontinuities.
- Integrate moment twice for exact deflection using:
  - y = 0 at both supports for a simply supported beam.
  - y = 0 and slope = 0 at the fixed end for a cantilever.
- Treat downward deflection as positive.
- Find exact deflection extrema at support/boundary endpoints and locations
  where slope is zero. If maxima are equal, report the leftmost location.
- Calculate bending stress as `fb = |M_max| * 12 / Sx` in ksi.
- The bending check passes when `fb <= Fb`.
- The deflection check passes when `|y_max| <= L/240 or L/360`, with L in inches.
- When steel self-weight is enabled, add it to the internal general load model
  as a synthetic full-span uniform load of section weight / 1000 kips/ft.
  Do not add it to the editable uniform-load list.
- Apply tabulated steel candidate weights, Ix, and Sx together when testing
  section candidates.
- `Use lightest passing` changes only the section selection. For steel, choose
  the lightest passing section; ties go to the larger Ix. For lumber, choose
  the first passing table entry. Display a clear message if none passes.
- Use full precision internally. Use kip, ft, and kip-ft units in the interface;
  use inch lengths and kips for calculations.
- Use E directly in kip/in^2: 29,000 for steel and 1,600 for lumber. Do not
  multiply E by 144.

## Display and Updates
- Draw the beam, supports, load arrows, reactions, and three aligned diagrams:
  shear, moment, and deflection.
- Uniform loads appear as a row of small arrows. Steel self-weight appears in
  the drawing only when enabled.
- Scale beam and diagram x positions to the same span scale.
- Label exact maximum shear, moment, and absolute deflection values and their
  locations.
- Moving the mouse over a diagram shows a vertical guide across all diagrams
  and reads V, M, and y at that x.
- Show two check cards: Bending and Deflection. Each card displays actual value,
  allowable value, utilization bar, and PASS or FAIL.
- Bar colors are green below 70%, amber from 70% through 100%, and red above
  100%. Exactly 100% passes.
- Hovering a check card may show its formula.
- Recalculate and redraw immediately after every input or selection change.
- Show reactions, shear, moment, and locations to two decimal places.
  Show bending stress to two decimals and deflection to three decimals in inches.
  Do not round values before comparisons.

## Desktop Report
- Provide `Print / Save Report` actions using Tkinter-native dialog and printing
  or PDF-export capabilities. The implementation must not require a web
  browser or external Python dependency.
- Generate a clean US Letter portrait report containing:
  - report title and generated date
  - support type and span
  - deflection limit
  - material and section properties
  - point and uniform loads
  - steel self-weight status and derived kips/ft
  - support reactions
  - maximum shear, moment, and deflection with locations
  - beam, shear, moment, and deflection diagrams
  - bending and deflection checks
  - recommended lightest passing section
  - educational-use disclaimer
- Report values must come from current inputs and unrounded calculation state.

## Validation
1. Simply supported, 20 ft, W12x26, uniform 1 kip/ft over full span:
   reactions 10 k each; max shear 10 k; max moment 50.0 kip-ft at 10 ft;
   fb = 17.96 ksi; max deflection 0.609 in at 10 ft; L/360 = 0.667 in;
   both checks pass.
2. Simply supported, 20 ft, W12x26, point load 10 k at 5 ft:
   reactions 7.5 k left and 2.5 k right; max moment 37.5 kip-ft at 5 ft;
   fb = 13.47 ksi; max deflection 0.340 in at 8.82 ft.
3. Cantilever, 10 ft, W12x26, point load 5 k at free end:
   reaction 5 k and fixed-end moment 50 kip-ft; deflection 0.487 in at free end;
   L/360 = 0.333 in, so deflection fails.
4. Simply supported, 12 ft, 2x10, uniform 0.05 kip/ft:
   max moment 0.90 kip-ft; fb = 0.505 ksi; max deflection 0.147 in;
   both pass.
5. Simply supported, 20 ft, W12x26, no external load, self-weight on:
   0.026 kips/ft; reactions 0.26 k each; moment 1.30 kip-ft at 10 ft;
   stress 0.467 ksi; deflection 0.016 in.
6. Simply supported, 20 ft, W12x26, 1 kip/ft external uniform load,
   self-weight on: combined load 1.026 kips/ft; reactions 10.26 k each;
   moment 51.30 kip-ft at 10 ft; stress 18.43 ksi; deflection 0.624 in.
7. Cantilever, 10 ft, W12x26, no external load, self-weight on:
   0.026 kips/ft; reaction 0.26 k; fixed-end moment 1.30 kip-ft;
   deflection 0.009 in at free end.
8. Section change with self-weight on and no external load:
   W12x26 gives 1.30 kip-ft, 0.467 ksi stress, and 0.016 in deflection.
   W10x12 gives 0.60 kip-ft, 0.661 ksi stress, and 0.028 in deflection.
9. Switching to lumber turns self-weight off. A 12 ft simply supported 2x10
   with 0.05 kip/ft external uniform load retains its no-self-weight result.

Use 0.001 in for deflection, 0.01 ksi for stress, and 0.01 ft for location
tolerances. Flag discrepancies rather than forcing results to match.

## Out of Scope
- Lumber self-weight
- Shear stress
- Lateral-torsional buckling
- Load combinations
- Continuous beams
