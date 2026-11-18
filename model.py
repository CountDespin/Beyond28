import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import math
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, classification_report, roc_auc_score, roc_curve, precision_recall_curve)
from imblearn.over_sampling import SMOTE
from imblearn.combine import SMOTETomek
from sklearn.ensemble import StackingClassifier
from sklearn.ensemble import AdaBoostClassifier
import warnings
warnings.filterwarnings('ignore')

filepath = "data/PCOS_data_without_infertility.xlsx"

df = pd.read_excel(filepath,sheet_name="Full_new")

df['II    beta-HCG(mIU/mL)'] = pd.to_numeric(df['II    beta-HCG(mIU/mL)'],errors='coerce')
df['AMH(ng/mL)'] = pd.to_numeric(df['AMH(ng/mL)'],errors='coerce')

df.drop('Unnamed: 44',axis=1,inplace=True)
correlation_with_target = df.corr()['PCOS (Y/N)'].abs().sort_values(ascending=False)

def load_and_preprocess_data(filepath):
    """Load and preprocess the PCOS dataset"""
    print("Loading data...")
    
    # Check file extension and load accordingly
    if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
        df = pd.read_excel(filepath, sheet_name='Full_new')
        print("Loaded Excel file (sheet: Full_new)")
    elif filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
        print("Loaded CSV file")
    else:
        raise ValueError("File must be .xlsx, .xls, or .csv format")
    
    print(f"Initial dataset shape: {df.shape}")
    print(f"\nColumn names found:")
    print(df.columns.tolist())
    
    # Drop unnecessary columns
    cols_to_drop = ['Sl. No', 'Patient File No.', 'Unnamed: 44', 
                    'Sl.No', 'Patient File No', 'PCOS']
    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns], errors='ignore')
    
    # Standardize column names - remove extra spaces
    df.columns = df.columns.str.strip()
    
    
    # Convert all object columns to numeric where possible
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Handle missing values
    # For numerical columns, fill with median
    numerical_cols = df.select_dtypes(include=[np.number]).columns
    for col in numerical_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna(df[col].median(), inplace=True)
    
    print(f"\nFinal dataset shape: {df.shape}")
    print(f"Missing values after preprocessing: {df.isnull().sum().sum()}")
    
    return df

def create_engineered_features(df):
    """Create additional features based on domain knowledge - adaptive to available columns"""
    df_eng = df.copy()
    
    # Check which columns are available
    cols = df_eng.columns.tolist()
    
    # Hormonal ratios (if available)
    if 'LH(mIU/mL)' in cols and 'FSH(mIU/mL)' in cols:
        df_eng['LH_FSH_ratio'] = df_eng['LH(mIU/mL)'] / (df_eng['FSH(mIU/mL)'] + 1e-6)
    
    # Symptom aggregation (if available)
    symptom_cols = ['Weight gain(Y/N)', 'hair growth(Y/N)', 'Skin darkening (Y/N)', 
                    'Hair loss(Y/N)', 'Pimples(Y/N)']
    available_symptoms = [col for col in symptom_cols if col in cols]
    if available_symptoms:
        df_eng['symptom_count'] = df_eng[available_symptoms].sum(axis=1)
    
    # Follicle features (if available)
    if 'Follicle No. (L)' in cols and 'Follicle No. (R)' in cols:
        df_eng['total_follicles'] = df_eng['Follicle No. (L)'] + df_eng['Follicle No. (R)']
        df_eng['follicle_asymmetry'] = abs(df_eng['Follicle No. (L)'] - df_eng['Follicle No. (R)'])
    
    
    if 'Avg. F size (L) (mm)' in cols and 'Avg. F size (R) (mm)' in cols:
        df_eng['avg_follicle_size'] = (df_eng['Avg. F size (L) (mm)'] + df_eng['Avg. F size (R) (mm)']) / 2
    
    # Lifestyle score (if available)
    if 'Fast food (Y/N)' in cols and 'Reg.Exercise(Y/N)' in cols:
        df_eng['lifestyle_risk'] = df_eng['Fast food (Y/N)'] - df_eng['Reg.Exercise(Y/N)']
    
    # BMI categories (if available)
    if 'BMI' in cols:
        df_eng['BMI_category'] = pd.cut(df_eng['BMI'], 
                                         bins=[0, 18.5, 25, 30, 100], 
                                         labels=[0, 1, 2, 3]).astype(int)
    
    # Waist-Hip ratio category (if available)
    if 'Waist:Hip Ratio' in cols:
        df_eng['WHR_risk'] = (df_eng['Waist:Hip Ratio'] > 0.85).astype(int)
    
    # Age categories (if available)
    if 'Age (yrs)' in cols:
        df_eng['age_group'] = pd.cut(df_eng['Age (yrs)'], 
                                      bins=[0, 20, 25, 30, 35, 100], 
                                      labels=[0, 1, 2, 3, 4]).astype(int)
    
    print(f"\nEngineered features created. New shape: {df_eng.shape}")
    
    return df_eng

def train_ensemble_model(X_train, y_train):
    """Train an ensemble of models for better performance"""
    
    # Individual models with optimized parameters
    lr = LogisticRegression(max_iter=2000, C=0.1, class_weight='balanced', random_state=42)
    
    rf = RandomForestClassifier(n_estimators=300, max_depth=6, 
                                 min_samples_split=6, min_samples_leaf=3,
                                 class_weight='balanced', oob_score=True, random_state=42)
    
    gb = GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, 
                                     max_depth=3, subsample=0.8, random_state=42)
    ada = AdaBoostClassifier(n_estimators=200, learning_rate=0.1, random_state=42)
    
    # Create voting classifier (soft voting for probability averaging)
    ensemble = StackingClassifier(
        estimators=[('rf', rf), ('gb', gb)],
        final_estimator=LogisticRegression(max_iter=2000)
    )
    
    print("Training ensemble model...")
    ensemble.fit(X_train, y_train)
    
    rf.fit(X_train, y_train)
    gb.fit(X_train, y_train)

    # Also train individual models for comparison
    models = {
        'Random Forest': rf,
        'Gradient Boosting': gb,
        'Ensemble': ensemble
    }
    
    return models

def evaluate_models(models, X_test, y_test):
    """Evaluate all models and return performance metrics"""
    results = {}
    
    for name, model in models.items():
        #if name != 'Ensemble':
        #    model.fit(X_test.iloc[:int(len(X_test)*0.8)], 
        #             y_test.iloc[:int(len(y_test)*0.8)])
        
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        
        results[name] = {
            'accuracy': accuracy_score(y_test, y_pred),
            'confusion_matrix': confusion_matrix(y_test, y_pred),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'roc_auc': roc_auc_score(y_test, y_prob)
        }
        
        print(f"\n{'='*50}")
        print(f"Model: {name}")
        print(f"{'='*50}")
        print(f"Accuracy: {results[name]['accuracy']:.4f}")
        print(f"ROC-AUC Score: {results[name]['roc_auc']:.4f}")
        print(f"\nConfusion Matrix:\n{results[name]['confusion_matrix']}")
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred))
    
    return results

"""def predict_pcos(model, scaler, feature_names, patient_data):
    
    #àPredict PCOS for a new patient
    
    #Parameters:
    #-----------
    #model : trained model
    #scaler : fitted StandardScaler
    #àfeature_names : list of feature names used in training
    #patient_data : dict with patient features
    
    #Returns:
    #--------
    #prediction : 'Yes' or 'No'
    #probability : probability of having PCOS
    #
    # Convert patient data to DataFrame
    patient_df = pd.DataFrame([patient_data])
    
    # Ensure all required features are present
    for feature in feature_names:
        if feature not in patient_df.columns:
            patient_df[feature] = 0
    
    # Select only the features used in training
    patient_df = patient_df[feature_names]
    
    # Scale the features
    patient_scaled = scaler.transform(patient_df)
    
    # Make prediction
    prediction = model.predict(patient_scaled)[0]
    probability = model.predict_proba(patient_scaled)[0][1]
    
    result = "Yes" if prediction == 1 else "No"
    
    return result, probability
"""

def predict_pcos(model, scaler, feature_names, patient_data):

    
    patient_df = pd.DataFrame([patient_data])

    patient_df = create_engineered_features(patient_df)

    patient_df = patient_df.reindex(
        columns=feature_names,
        fill_value=0
    )

    patient_df = patient_df.apply(pd.to_numeric, errors='coerce')

    patient_df = patient_df.fillna(0)

    # Scaling
    patient_scaled = scaler.transform(patient_df)

    prediction = model.predict(patient_scaled)[0]

    probability = model.predict_proba(patient_scaled)[0][1]

    result = "Yes" if prediction == 1 else "No"

    return result, probability


def main(filepath):
    """Main execution pipeline"""
    
    # Load and preprocess data
    df = load_and_preprocess_data(filepath)
    
    # Check if target column exists
    target_col = None
    possible_targets = ['PCOS (Y/N)', 'PCOS(Y/N)', 'PCOS', 'PCOS (Y/N)']
    for col in possible_targets:
        if col in df.columns:
            target_col = col
            break
    
    if target_col is None:
        raise ValueError(f"Target column not found! Available columns: {df.columns.tolist()}")
    
    print(f"\nUsing target column: '{target_col}'")
    
    # Feature engineering
    df_eng = create_engineered_features(df)
    
    # Separate features and target
    X = df_eng.drop(target_col, axis=1)
    y = df_eng[target_col]
    
    print(f"\nFeatures shape: {X.shape}")
    print(f"Available features: {X.columns.tolist()}")
        
    print(f"\nClass distribution:")
    print(y.value_counts())
    if len(y.value_counts()) > 1:
        print(f"Class balance: {y.value_counts()[1]/len(y)*100:.2f}% positive cases")
    
    # Check if we have enough features
    if X.shape[1] < 3:
        print("\n WARNING: Very few features available. Model performance may be limited.")
        print("Consider using the full dataset with all 44+ features for better results.")
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Handle class imbalance with SMOTE (only if we have multiple classes)
    if len(y.value_counts()) > 1:
        print("\nApplying SMOTE for class balancing...")
        smote_tomek = SMOTETomek(random_state=42)
        X_train_balanced, y_train_balanced = smote_tomek.fit_resample(X_train, y_train)
        
        print(f"Training set size after SMOTE: {X_train_balanced.shape}")
        print(f"Class distribution after SMOTE: {pd.Series(y_train_balanced).value_counts()}")
    else:
        X_train_balanced, y_train_balanced = X_train, y_train
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_balanced)
    X_test_scaled = scaler.transform(X_test)
    
    # Convert back to DataFrame for compatibility
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=X.columns)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=X.columns)
    y_train_balanced = pd.Series(y_train_balanced)
    
    # Train models
    models = train_ensemble_model(X_train_scaled, y_train_balanced)
    
    # Evaluate models
    results = evaluate_models(models, X_test_scaled, y_test)
    # Plot Train vs Test accuracy for overfitting check
    #plot_overfitting(models, X_train_scaled, y_train_balanced, X_test_scaled, y_test)

    
    # Select best model (Ensemble)
    best_model = models['Ensemble']
        # Feature importance (from Random Forest)
    if X.shape[1] >= 2:  # Only show importance if we have features
        rf_model = models['Random Forest']
        rf_model.fit(X_train_scaled, y_train_balanced)
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': rf_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\n" + "="*50)
        print("Top 15 Most Important Features:")
        print("="*50)
        print(feature_importance.head(15))
    
    return best_model, scaler, X.columns.tolist(), results



    # Train the model
model, scaler, feature_names, results = main(filepath)
    
    # Example: Predict for a new patient

new_patient = {
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
        'Endometrium (mm)': 9.0
    }
    
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
    'Hair loss(Y/N)'
    #'RBS(mg/dl)'
]

means = df.mean(numeric_only=True)

for column in new_patient:
    if column not in exclude_columns and column in means.index:
        new_patient[column] = means[column]

for i in exclude_columns:
    new_patient[i]=float(input(f"Insert {i}: "))

prediction, probability = predict_pcos(model, scaler, feature_names, new_patient)
    
print(f"\nPCOS Prediction: {prediction}")
print(f"Confidence: {probability*100:.2f}%")

if prediction == "Yes":
    print("\n⚠️ OH HELL NAW\nThe patient shows indicators of PCOS.")
    print("Recommendation: Consult with a healthcare professional for proper diagnosis.")
else:
    print("\n✓ The patient shows low indicators of PCOS.")
    print("Recommendation: Continue regular health monitoring.")
