import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests

#API temperature by key
def get_current_temperature(city, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['main']['temp']
    elif response.status_code == 401:
        st.error("Invalid API key. Please see https://openweathermap.org/faq#error401 for more info.")
        return None
    else:
        st.error("Failed to fetch data from OpenWeatherMap API.")
        return None

# Streamlit app
st.title("Temperature Analysis and Monitoring")
st.subheader("Upload historical temperature data or use default dataset")
use_default = st.button("Use Default Dataset")
if use_default:
    default_file_path = "temperature_data.csv"
    data = pd.read_csv(default_file_path)
    st.success("Default dataset loaded successfully!")
else:
    uploaded_file = st.file_uploader("Upload historical temperature data (CSV):", type=['csv'])
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        st.success("File uploaded successfully!")

if 'data' in locals():
    data['temperature_rolling_avg'] = (
        data.sort_values('timestamp')
        .groupby(['city', 'season'])['temperature']
        .transform(lambda x: x.rolling(window=30, min_periods=1).mean())
    )
    data_grouped = data.groupby(['city', 'season'], as_index=False).agg(
        temperature_avg=('temperature', 'mean'),
        temperature_std=('temperature', 'std'))
    data = data.merge(data_grouped, on=['city', 'season'], how='left')
    data['upper_bound'] = data['temperature_avg'] + 2 * data['temperature_std']
    data['lower_bound'] = data['temperature_avg'] - 2 * data['temperature_std']
    data['is_anomaly'] = ((data['temperature'] < data['lower_bound']) | 
                          (data['temperature'] > data['upper_bound'])).astype(int)
    selected_city = st.selectbox("Select a city:", data['city'].unique())
    city_data = data[data['city'] == selected_city].copy()
    if not city_data.empty:
        # descriptive statistics
        st.subheader("Descriptive Statistics")
        st.write(city_data[['temperature', 'temperature_rolling_avg']].describe())

        # Plot temperature time series with anomalies
        st.subheader("Temperature Time Series with Anomalies")
        plt.figure(figsize=(10, 6))
        plt.plot(city_data['timestamp'], city_data['temperature'], label='Temperature')
        plt.plot(city_data['timestamp'], city_data['temperature_rolling_avg'], label='30-Day Rolling Average', color='orange')
        anomalies = city_data[city_data['is_anomaly'] == 1]
        plt.scatter(anomalies['timestamp'], anomalies['temperature'], color='red', label='Anomalies')

        plt.xlabel("Date")
        plt.ylabel("Temperature (°C)")
        plt.legend()
        st.pyplot(plt)

        # Seasonal
        st.subheader(f"Seasonal Profiles for {selected_city}")
        seasonal_stats_city = city_data.groupby(['season']).agg(
            mean_temp=('temperature', 'mean'),
            std_temp=('temperature', 'std')
        ).reset_index()
        st.write(seasonal_stats_city)

        plt.figure(figsize=(8, 4))
        plt.bar(seasonal_stats_city['season'], seasonal_stats_city['mean_temp'], yerr=seasonal_stats_city['std_temp'], capsize=5)
        plt.xlabel("Season")
        plt.ylabel("Temperature (°C)")
        plt.title(f"Mean Temperature by Season for {selected_city}")
        st.pyplot(plt)

# API key input
st.subheader("Current Temperature Monitoring")
api_key = st.text_input("Enter your OpenWeatherMap API key:")
if api_key:
    if st.button("Merge Current Temperature"):
        if selected_city in data['city'].unique():
            city_data = data[data['city'] == selected_city].copy()
            current_temp = get_current_temperature(selected_city, api_key)
            if current_temp is not None:
                current_season = city_data['season'].iloc[-1]  # Assume last entry's season is current
                seasonal_stats = city_data.groupby('season').agg(
                    mean_temp=('temperature', 'mean'),
                    std_temp=('temperature', 'std')
                ).reset_index()
                season_stats = seasonal_stats[seasonal_stats['season'] == current_season]
                mean_temp = season_stats['mean_temp'].values[0]
                std_temp = season_stats['std_temp'].values[0]
                lower_bound = mean_temp - 2 * std_temp
                upper_bound = mean_temp + 2 * std_temp

                if lower_bound <= current_temp <= upper_bound:
                    st.success(f"The current temperature is within the normal range for the season.\n\n"
                               f"Temperature: {current_temp}°C\nNormal Range: {lower_bound:.2f}°C to {upper_bound:.2f}°C")
                else:
                    st.warning(f"The current temperature is outside the normal range for the season.\n\n"
                               f"Temperature: {current_temp}°C\nNormal Range: {lower_bound:.2f}°C to {upper_bound:.2f}°C")
