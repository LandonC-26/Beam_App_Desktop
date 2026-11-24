# Beam Designer

## Purpose
A native Python desktop beam design application built with Tkinter that
draws shear, moment, and deflection diagrams and checks bending strength
and stiffness.

## Default Example
- Simply supported beam
- 20 ft span
- W12×26 ASTM A992 steel section
- 1.0 kip/ft uniform load across the full span
- 24 ksi bending stress limit (conservative app default)
- L/360 deflection limit

## Inputs
- Beam type: simply supported or cantilever
- Clear span in feet
- One or more downward point loads, in kips, with position in feet
  measured from the left end
- A full-span uniform load, in kip/ft
- Material category: steel or lumber
- Steel W-shape or lumber nominal size
- Allowable bending stress in ksi or psi
- Deflection limit as a span ratio, with L/360 as the default
- Optional beam self-weight; off by default

## Calculations
- Sign convention: downward loads are positive in the loading model;
  shear and moment diagrams use structural engineering signs and are
  clearly labeled. Deflections are stored and displayed as downward
  positive values.
- Reactions, shear, and bending moment by superposition
- Maximum absolute shear and moment
- Elastic deflection at 101 evenly spaced stations using Euler-Bernoulli
  beam theory
- Steel bending stress: \(f_b = M/S_x\), with M in kip-inches
- Lumber bending stress uses the selected section modulus and allowable
  \(F_b\)
- Deflection check against the selected L/limit ratio
- A 20 ft simply supported W12×26 example with 1 kip/ft must calculate
  50.0 kip-ft maximum moment and approximately 0.609 in maximum deflection

## Outputs
- Beam and load sketch
- Shear, moment, and deflection diagrams
- Reactions
- Maximum moment and location
- Maximum deflection and location
- Bending stress and allowable stress
- Actual deflection and allowed deflection
- Separate pass/fail results and governing utilization ratios

## Save and Open
- A File menu provides Save and Open commands for JSON design files
- Save support type, span, material and section, deflection limit, allowable
  stress, uniform load, point loads, and self-weight setting
- Opening a design restores its saved inputs and recalculates the results
- Invalid or unsupported design files are reported without applying partial
  changes

## Export Results
- An Export CSV button saves the analysis stations as an Excel-compatible CSV
- Include position \(x\) in feet, shear \(V\) in kips, moment \(M\) in kip-ft,
  and downward-positive deflection in inches
- Export all 101 evenly spaced stations used in the analysis

## Look and feel
- Clean, professional Tkinter desktop interface
- Example beam preloaded when the app starts
- Neutral academic style with blue accents and clear units
- Resizable window with organized labels and input groups
- Embedded plots in the application window

## Validation
- Store source properties and hand-calculation assumptions in
  `01_data/beam_properties.csv`
- Store test cases in `02_validation/test_cases.csv`
- Document independent checks in `02_validation/validation.md`
- Required examples include simply supported uniform load, simply supported
  point load, cantilever end point load, cantilever uniform load, and the
  default W12×26 example

## Out of scope
- Continuous beams
- Buckling, lateral-torsional buckling, shear failure, and bearing
- Moving loads
- Variable uniform loads
- Connection design