from flask import Flask, render_template, request, jsonify
import requests
import json
import time
from datetime import datetime
import sqlite3
import os
from geopy.geocoders import Nominatim
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'business-finder-2024'

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessFinder:
    def __init__(self):
        self.geocoder = Nominatim(user_agent="business_finder_v2.0")
        self.init_database()
        
        # ÇOK ZENGİN KATEGORİ MAPPING - Her kategori için 5-15 farklı etiket
        self.advanced_category_mapping = {
            # TEKNOLOJİ & YAZILIM
            'yazılım': [
                'office=it', 'office=company', 'office=software', 'industry=software',
                'name~"yazılım|software|bilişim|teknoloji|IT|teknik|web|mobil|uygulama"',
                'office~".*"["industry"="software"]', 'shop=computer',
                'amenity=internet_cafe', 'office=research', 'industry=technology',
                'name~"developer|geliştirici|programlama|coding|digital"'
            ],
            'software': [
                'office=it', 'office=company', 'office=software', 'industry=software',
                'name~"software|development|tech|IT|programming|coding|app|web"',
                'office~".*"["industry"="software"]', 'shop=computer',
                'office=research', 'industry=technology'
            ],
            'bilişim': [
                'office=it', 'office=company', 'industry=technology',
                'name~"bilişim|teknoloji|IT|sistem|network|ağ|server"',
                'shop=computer', 'amenity=internet_cafe'
            ],
            
            # YİYECEK & İÇECEK
            'kafe': [
                'amenity=cafe', 'amenity=restaurant["cuisine"="coffee_shop"]',
                'name~"kafe|cafe|kahve|coffee|espresso|latte"', 'shop=coffee',
                'amenity=bar["bar"="coffee"]', 'cuisine=coffee_shop',
                'name~"starbucks|gloria|kahve dünyası|coffee shop"'
            ],
            'cafe': [
                'amenity=cafe', 'amenity=restaurant["cuisine"="coffee_shop"]',
                'name~"cafe|coffee|espresso|cappuccino|latte"', 'shop=coffee',
                'cuisine=coffee_shop', 'amenity=bar["bar"="coffee"]'
            ],
            'restoran': [
                'amenity=restaurant', 'amenity=fast_food', 'amenity=food_court',
                'name~"restoran|restaurant|lokanta|yemek|aşçı|chef"',
                'cuisine~".*"', 'amenity=pub["food"="yes"]',
                'tourism=restaurant', 'shop=deli'
            ],
            'restaurant': [
                'amenity=restaurant', 'amenity=fast_food', 'amenity=food_court',
                'cuisine~".*"', 'amenity=pub["food"="yes"]', 'tourism=restaurant'
            ],
            'fast_food': [
                'amenity=fast_food', 'name~"mcdonald|burger|pizza|kebab|döner"',
                'cuisine=burger', 'cuisine=pizza', 'cuisine=kebab'
            ],
            
            # SAĞLIK
            'eczane': [
                'amenity=pharmacy', 'shop=chemist', 'healthcare=pharmacy',
                'name~"eczane|pharmacy|eczacı|ilaç|drug"',
                'shop=medical_supply', 'healthcare=clinic["pharmacy"="yes"]'
            ],
            'pharmacy': [
                'amenity=pharmacy', 'shop=chemist', 'healthcare=pharmacy',
                'name~"pharmacy|drug|medicine"', 'shop=medical_supply'
            ],
            'hastane': [
                'amenity=hospital', 'amenity=clinic', 'healthcare=hospital',
                'healthcare=clinic', 'name~"hastane|hospital|klinik|clinic|tıp|medical"',
                'healthcare=doctor', 'amenity=doctors', 'healthcare=centre'
            ],
            'hospital': [
                'amenity=hospital', 'amenity=clinic', 'healthcare=hospital',
                'healthcare=clinic', 'healthcare=doctor', 'amenity=doctors'
            ],
            'doktor': [
                'healthcare=doctor', 'amenity=doctors', 'healthcare=clinic',
                'name~"doktor|doctor|hekim|physician|tıp|medical"',
                'office=physician', 'healthcare=dentist'
            ],
            
            # ALIŞVERİŞ
            'market': [
                'shop=supermarket', 'shop=convenience', 'shop=grocery',
                'name~"market|süper|grocery|gıda|migros|carrefour|bim|a101"',
                'amenity=marketplace', 'shop=department_store',
                'shop=general', 'shop=food'
            ],
            'supermarket': [
                'shop=supermarket', 'shop=convenience', 'shop=grocery',
                'shop=department_store', 'amenity=marketplace'
            ],
            'mağaza': [
                'shop~".*"', 'name~"mağaza|store|shop|alışveriş|satış"',
                'amenity=marketplace', 'shop=mall', 'tourism=shopping'
            ],
            
            # FİNANS
            'banka': [
                'amenity=bank', 'office=financial', 'amenity=atm',
                'name~"banka|bank|finansal|financial|kredi|para"',
                'office=insurance', 'amenity=bureau_de_change'
            ],
            'bank': [
                'amenity=bank', 'office=financial', 'amenity=atm',
                'office=insurance', 'amenity=bureau_de_change'
            ],
            'atm': [
                'amenity=atm', 'name~"atm|bankamatik|para|cash"'
            ],
            
            # EĞİTİM
            'okul': [
                'amenity=school', 'amenity=university', 'amenity=college',
                'name~"okul|school|üniversite|university|lise|ilkokul|ortaokul"',
                'amenity=kindergarten', 'building=school', 'education~".*"'
            ],
            'school': [
                'amenity=school', 'amenity=university', 'amenity=college',
                'amenity=kindergarten', 'building=school'
            ],
            'üniversite': [
                'amenity=university', 'amenity=college',
                'name~"üniversite|university|akademi|yüksekokul"',
                'building=university'
            ],
            
            # GÜZELLİK & BAKIM
            'kuaför': [
                'shop=hairdresser', 'shop=beauty', 'amenity=hairdresser',
                'name~"kuaför|berber|hairdresser|beauty|güzellik|saç"',
                'shop=cosmetics', 'leisure=spa'
            ],
            'berber': [
                'shop=hairdresser', 'amenity=hairdresser',
                'name~"berber|barbershop|kuaför|saç|erkek"'
            ],
            'güzellik': [
                'shop=beauty', 'shop=cosmetics', 'leisure=spa',
                'name~"güzellik|beauty|estetik|kozmetik|nail|masaj"',
                'shop=massage', 'amenity=spa'
            ],
            
            # SPOR & FITNESS
            'gym': [
                'leisure=fitness_centre', 'leisure=sports_centre', 'amenity=gym',
                'name~"gym|fitness|spor|antrenman|training"',
                'shop=sports', 'leisure=swimming_pool', 'sport~".*"'
            ],
            'fitness': [
                'leisure=fitness_centre', 'leisure=sports_centre', 'amenity=gym',
                'sport=fitness', 'leisure=swimming_pool'
            ],
            'spor': [
                'leisure=sports_centre', 'leisure=fitness_centre',
                'name~"spor|sport|atletik|futbol|basketbol|voleybol"',
                'leisure=stadium', 'sport~".*"'
            ],
            
            # KONAKLAMA
            'hotel': [
                'tourism=hotel', 'tourism=motel', 'tourism=guest_house',
                'name~"hotel|otel|pansiyon|konaklama|apart"',
                'tourism=hostel', 'building=hotel'
            ],
            'otel': [
                'tourism=hotel', 'tourism=motel', 'tourism=guest_house',
                'name~"otel|hotel|pansiyon|konaklama|apart"',
                'tourism=hostel', 'building=hotel'
            ],
            
            # ULAŞIM
            'benzinlik': [
                'amenity=fuel', 'shop=gas_station',
                'name~"benzin|petrol|shell|bp|total|opet|po|akaryakıt"',
                'highway=services["fuel"="yes"]'
            ],
            'fuel': [
                'amenity=fuel', 'shop=gas_station',
                'highway=services["fuel"="yes"]'
            ],
            'otopark': [
                'amenity=parking', 'amenity=parking_entrance',
                'name~"otopark|parking|park|garaj"',
                'building=parking', 'landuse=parking'
            ],
            
            # HUKUK & MALİ
            'avukat': [
                'office=lawyer', 'office=legal', 'amenity=lawyer',
                'name~"avukat|lawyer|hukuk|legal|adalet|noter"',
                'office=notary', 'amenity=courthouse'
            ],
            'lawyer': [
                'office=lawyer', 'office=legal', 'amenity=lawyer',
                'office=notary', 'amenity=courthouse'
            ],
            'muhasebe': [
                'office=accountant', 'office=financial',
                'name~"muhasebe|accountant|mali|vergi|smmm"',
                'office=tax_advisor', 'office=insurance'
            ],
            'noter': [
                'office=notary', 'amenity=notary',
                'name~"noter|notary|tasdik|onay"'
            ],
            
            # HİZMETLER
            'temizlik': [
                'shop=dry_cleaning', 'shop=laundry',
                'name~"temizlik|cleaning|kuru|çamaşır|laundry"',
                'amenity=washing_machine'
            ],
            'tamir': [
                'shop=repair', 'craft=electrician', 'craft=plumber',
                'name~"tamir|repair|servisi|teknik|usta"',
                'shop=electronics_repair', 'craft~".*"'
            ],
            
            # EĞLENCE & KÜLTÜR
            'sinema': [
                'amenity=cinema', 'name~"sinema|cinema|movie|film"',
                'leisure=cinema', 'building=cinema'
            ],
            'müze': [
                'tourism=museum', 'name~"müze|museum|galeri|sanat"',
                'tourism=gallery', 'amenity=arts_centre'
            ],
            
            # PET & HAYVAN
            'veteriner': [
                'amenity=veterinary', 'healthcare=veterinary',
                'name~"veteriner|vet|hayvan|animal|pet"',
                'shop=pet', 'amenity=animal_shelter'
            ],
            'pet_shop': [
                'shop=pet', 'name~"pet|hayvan|animal|köpek|kedi"',
                'shop=pet_grooming', 'amenity=veterinary'
            ]
        }
        
    def init_database(self):
        """SQLite veritabanını başlat"""
        try:
            conn = sqlite3.connect('business_data.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location TEXT NOT NULL,
                    category TEXT NOT NULL,
                    results_count INTEGER,
                    search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    address TEXT,
                    latitude REAL,
                    longitude REAL,
                    category TEXT,
                    phone TEXT,
                    website TEXT,
                    cached_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Veritabanı başarıyla başlatıldı")
            
        except Exception as e:
            logger.error(f"❌ Veritabanı hatası: {str(e)}")
    
    def get_coordinates(self, location):
        """Konum koordinatlarını al"""
        try:
            logger.info(f"🌍 Konum aranıyor: {location}")
            location_data = self.geocoder.geocode(location, timeout=15)
            
            if location_data:
                coordinates = {
                    'latitude': location_data.latitude,
                    'longitude': location_data.longitude,
                    'display_name': location_data.address
                }
                logger.info(f"✅ Konum bulundu: {coordinates}")
                return coordinates
            else:
                logger.warning(f"❌ Konum bulunamadı: {location}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Koordinat alma hatası: {str(e)}")
            return None
    
    def build_overpass_query(self, lat, lon, category, radius):
        """Gelişmiş Overpass sorgusu oluştur"""
        category_lower = category.lower()
        
        if category_lower in self.advanced_category_mapping:
            tag_list = self.advanced_category_mapping[category_lower]
        else:
            # Fallback: genel arama
            tag_list = [
                f'name~"{category}"',
                f'amenity~".*{category}.*"',
                f'shop~".*{category}.*"',
                f'office~".*{category}.*"'
            ]
        
        # Her etiket için node, way, relation sorguları oluştur
        query_parts = []
        for tag in tag_list:
            query_parts.extend([
                f"node[{tag}](around:{radius},{lat},{lon});",
                f"way[{tag}](around:{radius},{lat},{lon});",
                f"relation[{tag}](around:{radius},{lat},{lon});"
            ])
        
        overpass_query = f"""
        [out:json][timeout:40];
        (
          {chr(10).join(['  ' + part for part in query_parts])}
        );
        out center meta;
        """
        
        return overpass_query
    
    def search_overpass_api(self, lat, lon, category, radius=5000):
        """Overpass API ile arama yap"""
        try:
            logger.info(f"🔍 Gelişmiş arama: {category} kategorisi, {radius}m yarıçap")
            
            # Sorgu oluştur
            overpass_query = self.build_overpass_query(lat, lon, category, radius)
            overpass_url = "http://overpass-api.de/api/interpreter"
            
            # API çağrısı
            response = requests.post(
                overpass_url,
                data=overpass_query,
                timeout=45,
                headers={'User-Agent': 'BusinessFinder/2.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                businesses = self.parse_overpass_results(data, category)
                logger.info(f"✅ {len(businesses)} işletme bulundu")
                return businesses
            else:
                logger.error(f"❌ Overpass API hatası: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Overpass API sorgu hatası: {str(e)}")
            return []
    
    def get_category_style(self, category):
        """Kategori stilini döndür"""
        styles = {
            'yazılım': {'icon': '💻', 'color': '#2196F3', 'bg': '#E3F2FD'},
            'software': {'icon': '💻', 'color': '#2196F3', 'bg': '#E3F2FD'},
            'bilişim': {'icon': '🖥️', 'color': '#1565C0', 'bg': '#E1F5FE'},
            'kafe': {'icon': '☕', 'color': '#8D6E63', 'bg': '#EFEBE9'},
            'cafe': {'icon': '☕', 'color': '#8D6E63', 'bg': '#EFEBE9'},
            'restoran': {'icon': '🍽️', 'color': '#FF5722', 'bg': '#FBE9E7'},
            'restaurant': {'icon': '🍽️', 'color': '#FF5722', 'bg': '#FBE9E7'},
            'eczane': {'icon': '💊', 'color': '#F44336', 'bg': '#FFEBEE'},
            'pharmacy': {'icon': '💊', 'color': '#F44336', 'bg': '#FFEBEE'},
            'market': {'icon': '🛒', 'color': '#4CAF50', 'bg': '#E8F5E8'},
            'supermarket': {'icon': '🛒', 'color': '#4CAF50', 'bg': '#E8F5E8'},
            'banka': {'icon': '🏦', 'color': '#3F51B5', 'bg': '#E8EAF6'},
            'bank': {'icon': '🏦', 'color': '#3F51B5', 'bg': '#E8EAF6'},
            'hastane': {'icon': '🏥', 'color': '#E91E63', 'bg': '#FCE4EC'},
            'hospital': {'icon': '🏥', 'color': '#E91E63', 'bg': '#FCE4EC'},
            'okul': {'icon': '🎓', 'color': '#FF9800', 'bg': '#FFF3E0'},
            'school': {'icon': '🎓', 'color': '#FF9800', 'bg': '#FFF3E0'},
            'kuaför': {'icon': '✂️', 'color': '#9C27B0', 'bg': '#F3E5F5'},
            'hairdresser': {'icon': '✂️', 'color': '#9C27B0', 'bg': '#F3E5F5'},
            'gym': {'icon': '🏋️', 'color': '#607D8B', 'bg': '#ECEFF1'},
            'fitness': {'icon': '🏋️', 'color': '#607D8B', 'bg': '#ECEFF1'},
            'hotel': {'icon': '🏨', 'color': '#795548', 'bg': '#EFEBE9'},
            'otel': {'icon': '🏨', 'color': '#795548', 'bg': '#EFEBE9'},
            'benzinlik': {'icon': '⛽', 'color': '#FFC107', 'bg': '#FFFDE7'},
            'fuel': {'icon': '⛽', 'color': '#FFC107', 'bg': '#FFFDE7'},
            'avukat': {'icon': '⚖️', 'color': '#455A64', 'bg': '#ECEFF1'},
            'lawyer': {'icon': '⚖️', 'color': '#455A64', 'bg': '#ECEFF1'}
        }
        
        return styles.get(category.lower(), {'icon': '🏢', 'color': '#666666', 'bg': '#F5F5F5'})
    
    def parse_overpass_results(self, data, category):
        """Overpass sonuçlarını parse et"""
        businesses = []
        seen_names = set()
        
        try:
            style = self.get_category_style(category)
            
            for element in data.get('elements', []):
                if element['type'] == 'node':
                    lat, lon = element.get('lat'), element.get('lon')
                elif element['type'] == 'way' and 'center' in element:
                    lat, lon = element['center']['lat'], element['center']['lon']
                else:
                    continue
                
                tags = element.get('tags', {})
                
                # İşletme adı
                name = (tags.get('name') or tags.get('brand') or 
                       f"{style['icon']} İsimsiz {category.title()}")
                
                # Duplicate kontrolü
                if name in seen_names:
                    continue
                seen_names.add(name)
                
                # Adres formatla
                address = self.format_address(tags)
                
                business = {
                    'id': element.get('id'),
                    'name': name,
                    'address': address,
                    'latitude': lat,
                    'longitude': lon,
                    'category': category,
                    'phone': tags.get('phone', tags.get('contact:phone', '📞 Kayıtlı değil')),
                    'website': tags.get('website', tags.get('contact:website', '🌐 Kayıtlı değil')),
                    'email': tags.get('email', tags.get('contact:email', '📧 Kayıtlı değil')),
                    'opening_hours': tags.get('opening_hours', '🕒 Bilgi yok'),
                    'icon': style['icon'],
                    'color': style['color'],
                    'bg_color': style['bg'],
                    'business_type': tags.get('amenity', tags.get('shop', tags.get('office', category)))
                }
                
                businesses.append(business)
            
            # İsme göre sırala ve ilk 50'yi al
            businesses.sort(key=lambda x: x['name'])
            return businesses[:50]
            
        except Exception as e:
            logger.error(f"❌ Parse hatası: {str(e)}")
            return []
    
    def format_address(self, tags):
        """Adres formatla"""
        address_parts = []
        
        fields = [
            ('addr:housenumber', ''), ('addr:street', ''),
            ('addr:neighbourhood', 'Mah.'), ('addr:quarter', 'Mah.'),
            ('addr:suburb', ''), ('addr:city', ''),
            ('addr:province', ''), ('addr:postcode', '')
        ]
        
        for field, suffix in fields:
            if field in tags and tags[field].strip():
                value = tags[field].strip()
                if suffix:
                    value += f" {suffix}"
                address_parts.append(value)
        
        if address_parts:
            return ', '.join(address_parts)
        
        return "📍 Adres kayıtlı değil"
    
    def search_businesses(self, location, category, radius=5000):
        """Ana arama fonksiyonu"""
        try:
            # Koordinatları al
            coordinates = self.get_coordinates(location)
            if not coordinates:
                return {
                    'status': 'error',
                    'message': f'"{location}" konumu bulunamadı. Lütfen daha spesifik bir adres girin.',
                    'businesses': []
                }
            
            # İşletmeleri ara
            businesses = self.search_overpass_api(
                coordinates['latitude'],
                coordinates['longitude'],
                category,
                radius
            )
            
            # Arama geçmişini kaydet
            self.save_search_history(location, category, len(businesses))
            
            return {
                'status': 'success',
                'location': {
                    'name': coordinates['display_name'],
                    'latitude': coordinates['latitude'],
                    'longitude': coordinates['longitude']
                },
                'category': category,
                'businesses': businesses,
                'total_found': len(businesses)
            }
            
        except Exception as e:
            logger.error(f"❌ Arama hatası: {str(e)}")
            return {
                'status': 'error',
                'message': f'Arama sırasında hata oluştu: {str(e)}',
                'businesses': []
            }
    
    def save_search_history(self, location, category, results_count):
        """Arama geçmişini kaydet"""
        try:
            conn = sqlite3.connect('business_data.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO search_history (location, category, results_count)
                VALUES (?, ?, ?)
            ''', (location, category, results_count))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Geçmiş kaydetme hatası: {str(e)}")
    
    def get_search_stats(self):
        """Arama istatistikleri"""
        try:
            conn = sqlite3.connect('business_data.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT location, category, results_count, search_time
                FROM search_history
                ORDER BY search_time DESC
                LIMIT 10
            ''')
            recent_searches = cursor.fetchall()
            
            cursor.execute('''
                SELECT category, COUNT(*) as count
                FROM search_history
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
            ''')
            popular_categories = cursor.fetchall()
            
            conn.close()
            
            return {
                'recent_searches': recent_searches,
                'popular_categories': popular_categories
            }
            
        except Exception as e:
            logger.error(f"❌ İstatistik hatası: {str(e)}")
            return {'recent_searches': [], 'popular_categories': []}

# Global instance
finder = BusinessFinder()

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_businesses():
    """İşletme arama endpoint'i"""
    try:
        data = request.get_json()
        
        location = data.get('location', '').strip()
        category = data.get('category', '').strip()
        radius = int(data.get('radius', 5000))
        
        if not location or not category:
            return jsonify({
                'status': 'error',
                'message': 'Lütfen konum ve kategori bilgilerini girin.'
            })
        
        logger.info(f"🔍 Arama başlatıldı: {location} - {category}")
        
        # Arama yap
        results = finder.search_businesses(location, category, radius)
        
        # Sonuç yoksa özel mesaj
        if results['status'] == 'success' and len(results['businesses']) == 0:
            results['status'] = 'error'
            results['message'] = f"""❌ "{category}" kategorisinde işletme bulunamadı!

📋 Öneriler:
• Kategori adını İngilizce deneyin (örn: "software", "cafe")
• Daha geniş bir yarıçap seçin (10-20 km)
• Büyük şehirlerde arama yapın
• Alternatif kategori isimleri deneyin

💡 Popüler kategoriler: kafe, eczane, market, banka, restoran

ℹ️ Not: OpenStreetMap verisi bölgeye göre değişiklik gösterebilir."""
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"❌ Arama endpoint hatası: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Arama sırasında hata oluştu: {str(e)}'
        })

@app.route('/stats')
def get_stats():
    """İstatistikleri getir"""
    try:
        stats = finder.get_search_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/categories')
def get_categories():
    """Desteklenen kategorileri listele"""
    categories = list(finder.advanced_category_mapping.keys())
    categorized = {
        'Teknoloji': [k for k in categories if k in ['yazılım', 'software', 'bilişim']],
        'Yiyecek': [k for k in categories if k in ['kafe', 'cafe', 'restoran', 'restaurant']],
        'Sağlık': [k for k in categories if k in ['eczane', 'pharmacy', 'hastane', 'hospital', 'doktor']],
        'Alışveriş': [k for k in categories if k in ['market', 'supermarket', 'mağaza']],
        'Finans': [k for k in categories if k in ['banka', 'bank', 'atm']],
        'Eğitim': [k for k in categories if k in ['okul', 'school', 'üniversite']],
        'Hizmetler': [k for k in categories if k in ['kuaför', 'berber', 'güzellik', 'temizlik', 'tamir']],
        'Diğer': [k for k in categories if k not in [
            'yazılım', 'software', 'bilişim', 'kafe', 'cafe', 'restoran', 'restaurant',
            'eczane', 'pharmacy', 'hastane', 'hospital', 'doktor', 'market', 'supermarket',
            'mağaza', 'banka', 'bank', 'atm', 'okul', 'school', 'üniversite',
            'kuaför', 'berber', 'güzellik', 'temizlik', 'tamir'
        ]]
    }
    
    return jsonify(categorized)

if __name__ == '__main__':
    print("🚀 Gelişmiş İşletme Bulucu Sistemi v2.0")
    print("🌍 Zenginleştirilmiş kategori mapping ile")
    print("📍 URL: http://localhost:5000")
    
    if not os.path.exists('business_data.db'):
        print("📊 Veritabanı oluşturuluyor...")
    
    app.run(host='0.0.0.0', port=5000, debug=True)