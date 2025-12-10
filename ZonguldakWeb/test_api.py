import openmeteo_requests
import requests_cache
from retry_requests import retry

cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
retry_session = retry(cache_session, retries=3, backoff_factor=0.5)
openmeteo = openmeteo_requests.Client(session=retry_session)

url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": 41.45,
    "longitude": 31.79,
    "start_date": "2024-01-01",
    "end_date": "2024-01-02",
    "daily": ["temperature_850hPa_mean", "temperature_2m_mean", "pressure_msl_mean"]
}

try:
    print("API test ediliyor...")
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    daily = response.Daily()
    
    temp850 = daily.Variables(0).ValuesAsNumpy()
    temp2m = daily.Variables(1).ValuesAsNumpy()
    
    print(f"✅ Başarılı!")
    print(f"   Temp850: {temp850}")
    print(f"   Temp2m: {temp2m}")
    
except Exception as e:
    print(f"❌ Hata: {e}")