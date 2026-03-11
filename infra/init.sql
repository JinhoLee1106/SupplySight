CREATE TABLE dates_shrimp (
    date TIMESTAMP PRIMARY KEY,
    sea_surface_temp_india FLOAT,
    sea_surface_temp_ecuador FLOAT,
    sea_surface_temp_indonesia FLOAT,
    sea_surface_temp_vietnam FLOAT,
    sea_surface_temp_thailand FLOAT,
    precipitation_india FLOAT,
    precipitation_ecuador FLOAT,
    precipitation_indonesia FLOAT,
    precipitation_vietnam FLOAT,
    precipitation_thailand FLOAT,
    wind_speed_india FLOAT,
    wind_speed_ecuador FLOAT,
    wind_speed_indonesia FLOAT,
    wind_speed_vietnam FLOAT,
    wind_speed_thailand FLOAT,
    wave_height_india FLOAT,
    wave_height_ecuador FLOAT,
    wave_height_indonesia FLOAT,
    wave_height_vietnam FLOAT,
    wave_height_thailand FLOAT,
    oil_price Float,
    sentiment_score Float -- maybe int?
);

CREATE TABLE months_shrimp (
    date TIMESTAMP PRIMARY KEY,
    monthly_import FLOAT,
    average_weight FLOAT, -- zscore can be calculated from it?
    average_price FLOAT,
    gdp_delta_india Float,
    gdp_delta_ecuador Float,
    gdp_delta_indonesia Float,
    gdp_delta_vietnam Float,
    gdp_delta_thailand Float,
    tarrif_rate Float
);
