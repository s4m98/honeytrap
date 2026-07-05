# ============= GEO LOCATION HANDLER =============
import requests
import os

class GeoLocationHandler:
    def __init__(self, geoip_db_path, enable_geoip):
        self.cache = {}
        self.enabled = False
        self.geoip_db_path = geoip_db_path
        self.enable_geoip = enable_geoip
        
        # Try to enable GeoIP
        if self.enable_geoip and os.path.exists(self.geoip_db_path):
            try:
                import geoip2.database
                self.reader = geoip2.database.Reader(self.geoip_db_path)
                self.enabled = True
                print("  ✅ GeoIP location tracking enabled")
            except:
                print("  ⚠️ GeoIP database found but couldn't load")
    
    def get_location(self, ip):
        """Get location information for an IP address"""
        if ip in self.cache:
            return self.cache[ip]
        
        location_info = {
            'country': 'Unknown',
            'city': 'Unknown',
            'latitude': 0,
            'longitude': 0,
            'isp': 'Unknown',
            'organization': 'Unknown'
        }
        
        # Try GeoIP database first
        if self.enabled:
            try:
                response = self.reader.city(ip)
                location_info['country'] = response.country.name or 'Unknown'
                location_info['city'] = response.city.name or 'Unknown'
                location_info['latitude'] = response.location.latitude or 0
                location_info['longitude'] = response.location.longitude or 0
                
                try:
                    asn_response = self.reader.asn(ip)
                    location_info['isp'] = asn_response.autonomous_system_organization or 'Unknown'
                except:
                    pass
                    
                self.cache[ip] = location_info
                return location_info
            except:
                pass
        
        # Fallback to free IP API (only for public IPs, skip localhost)
        if ip not in ['127.0.0.1', 'localhost'] and not ip.startswith('192.168.') and not ip.startswith('10.'):
            try:
                response = requests.get(f'http://ip-api.com/json/{ip}', timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success':
                        location_info['country'] = data.get('country', 'Unknown')
                        location_info['city'] = data.get('city', 'Unknown')
                        location_info['latitude'] = data.get('lat', 0)
                        location_info['longitude'] = data.get('lon', 0)
                        location_info['isp'] = data.get('isp', 'Unknown')
                        location_info['organization'] = data.get('org', 'Unknown')
                        self.cache[ip] = location_info
            except:
                pass
        
        return location_info
