from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pandas as pd
import psycopg2
import os, sys


load_dotenv(".env.loc")

db_host = os.getenv("POSTGRES_HOST")
db_username = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")

def run_demo(recent: int, total: int):

    today_date = datetime.now(tz = timezone.utc).date()
    recent_earlist_date = today_date - timedelta(days = recent)
    total_earliest_date = today_date - timedelta(days = total)
    
    db_params = {
        "host" : db_host,
        "database" : db_name,
        "user" : db_username,
        "password" : db_password
    }

    conn = psycopg2.connect(**db_params)

    postgres_url = f"postgresql://{db_username}:{db_password}@{db_host}:5432/{db_name}"
    engine = create_engine(postgres_url)

    query = f"""
        SELECT * from dates_shrimp
        WHERE date BETWEEN \'{total_earliest_date}\' AND \'{today_date}\'
        ORDER BY date ASC
    """

    df_full = pd.read_sql(text(query), con = engine)
    df_full["date"] = pd.to_datetime(df_full["date"])
    df_full = df_full.drop("sentiment_score", axis = 1) # not implemented yet

    if 'conn' in locals():
        conn.close()
    if 'engine' in locals():
        engine.dispose()

    df_partial = df_full[df_full["date"].between(str(recent_earlist_date), str(today_date))]

    df_full_stats = df_full.drop("date", axis = 1).agg(["mean", "std"])
    df_partial_stats = df_partial.drop("date", axis = 1).agg(["mean"])

    df_partial_stats_T = df_partial_stats.T
    df_partial_stats_T.rename(columns = {"mean": "val"}, inplace = True)

    df_compare = pd.merge(df_full_stats.T, df_partial_stats_T, how = "inner", left_index=True, right_index=True)

    rename_dict = {
            "sea_surface_temp_india" : "sea_surface_temp_india (°C)",
            "sea_surface_temp_ecuador" : "sea_surface_temp_ecuador (°C)",
            "sea_surface_temp_indonesia" : "sea_surface_temp_indonesia (°C)",
            "sea_surface_temp_vietnam" : "sea_surface_temp_vietnam (°C)",
            "sea_surface_temp_thailand" : "sea_surface_temp_thailand (°C)",
            "precipitation_india" : "precipitation_india (mm)",
            "precipitation_ecuador" : "precipitation_ecuador (mm)",
            "precipitation_indonesia" : "precipitation_indonesia (mm)",
            "precipitation_vietnam" : "precipitation_vietnam (mm)",
            "precipitation_thailand" : "precipitation_thailand (mm)",
            "wind_speed_india" : "wind_speed_india (km/h)",
            "wind_speed_ecuador" : "wind_speed_ecuador (km/h)",
            "wind_speed_indonesia" : "wind_speed_indonesia (km/h)",
            "wind_speed_vietnam" : "wind_speed_vietnam (km/h)",
            "wind_speed_thailand" : "wind_speed_thailand (km/h)",
            "wave_height_india" : "wave_height_india (m)",
            "wave_height_ecuador" : "wave_height_ecuador (m)",
            "wave_height_indonesia" : "wave_height_indonesia (m)",
            "wave_height_vietnam" : "wave_height_vietnam (m)",
            "wave_height_thailand" : "wave_height_thailand (m)",
            "oil_price" : "oil_price ($)"
        }

    df_full_stats.rename(columns = rename_dict, inplace = True)
    df_partial_stats.rename(columns = rename_dict, inplace = True)

    print(f"\n{total}-day stats (since {total_earliest_date}):")
    print(df_full_stats.T)
    print(f"\n\n{recent}-day stats (since {recent_earlist_date}):")
    print(df_partial_stats.T)
    print("\n")

    for index, row in df_compare.iterrows():
        try:
            z_score = (row["val"] - row["mean"]) / row["std"]
            if abs(z_score) > 1:
                print(f"{'!' * round(abs(z_score))}\t {index} is {abs(round(z_score, 2))} standard deviations {'above' if z_score > 0 else 'below'} the average")
        
        except Exception:
            continue
    print("\n")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        run_demo(int(sys.argv[1]), int(sys.argv[2]))
        
    else:
        print("Invalid input")