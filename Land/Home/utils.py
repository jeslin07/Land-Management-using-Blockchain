import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
import os
from django.conf import settings

class LandPricePrediction:
    def __init__(self):
        self.cat_model = None
        self.lgb_model = None
        self.meta_model = None
        self.data = None
        self.load_models()
        
    def load_models(self):
        models_dir = os.path.join(settings.BASE_DIR, "models")
        
        # Load CatBoost model
        self.cat_model = CatBoostRegressor()
        self.cat_model.load_model(os.path.join(models_dir, "final_catboost.cbm"))
        
        # Load LightGBM and meta models
        self.lgb_model = joblib.load(os.path.join(models_dir, "final_lgb.pkl"))
        self.meta_model = joblib.load(os.path.join(models_dir, "meta_ridge.pkl"))

        # Load data
        data_path = os.path.join(settings.BASE_DIR, "land_cleaned.csv")
        self.data = pd.read_csv(data_path)
        
        # Set categorical types and lowercase text for matching
        for col in ["district", "locality", "location"]:
            if col in self.data.columns:
                self.data[col] = self.data[col].astype("category")
        
        self.data["district"] = self.data["district"].str.lower()
        self.data["locality"] = self.data["locality"].str.lower()
    
    def get_districts(self):
        if self.data is not None:
            return sorted(self.data["district"].unique())
        return []
    
    def get_localities(self, district):
        if self.data is not None and district:
            district = district.lower()
            localities = self.data[self.data["district"] == district]["locality"].unique()
            return sorted(localities)
        return []
    
    def predict_price(self, district, locality):
        district = district.strip().lower()
        locality = locality.strip().lower()
        
        subset = self.data[(self.data["district"] == district) & (self.data["locality"] == locality)]
        if subset.empty:
            raise ValueError(f"No records found for district='{district}', locality='{locality}'")
        
        avg_cents = subset["cents"].mean()
        example = {
            "district": district,
            "locality": locality,
            "location": "Unknown",
            "area_sqft": subset["area_sqft"].mean(),
            "cents": avg_cents,
            "loc_mean_price": subset["price_num"].mean(),
            "dist_mean_price": self.data[self.data["district"] == district]["price_num"].mean(),
            "loc_count": len(subset),
            "dist_count": len(self.data[self.data["district"] == district]),
            "price_per_cent_from_price": (subset["price_num"] / subset["cents"]).mean(),
        }
        
        features = [
            "district", "locality", "location",
            "area_sqft", "cents",
            "loc_mean_price", "dist_mean_price",
            "loc_count", "dist_count",
            "price_per_cent_from_price"
        ]
        
        X_example = pd.DataFrame([example], columns=features)
        for col in ["district", "locality", "location"]:
            if col in X_example.columns:
                X_example[col] = X_example[col].astype("category")
        
        pred_cb_log = self.cat_model.predict(X_example)
        pred_lgb_log = self.lgb_model.predict(X_example)
        
        meta_features = np.vstack([pred_cb_log, pred_lgb_log]).T
        pred_meta_log = self.meta_model.predict(meta_features)
        pred_meta_real = np.expm1(pred_meta_log)
        
        pred_price_total = pred_meta_real[0]
        pred_price_per_cent = pred_price_total / avg_cents if avg_cents > 0 else None
        
        return {
            "total_price": pred_price_total,
            "price_per_cent": pred_price_per_cent,
            "avg_cents": avg_cents,
            "district": district.title(),
            "locality": locality.title(),
        }

# Singleton predictor instance
predictor = LandPricePrediction()
