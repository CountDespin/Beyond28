import copy
import importlib
import math
import sys

import pandas as pd
import streamlit as st

st.set_page_config(page_title="PCOS Predictor", page_icon="", layout="centered")

# sample data, DO NOT EDIT, it will be calculated with averages anyway (except important ones)
SAMPLE_PATIENT = {
    'Age (yrs)': 18,
    'Weight (Kg)': 70,
    'Height(Cm)': 160,
    'BMI': 27.34,
    'Blood Group': 11,
    'Pulse rate(bpm)': 76,
    'RR (breaths/min)': 18,
    'Hb(g/dl)': 12.5,
    'Cycle(R/I)': 4,
    'Cycle length(days)': 35,
    'Marraige Status (Yrs)': 2.0,
    'Pregnant(Y/N)': 0,
    'No. of aborptions': 0,
    'I   beta-HCG(mIU/mL)': 0.5,
    'II    beta-HCG(mIU/mL)': 0.5,
    'FSH(mIU/mL)': 5.5,
    'LH(mIU/mL)': 12.0,
    'FSH/LH': 0.46,
    'Hip(inch)': 38,
    'Waist(inch)': 32,
    'Waist:Hip Ratio': 0.84,
    'TSH (mIU/L)': 2.5,
    'AMH(ng/mL)': 8.5,
    'PRL(ng/mL)': 15.0,
    'Vit D3 (ng/mL)': 20.0,
    'PRG(ng/mL)': 0.8,
    'RBS(mg/dl)': 95.0,
    'Weight gain(Y/N)': 1,
    'hair growth(Y/N)': 1,
    'Skin darkening (Y/N)': 1,
    'Hair loss(Y/N)': 0,
    'Pimples(Y/N)': 1,
    'Fast food (Y/N)': 1.0,
    'Reg.Exercise(Y/N)': 0,
    'BP _Systolic (mmHg)': 120,
    'BP _Diastolic (mmHg)': 80,
    'Follicle No. (L)': 12,
    'Follicle No. (R)': 14,
    'Avg. F size (L) (mm)': 18.0,
    'Avg. F size (R) (mm)': 19.0,
    'Endometrium (mm)': 9.0,
}

# (Y/N) yes or no, = 1 / 0
# (R/I) regular or irregular
exclude_columns = [
    'Age (yrs)',
    'Pimples(Y/N)',
    'Reg.Exercise(Y/N)',
    #'Follicle No. (R)',
    #'Follicle No. (L)',
    'Fast food (Y/N)',
    'Cycle length(days)',
    'Cycle(R/I)',
    #'AMH(ng/mL)',
    'Weight gain(Y/N)',
    'Skin darkening (Y/N)',
    'BMI',
    #'Weight (Kg)',
    #'Height(Cm)',
    'Hair loss(Y/N)',
    #'RBS(mg/dl)'
]

# Encoding of Cycle(R/I): must match the training data.
# Your sample uses 4 for irregular -> raw Kaggle encoding (2 = regular, 4 = irregular).
# If your df['Cycle(R/I)'].unique() is [1, 0], change these to 1 and 0.
CYCLE_REGULAR_VALUE = 2
CYCLE_IRREGULAR_VALUE = 4


NUMERIC_FIELDS = {
    "Age (yrs)": dict(label="Age (years)", min=10, max=60, default=25, step=1,
                      help="Patient age, between 10 and 60."),
    "Cycle length(days)": dict(label="Cycle length (days)", min=1, max=90,
                               default=5, step=1, help="Cycle length in days."),
    "BMI": dict(label="BMI", min=10.0, max=60.0, default=22.0, step=0.1,
                help="Body mass index (kg/m²)."),
}

YES_NO_LABELS = {
    "Pimples(Y/N)": "Pimples / acne",
    "Reg.Exercise(Y/N)": "Regular exercise",
    "Fast food (Y/N)": "Frequent fast food",
    "Weight gain(Y/N)": "Recent weight gain",
    "Skin darkening (Y/N)": "Skin darkening",
    "Hair loss(Y/N)": "Hair loss",
}


def render_field(col: str) -> float:
    if col.endswith("(Y/N)"):
        choice = st.radio(YES_NO_LABELS.get(col, col), ["No", "Yes"],
                          horizontal=True, key=col)
        return 1.0 if choice == "Yes" else 0.0

    if col.endswith("(R/I)"):
        choice = st.radio("Cycle regularity", ["Regular", "Irregular"],
                          horizontal=True, key=col)
        return float(CYCLE_REGULAR_VALUE if choice == "Regular"
                     else CYCLE_IRREGULAR_VALUE)

    if col in NUMERIC_FIELDS:
        cfg = NUMERIC_FIELDS[col]
        is_int = isinstance(cfg["default"], int)
        return float(st.number_input(
            cfg["label"], min_value=cfg["min"], max_value=cfg["max"],
            value=cfg["default"], step=cfg["step"],
            format="%d" if is_int else "%.1f", help=cfg["help"], key=col,
        ))

    return float(st.number_input(col, value=0.0, key=col))


def validate(values: dict) -> list[str]:
    errors = []
    for key, value in values.items():
        if value is None or (isinstance(value, float) and math.isnan(value)):
            errors.append(f"Field '{key}' is not valid.")
    if not (10 <= values.get("BMI", 22) <= 60):
        errors.append("BMI must be between 10 and 60.")
    if not (10 <= values.get("Age (yrs)", 25) <= 60):
        errors.append("Age must be between 10 and 60 years.")
    if values.get("Cycle length(days)", 5) < 1:
        errors.append("Cycle length must be at least 1 day.")
    return errors


def run_model_py():
    """Re-execute model.py from scratch (retrains every time)."""
    sys.modules.pop("model", None)
    importlib.invalidate_caches()
    return importlib.import_module("model")

st.title("PCOS Predictor")
st.caption("Demo tool based on machine learning. It is not a medical diagnosis.")

with st.form("pcos_form"):
    st.subheader("Patient data")
    values = {}
    ui_cols = st.columns(2)
    for i, col in enumerate(exclude_columns):
        with ui_cols[i % 2]:
            values[col] = render_field(col)
    submitted = st.form_submit_button("Predict", type="primary",
                                      use_container_width=True)

if submitted:
    errors = validate(values)
    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    try:
        with st.spinner("Training the model and computing the prediction..."):
            m = run_model_py()
            df, model, scaler = m.df, m.model, m.scaler
            feature_names, predict_pcos = m.feature_names, m.predict_pcos

            new_patient = copy.deepcopy(SAMPLE_PATIENT)

            means = df.mean(numeric_only=True)
            for column in new_patient:
                if column not in exclude_columns and column in means.index:
                    new_patient[column] = means[column]

            for col in exclude_columns:
                new_patient[col] = values[col]

            prediction, probability = predict_pcos(
                model, scaler, feature_names, copy.deepcopy(new_patient)
            )
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.stop()

    prob = float(probability)
    if prob > 1:
        prob /= 100
    prob = min(max(prob, 0.0), 1.0)

    st.divider()
    st.subheader("Result")

    c1, c2 = st.columns(2)
    c1.metric("PCOS prediction", str(prediction))
    if prediction == "Yes":
        c2.metric("Confidence", f"{prob * 100:.2f}%")
    #st.progress(prob)

    if prediction == "Yes":
        st.warning(
            "**The patient shows indicators of PCOS.**\n\n"
            "Recommendation: consult a healthcare professional for a proper diagnosis."
        )
    else:
        st.success(
            "**The patient shows low indicators of PCOS.**\n\n"
            "Recommendation: continue regular health monitoring."
        )

    with st.expander("Debug: full patient sent to the model"):
        st.dataframe(pd.DataFrame([new_patient]).T.rename(columns={0: "value"}))
