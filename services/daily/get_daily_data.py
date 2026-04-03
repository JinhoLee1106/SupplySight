from datetime import date
from dotenv import load_dotenv
from functools import reduce
import pandas as pd
import requests, os

load_dotenv(".env.loc")
st_louis_api_key = os.getenv("STLOUIS_API_KEY")

marine_api_url = "https://marine-api.open-meteo.com/v1/marine"
weather_api_url = "https://archive-api.open-meteo.com/v1/archive"
oil_api_url = "https://api.stlouisfed.org/fred/series/observations"

countries = {
    "india": (17.65, 83.35),
    "ecuador": (-2.2, -81.0),
    "indonesia": (-7.18, 112.75),
    "vietnam": (9.17, 104.8),
    "thailand": (13.45, 100.25),
}
 
def get_country_wave_height_and_temp_df(country: str, start_date: date, end_date: date) -> pd.DataFrame:
    params = {
        "latitude": countries.get(country)[0],
        "longitude": countries.get(country)[1],
        "hourly": ["sea_surface_temperature"],
        "daily": ["wave_height_max"],
        "start_date": str(start_date),
        "end_date": str(end_date),
        "timezone": "UTC"
    }

    response = requests.get(marine_api_url, params)

    if response.status_code == 200:
        data = response.json()

        df_daily_wave_height = pd.DataFrame(data["daily"])
        df_daily_wave_height["time"] = pd.to_datetime(df_daily_wave_height["time"])

        df_hourly_temp = pd.DataFrame(data["hourly"])
        df_hourly_temp["time"] = pd.to_datetime(df_hourly_temp["time"])
        df_daily_temp = df_hourly_temp.set_index("time").resample("D").mean().reset_index()
        
        df_daily_wave_height_and_temp = pd.merge(df_daily_wave_height, df_daily_temp, on = "time", how = "inner")

        df_daily_wave_height_and_temp.rename(
            columns = {
                "time": "date",
                "wave_height_max": f"wave_height_{country}",
                "sea_surface_temperature": f"sea_surface_temp_{country}"
            },
            inplace = True
        )

        return df_daily_wave_height_and_temp


def get_country_wind_speed_and_precipitation_df(country: str, start_date: date, end_date: date) -> pd.DataFrame:
    params = {
        "latitude": countries.get(country)[0],
        "longitude": countries.get(country)[1],
        "start_date": str(start_date),
        "end_date": str(end_date),
        "daily": ["wind_speed_10m_max", "precipitation_sum"], 
        "timezone": "UTC"
    }

    response = requests.get(weather_api_url, params)

    if response.status_code == 200:
        data = response.json()
        df_country_wind_speed_and_precipitation = pd.DataFrame(data['daily'])
        df_country_wind_speed_and_precipitation["time"] = pd.to_datetime(df_country_wind_speed_and_precipitation["time"])

        df_country_wind_speed_and_precipitation.rename(
            columns = {
                "time": "date",
                "wind_speed_10m_max": f"wind_speed_{country}",
                "precipitation_sum": f"precipitation_{country}"
            },
            inplace = True
        )

        return df_country_wind_speed_and_precipitation


def get_oil_price_df(start_date: date, end_date: date) -> pd.DataFrame:
    params = {
        "series_id": "DCOILBRENTEU",
        "api_key": st_louis_api_key,
        "file_type": "json",
        "observation_start": str(start_date),
        "observation_end": str(end_date)
    }

    response = requests.get(oil_api_url, params)

    if response.status_code == 200:
        data = response.json()

        df_oil = pd.DataFrame(data['observations'])
        df_oil = df_oil[df_oil['value'] != '.'] 

        df_oil['date'] = pd.to_datetime(df_oil['date'])
        df_oil['oil_price'] = df_oil['value'].astype(float)
        df_oil = df_oil[['date', 'oil_price']]

        return df_oil


def get_daily_df(start_date: date, end_date: date) -> pd.DataFrame:
    df_list = []
    for country in countries.keys():
        df_country_daily_wave_height_and_temp = get_country_wave_height_and_temp_df(country, start_date, end_date)
        df_list.append(df_country_daily_wave_height_and_temp)

        df_country_wind_speed_and_precipitation = get_country_wind_speed_and_precipitation_df(country, start_date, end_date)
        df_list.append(df_country_wind_speed_and_precipitation)

    df_climate = reduce(lambda left, right: pd.merge(left, right, on = "date", how = "inner"), df_list)
    df_oil = get_oil_price_df(start_date, end_date)
    df_daily = pd.merge(df_climate, df_oil, on = "date", how = "left")

    return(df_daily)
