import os
import json
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
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
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    wape = float(np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)))
    return {'MAE': mae, 'RMSE': rmse, 'WAPE': wape, 'ACC_1_minus_WAPE': 1 - wape}

train_df = pd.read_csv(train_path)
test_df = pd.read_csv(test_path)

X_train = train_df[feature_cols].fillna(0)
y_train = train_df['target_sales'].fillna(0)
X_test = test_df[feature_cols].fillna(0)
y_test = test_df['target_sales'].fillna(0)

baseline_pred = X_test['sales'].to_numpy()
baseline_m = metrics(y_test, baseline_pred)

params = {
    'objective': 'mae',
    'n_estimators': 1200,
    'learning_rate': 0.03,
    'num_leaves': 63,
    'max_depth': -1,
    'subsample': 0.8,
    'subsample_freq': 1,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.0,
    'reg_lambda': 1.0,
    'random_state': 42,
    'n_jobs': -1,
}

model = lgb.LGBMRegressor(**params)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    eval_metric='l1',
    callbacks=[lgb.early_stopping(100), lgb.log_evaluation(0)]
)

pred = model.predict(X_test)
pred = np.maximum(pred, 0.0)
lgbm_m = metrics(y_test, pred)

fi = pd.DataFrame({'feature': feature_cols, 'importance': model.feature_importances_}).sort_values('importance', ascending=False)

pred_df = test_df.copy()
pred_df['lgbm_predicted_target_sales'] = pred
pred_df['naive_predicted_target_sales'] = baseline_pred
pred_path = os.path.join(out_dir, 'lgbm_test_predictions.csv')
pred_df.to_csv(pred_path, index=False, encoding='utf-8-sig')

model_path = os.path.join(out_dir, 'lgbm_product_nextday_model.pkl')
joblib.dump(model, model_path)

summary = {
    'train_rows': int(len(train_df)),
    'test_rows': int(len(test_df)),
    'feature_cols': feature_cols,
    'lgbm_params': params,
    'best_iteration_': int(model.best_iteration_ or params['n_estimators']),
    'lgbm_metrics': lgbm_m,
    'baseline_metrics': baseline_m,
    'lgbm_better_than_baseline': {
        'MAE': bool(lgbm_m['MAE'] < baseline_m['MAE']),
        'RMSE': bool(lgbm_m['RMSE'] < baseline_m['RMSE']),
        'WAPE': bool(lgbm_m['WAPE'] < baseline_m['WAPE']),
        'ACC': bool(lgbm_m['ACC_1_minus_WAPE'] > baseline_m['ACC_1_minus_WAPE'])
    },
    'top20_feature_importance': fi.head(20).to_dict(orient='records'),
    'predictions_path': pred_path,
    'model_path': model_path
}

summary_path = os.path.join(out_dir, 'lgbm_compare_summary.json')
with open(summary_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(json.dumps(summary, ensure_ascii=False, indent=2))
print('summary_path=', summary_path)
