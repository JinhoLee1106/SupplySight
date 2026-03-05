# SupplySight
## How to Run & Test
1. Setup Environment   
    pip install -r requirements.txt <br>
    set your CENSUS_API_KEY in .env
    > touch .env <br>
    > echo "CENSUS_API_KEY=**your_key_here**\nSHRIMP_MONTHS_BACK=**number of months you want**" > .env
2. run data collection
  
## dataframe
1. shrimp_imports.cvs:
    >https://www.census.gov/data/developers/data-sets/international-trade.html<br>
    https://www.census.gov/foreign-trade/reference/guides/Guide_to_International_Trade_Datasets.pdf
    
    - I_COMMODITY: 2, 4, 6, or 10 character Import Harmonized System Code (String)
    - I_COMMODITY_SDESC: 50 character Import Harmonized Code Description (String)
    - GEN_VAL_MO: General Imports, Total Value (Int)
    - VES_WGT_MO: Vessel Shipping Weight (Int)
    - CNT_WGT_MO: Containerized Vessel Shipping Weight (Int)
    - AIR_WGT_MO: Air Shipping Weight (Int)
    - MONTH: \<YYYY\>\-\<MM\>
2. fao_shrimp_price_index.csv
    > https://www.fao.org/fishery/en/fishstat/fishpriceindex
    
    - date: \<YYYY\>\-\<MM\>
    - commodity: (String)
    - value: (float .1f)
    - source: (String)
    - source_file: (String)
    - ingested_at: (String)
3. weather_hourly.csv
    > https://open-meteo.com/en/docs
    
    - time (YYYY-MM-DDThh:mm)
    - sea_surface_temperature: (float .1f)
    - wave_height (float .2f)
    - ocean_current_velocity (float .1f)
    - sea_level_height_msl (float .2f)
4. news
    tbc
