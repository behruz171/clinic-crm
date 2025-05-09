import requests

def get_location_from_ip(ip_address):
    try:
        response = requests.get(f"https://ipapi.co/{ip_address}/json/")
        if response.status_code == 200:
            data = response.json()
            return {
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
            }
        else:
            return {"error": True, "reason": "Invalid response from IP API"}
    except Exception as e:
        return {"error": True, "reason": str(e)}
