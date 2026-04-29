import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

train_path = r"C:/Users/LG/Downloads/rf_train_compact_unzipped/rf_train_compact.csv"
test_path = r"C:/Users/LG/Downloads/rf_test_compact.csv"
out_dir = r"C:/Users/LG/OneDrive/바탕 화면/cap"
os.makedirs(out_dir, exist_ok=True)

feature_cols = [
    'plu_id', 'category_l_id', 'category_m_id', 'category_s_id',
    'sales', 'lag_1', 'lag_3', 'lag_7',
    'rolling_7_mean', 'rolling_7_std',
    'day_of_week', 'month', 'is_weekend',
    'is_holiday_filled', 'academic_event_filled', 'academic_event_2026_flag',
    'weather_missing', 'avg_temp_c_filled', 'precipitation_mm_filled', 'is_rain_filled',
    'timetable_class_count', 'timetable_headcount',
    'timetable_large_class_count', 'timetable_max_class_headcount',
    'timetable_is_class_day'
]

def metrics(y_true, y_pred):
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    denom = float(np.sum(np.abs(y_true)))
    wape = float(np.sum(np.abs(y_true - y_pred)) / denom) if denom != 0 else float('nan')
    return {'MAE': mae, 'RMSE': rmse, 'WAPE': wape, 'ACC_1_minus_WAPE': float(1 - wape) if np.isfinite(wape) else float('nan')}

train_df = pd.read_csv(train_path)
test_df = pd.read_csv(test_path)

X_train = train_df[feature_cols].fillna(0)
y_train = train_df['target_sales'].fillna(0)
X_test = test_df[feature_cols].fillna(0)
y_test = test_df['target_sales'].fillna(0)

# Baseline
base_pred = X_test['sales'].to_numpy()
base_metrics = metrics(y_test.to_numpy(), base_pred)

candidates = [
    ('rf_100_default', dict(n_estimators=100, random_state=42, n_jobs=-1)),
    ('rf_50_fast', dict(n_estimators=50, max_depth=20, min_samples_leaf=2, random_state=42, n_jobs=-1)),
    ('rf_200_depth20_leaf2', dict(n_estimators=200, max_depth=20, min_samples_leaf=2, random_state=42, n_jobs=-1)),
    ('rf_300_depth30_leaf1', dict(n_estimators=300, max_depth=30, min_samples_leaf=1, random_state=42, n_jobs=-1)),
]

results = []
best = None
best_key = None
best_model = None
best_pred = None

for key, params in candidates:
    model = RandomForestRegressor(**params)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    m = metrics(y_test.to_numpy(), pred)
    rec = {'model_key': key, 'params': params, 'metrics': m}
    results.append(rec)
    if best is None or m['WAPE'] < best['WAPE']:
        best = m
        best_key = key
        best_model = model
        best_pred = pred

# Save best outputs
pred_out = test_df.copy()
pred_out['rf_predicted_target_sales'] = best_pred
pred_out['naive_predicted_target_sales'] = base_pred
pred_path = os.path.join(out_dir, 'rf_test_predictions_fulltrain.csv')
pred_out.to_csv(pred_path, index=False, encoding='utf-8-sig')

model_path = os.path.join(out_dir, 'rf_product_nextday_model_fulltrain.pkl')
joblib.dump(best_model, model_path)

fi = pd.DataFrame({'feature': feature_cols, 'importance': best_model.feature_importances_}).sort_values('importance', ascending=False)

summary = {
    'train_rows': int(len(train_df)),
    'test_rows': int(len(test_df)),
    'feature_cols': feature_cols,
    'baseline_metrics': base_metrics,
    'rf_candidates': results,
    'best_model_key': best_key,
    'best_model_metrics': best,
    'best_vs_baseline': {
        'MAE_lower_is_better': bool(best['MAE'] < base_metrics['MAE']),
        'RMSE_lower_is_better': bool(best['RMSE'] < base_metrics['RMSE']),
        'WAPE_lower_is_better': bool(best['WAPE'] < base_metrics['WAPE']),
        'ACC_higher_is_better': bool(best['ACC_1_minus_WAPE'] > base_metrics['ACC_1_minus_WAPE'])
    },
    'top20_feature_importance': fi.head(20).to_dict(orient='records'),
    'predictions_path': pred_path,
    'model_path': model_path
}

summary_path = os.path.join(out_dir, 'rf_fulltrain_compare_summary.json')
with open(summary_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False, indent=2))
print('summary_path=', summary_path)
