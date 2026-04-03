CREATE TABLE dates_shrimp (
    date DATE PRIMARY KEY,
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
    date DATE PRIMARY KEY,
    monthly_import FLOAT,
    avg_unit_value_per_kg FLOAT,
    avg_air_share FLOAT,
    avg_container_ratio FLOAT,
    monthly_import_mom_pct FLOAT,
    monthly_import_yoy_pct FLOAT,
    monthly_import_roll3_avg FLOAT,
    monthly_import_roll6_avg FLOAT,
    monthly_import_roll3_std FLOAT,
    monthly_import_roll6_std FLOAT,
    monthly_import_zscore_6 FLOAT,
    price_index_value FLOAT
);

CREATE TABLE news (
    id UUID PRIMARY KEY,
    status TEXT DEFAULT 'new' CHECK (status in ('new', 'pending', 'processed')),
    source TEXT,
    title TEXT,
    content TEXT,
    url TEXT,
    publication_date DATE
);

CREATE TABLE evaluated_news (
    id UUID,
    product TEXT,
    relevancy_score INT,
    sentiment_score INT,
    processed_time TIMESTAMP
);
