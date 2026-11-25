# Beam Designer

Beam Designer is a Python desktop app for analyzing simply supported beams and
cantilevers. It calculates reactions, shear, moment, and deflection; checks
bending and deflection limits; and recommends a lightest passing section.

## Requirements and installation

- Python 3.10 or newer with Tkinter/Tcl-Tk support
- No third-party Python packages are required; the app uses the Python standard
  library.

Install Python with Tkinter support for your operating system, then open a
terminal in this project folder. No `pip install` step is needed.

## Start the application

```bash
python3 app.py
```

## Save, open, and export

- Choose **File → Save** to save the current design as JSON, or **File → Open**
  to restore a saved design.
- Click **Export Results** to save the current beam's shear, moment, and
  deflection values along the span as a CSV file that can be opened in Excel.
- Click **Print / Save PDF** to create a US Letter portrait calculation sheet
  with beam inputs, loads, diagrams, results, design checks, and recommendation.

## Validation

Run the calculation test suite:

```bash
python3 -m unittest -v test_beam_calculations.py
```

Run all nine specification validation cases:

```bash
python3 02_validation/run_validation.py
```
