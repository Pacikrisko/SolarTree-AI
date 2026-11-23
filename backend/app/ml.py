"""Real scikit-learn models trained on time series, initially synthetic DEMO data."""
from datetime import timedelta
import math
import numpy as np
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.metrics import mean_absolute_error


def features(r):
    hr = r.time.hour + r.time.minute / 60
    return [math.sin(2*math.pi*hr/24), math.cos(2*math.pi*hr/24), hr,
            r.temperature_c, r.humidity_pct]


def predict_power(readings, steps=6):
    data = sorted(readings, key=lambda r:r.time)
    if len(data) < 30:
        return {'points':[], 'mae_w':None, 'trained_samples':len(data), 'model':'Недостатъчно данни'}
    x=np.array([features(r) for r in data]); y=np.array([r.power_w for r in data])
    split=max(20, int(len(data)*.8))
    validation_model=RandomForestRegressor(n_estimators=45,min_samples_leaf=2,random_state=42,n_jobs=1)
    validation_model.fit(x[:split], y[:split])
    mae=round(float(mean_absolute_error(y[split:],validation_model.predict(x[split:]))),1)
    model=RandomForestRegressor(n_estimators=45,min_samples_leaf=2,random_state=42,n_jobs=1)
    model.fit(x,y)
    latest=data[-1]
    result=[]
    for i in range(1,steps+1):
        when=latest.time+timedelta(minutes=15*i)
        h=when.hour+when.minute/60
        # Future temperature/humidity unknown. Last readings serve as a simple assumption.
        xfuture=np.array([[math.sin(2*math.pi*h/24),math.cos(2*math.pi*h/24),h,
                           latest.temperature_c,latest.humidity_pct]])
        power=max(0,round(float(model.predict(xfuture)[0]),1))
        result.append({'time':when.isoformat()+'Z','power_w':power})
    return {'points':result,'mae_w':mae,'trained_samples':len(data),
            'model':'RandomForestRegressor','synthetic_data':all(r.source == 'simulation' for r in data),
            'disclaimer':'Прогнозата е експериментална, НЕ управлява оборудването. Измерванията може да са симулирани.'}


def detect_anomaly(history, new_reading):
    """IsolationForest anomaly detector for demonstration/analytics; NOT safety control."""
    if len(history) < 40:
        return False, 0.0
    def row(r):
        return [r.power_w,r.temperature_c,r.humidity_pct,r.h2_sensor_value,r.water_pct]
    baseline=np.array([row(r) for r in history[-100:]],dtype=float)
    current=np.array([row(new_reading)],dtype=float)
    model=IsolationForest(n_estimators=80,contamination=.04,random_state=42)
    model.fit(baseline)
    score=float(model.decision_function(current)[0])
    return bool(model.predict(current)[0] == -1),round(score,3)
