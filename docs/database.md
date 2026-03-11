## Schema
```mermaid
erDiagram
    dates_shrimp {
        TIMESTAMP(PK) date
        FLOAT sea_surface_temp_india
        FLOAT sea_surface_temp_ecuador
        FLOAT sea_surface_temp_indonesia
        FLOAT sea_surface_temp_vietnam
        FLOAT sea_surface_temp_thailand
        FLOAT precipitation_india
        FLOAT precipitation_ecuador
        FLOAT precipitation_indonesia
        FLOAT precipitation_vietnam
        FLOAT precipitation_thailand
        FLOAT wind_speed_india
        FLOAT wind_speed_ecuador
        FLOAT wind_speed_indonesia
        FLOAT wind_speed_vietnam
        FLOAT wind_speed_thailand
        FLOAT wave_height_india
        FLOAT wave_height_ecuador
        FLOAT wave_height_indonesia
        FLOAT wave_height_vietnam
        FLOAT wave_height_thailand
        FLOAT oil_price
        FLOAT sentiment_score
    }

    months_shrimp {
        TIMESTAMP(PK) date
        FLOAT monthly_import
        FLOAT average_weight
        FLOAT average_price
        FLOAT gdp_delta_india
        FLOAT gdp_delta_ecuador
        FLOAT gdp_delta_indonesia
        FLOAT gdp_delta_vietnam
        FLOAT gdp_delta_thailand
        FLOAT tarrif_rate
    }
```

## Command
Activate postgres instance
```
docker-compose -f infra/compose.yml --env-file {ENV_LOCATION} up -d
```
- The tables are automatically created once docker instnace is up. Change the schemas in infra/init.sql if needed.

Deactivate postgres instance
```
docker-compose -f infra/compose.yml down -v
```
- No persistent storage yet so deactivating removes all information.
- Must deactivate first for changing schema effects to show.

## Postgres Helper
```services/postgres_helper.py```: A class that provides simplified interactions with postgres. For large data, use dataframe.