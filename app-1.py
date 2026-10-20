import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="Cake Assistant", page_icon="🎂", layout="centered")

COLOUR_RGB = {
    "Pink": (244, 143, 177), "White": (250, 250, 250), "Blue": (100, 160, 230),
    "Red": (220, 70, 70), "Gold": (225, 185, 70), "Purple": (160, 110, 210),
    "Brown": (120, 80, 60), "Yellow": (250, 220, 90),
}


# ---------- 2. DATA PROCESSING ----------
@st.cache_data
def load_data():
    df = pd.read_csv("cake_data.csv")
    df = df.drop_duplicates().dropna()          # clean data
    return df


CAT = ["flavour", "occasion", "style", "colour"]
NUM = ["size_kg", "price"]


def build_features(df):
    enc = pd.get_dummies(df[CAT])                # encoding -> numbers
    num = df[NUM].copy()
    num = (num - num.min()) / (num.max() - num.min() + 1e-9)   # scaling
    return pd.concat([enc, num], axis=1).astype(float)


# ---------- MODEL TRAINING (price prediction) ----------
@st.cache_resource
def train_price_model(df):
    X = pd.get_dummies(df[CAT + ["size_kg", "tiers"]])
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, df["price"])
    return model, list(X.columns)


def predict_price(model, cols, flavour, occasion, style, colour, size, tiers):
    row = pd.DataFrame([{"flavour": flavour, "occasion": occasion, "style": style,
                         "colour": colour, "size_kg": size, "tiers": tiers}])
    X = pd.get_dummies(row).reindex(columns=cols, fill_value=0)
    return int(model.predict(X)[0])


# ---------- 3. AI/ML RECOMMENDATION (cosine similarity) ----------
def recommend(df, feats, flavour, occasion, style, colour, size, budget, top_n=3):
    q = pd.DataFrame([{"flavour": flavour, "occasion": occasion, "style": style,
                       "colour": colour, "size_kg": size, "price": budget}])
    all_ = pd.concat([df[CAT + NUM], q], ignore_index=True)
    enc = pd.get_dummies(all_[CAT])
    num = all_[NUM].copy()
    num = (num - num.min()) / (num.max() - num.min() + 1e-9)
    mat = pd.concat([enc, num], axis=1).astype(float).values
    sims = cosine_similarity(mat[-1:], mat[:-1])[0]
    out = df.copy()
    out["match_%"] = (sims * 100).round(1)
    return out.sort_values("match_%", ascending=False).head(top_n)


# ---------- 4. DESIGN SUGGESTION ----------
def draw_cake(colour, style, occasion, tiers):
    W, H = 600, 600
    img = Image.new("RGB", (W, H), (255, 248, 240))
    d = ImageDraw.Draw(img)
    c = COLOUR_RGB.get(colour, (244, 143, 177))
    dark = tuple(max(0, v - 50) for v in c)
    d.rectangle([60, 520, 540, 540], fill=(200, 190, 180))          # plate
    tiers = int(max(1, min(3, tiers)))
    y = 520
    width = 360 if tiers > 1 else 320
    for t in range(tiers):
        h = 90
        x0, x1 = (W - width) // 2, (W + width) // 2
        d.rounded_rectangle([x0, y - h, x1, y], 18, fill=c, outline=dark, width=3)
        if style == "Drip":
            for x in range(x0 + 20, x1 - 10, 45):
                d.rounded_rectangle([x, y - h, x + 24, y - h + 40 + (x % 3) * 12], 10, fill=dark)
        elif style == "Floral":
            for x in range(x0 + 30, x1, 60):
                d.ellipse([x - 12, y - 55, x + 12, y - 31], fill=(255, 220, 230), outline=dark)
                d.ellipse([x - 4, y - 47, x + 4, y - 39], fill=(250, 200, 60))
        elif style == "Fondant":
            d.line([x0, y - h + 18, x1, y - h + 18], fill=(255, 255, 255), width=5)
            for x in range(x0 + 15, x1, 30):
                d.ellipse([x - 5, y - 20, x + 5, y - 10], fill=(255, 255, 255))
        elif style == "Photo":
            d.rectangle([x0 + 90, y - h + 15, x1 - 90, y - 15], outline=(255, 255, 255), width=4)
        elif style == "Theme":
            for x in range(x0 + 25, x1, 50):
                d.polygon([(x, y - 30), (x + 10, y - 55), (x + 20, y - 30)], fill=(255, 255, 255))
        y -= h
        width -= 80
    d.ellipse([285, y - 30, 315, y], fill=(220, 40, 60))            # cherry on top
    try:
        font = ImageFont.load_default(size=28)
    except TypeError:
        font = ImageFont.load_default()
    d.text((W // 2, 570), f"{occasion} • {style} • {colour}", fill=(90, 60, 50), font=font, anchor="mm")
    return img


# ---------- 1. USER INPUT + 5. FINAL OUTPUT ----------
df = load_data()
feats = build_features(df)
model, cols = train_price_model(df)

st.title("🎂 AI Cake Recommendation Assistant")
st.caption("Cosine-similarity recommendations + design suggestion + price prediction")

c1, c2 = st.columns(2)
flavour = c1.selectbox("Flavour", sorted(df["flavour"].unique()))
occasion = c2.selectbox("Occasion", sorted(df["occasion"].unique()))
style = c1.selectbox("Style", sorted(df["style"].unique()))
colour = c2.selectbox("Colour", sorted(df["colour"].unique()))
size = c1.select_slider("Size (kg)", options=[0.5, 1, 1.5, 2, 3, 4], value=1)
budget = c2.number_input("Budget (₹)", 300, 6000, 1000, step=100)

if st.button("Get my cake 🍰", use_container_width=True):
    recs = recommend(df, feats, flavour, occasion, style, colour, size, budget)
    tiers = 1 if size <= 2 else 2
    price = predict_price(model, cols, flavour, occasion, style, colour, size, tiers)

    st.subheader("Top recommendations")
    for _, r in recs.iterrows():
        st.write(f"**{r['name']}** — {r['flavour']}, {r['size_kg']} kg, "
                 f"₹{r['price']}  (match {r['match_%']}%)")

    st.subheader("Design suggestion")
    st.image(draw_cake(colour, style, occasion, tiers), use_container_width=True)

    st.subheader("Final output")
    st.success(f"Recommended: {flavour} {style} cake, {size} kg, {colour} theme "
               f"for {occasion}.  Estimated price: ₹{price}")
    if price > budget:
        st.warning("Estimated price is above your budget. Try a smaller size or the Minimalist style.")
