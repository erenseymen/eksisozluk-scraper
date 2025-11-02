#!/usr/bin/env python3
"""
Ekşi Sözlük Scraper
Terminal tabanlı, AI-friendly output üreten scraper.
"""

import argparse
import json
import re
import time
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

import cloudscraper
from bs4 import BeautifulSoup


class EksisozlukScraper:
    """Ekşi Sözlük scraper sınıfı"""
    
    BASE_URL = "https://eksisozluk.com"
    
    def __init__(self, delay: float = 1.5, max_retries: int = 3, retry_delay: float = 5.0, timeout: float = 60.0):
        """
        Args:
            delay: Her request arası bekleme süresi (saniye)
            max_retries: Maksimum tekrar deneme sayısı
            retry_delay: Hata aldığında tekrar denemeden önce bekleme süresi (saniye)
            timeout: Toplam timeout süresi (saniye)
        """
        self.delay = delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        # cloudscraper Cloudflare korumasını bypass eder
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'linux',
                'desktop': True
            }
        )
        # Ek header'lar
        self.session.headers.update({
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        })
    
    def _make_request(self, url: str):
        """HTTP request yapar, retry mekanizması ile"""
        start_time = time.time()
        attempt = 0
        
        while attempt < self.max_retries:
            try:
                # Timeout kontrolü
                if time.time() - start_time > self.timeout:
                    print(f"ERROR: Timeout ({self.timeout}s) aşıldı", file=sys.stderr)
                    return None
                
                response = self.session.get(url, timeout=10, allow_redirects=True)
                
                # 404 hatası sayfa yok demektir, retry yapma
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response
                
            except Exception as e:
                # HTTP hataları için kontrol et
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 404:
                        # 404 hatası sayfa yok demektir, retry yapma
                        return None
                
                attempt += 1
                if attempt < self.max_retries:
                    print(f"WARNING: Request hatası (deneme {attempt}/{self.max_retries}): {e}", file=sys.stderr)
                    time.sleep(self.retry_delay)
                else:
                    print(f"ERROR: Maksimum deneme sayısına ulaşıldı: {url}", file=sys.stderr)
                    return None
        
        return None
    
    def _parse_entry(self, entry_element) -> Optional[Dict]:
        """Bir entry elementini parse eder - çoklu selector stratejisi ile"""
        try:
            entry_data = {}
            
            # Entry ID - data-id attribute'dan veya href'ten
            entry_id = None
            if entry_element.get('data-id'):
                entry_id = entry_element.get('data-id')
                entry_data['entry_id'] = entry_id
            else:
                # href'ten entry ID çıkar
                entry_id_elem = (entry_element.find('a', {'class': 'entry-date'}) or 
                               entry_element.find('a', class_=re.compile('entry.*date')) or
                               entry_element.find('a', href=re.compile(r'entry--\d+')))
                if entry_id_elem and entry_id_elem.get('href'):
                    href = entry_id_elem['href']
                    entry_id_match = re.search(r'entry--(\d+)', href)
                    if entry_id_match:
                        entry_id = entry_id_match.group(1)
                        entry_data['entry_id'] = entry_id
                        entry_data['entry_url'] = self.BASE_URL + href if href.startswith('/') else href
            
            if not entry_id:
                return None
            
            # Entry tarihi
            date_elem = (entry_element.find('a', {'class': 'entry-date'}) or
                        entry_element.find('a', class_=re.compile('entry.*date')) or
                        entry_element.find('span', class_=re.compile('date')) or
                        entry_element.find('time'))
            if date_elem:
                entry_data['date'] = date_elem.get_text(strip=True)
            
            # Yazar
            author_elem = (entry_element.find('a', {'class': 'entry-author'}) or
                          entry_element.find('a', class_=re.compile('entry.*author')) or
                          entry_element.find('a', class_=re.compile('author')) or
                          entry_element.find('span', {'class': 'entry-author'}) or
                          entry_element.find('span', class_=re.compile('author')))
            if author_elem:
                entry_data['author'] = author_elem.get_text(strip=True)
            
            # Entry içeriği - çoklu selector dene
            content_elem = (entry_element.find('div', {'class': 'content'}) or
                           entry_element.find('div', class_=re.compile('content')) or
                           entry_element.find('p') or
                           entry_element.find('div', {'class': 'entry-content'}))
            
            if content_elem:
                # HTML tag'lerini temizle ama formatı koru
                for br in content_elem.find_all('br'):
                    br.replace_with('\n')
                for p in content_elem.find_all('p'):
                    p.append('\n')
                entry_data['content'] = content_elem.get_text(separator='\n', strip=True)
            
            # Fav sayısı
            fav_elem = (entry_element.find('span', {'class': 'fav-count'}) or
                       entry_element.find('span', class_=re.compile('fav')) or
                       entry_element.find('a', class_=re.compile('favorite')))
            if fav_elem:
                fav_text = fav_elem.get_text(strip=True)
                # Sayıları çıkar
                fav_numbers = re.findall(r'\d+', fav_text)
                if fav_numbers:
                    try:
                        entry_data['favorite_count'] = int(fav_numbers[0])
                    except ValueError:
                        entry_data['favorite_count'] = 0
                else:
                    entry_data['favorite_count'] = 0
            
            # Entry numarası (sıralama)
            entry_no_elem = (entry_element.find('span', {'class': 'index'}) or
                           entry_element.find('span', class_=re.compile('index')) or
                           entry_element.find('span', class_=re.compile('entry.*number')))
            if entry_no_elem:
                entry_data['entry_number'] = entry_no_elem.get_text(strip=True)
            
            # Entry ID ve content zorunlu
            if 'entry_id' in entry_data and 'content' in entry_data and entry_data['content']:
                return entry_data
            
        except Exception as e:
            print(f"WARNING: Entry parse hatası: {e}", file=sys.stderr)
        
        return None
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Ekşi Sözlük tarih formatını parse eder"""
        try:
            # Formatlar: "12.01.2024 15:30" veya "dün 15:30" veya "bugün 15:30" veya "20.02.1999 ~ 06.05.2007 01:16"
            date_str = date_str.strip()
            
            # Tarih aralığı formatı: "26.10.2025 15:42 ~ 18:12" veya "20.02.1999 ~ 06.05.2007 01:16"
            # İlk tarihi kullan (orijinal posting tarihi)
            if ' ~ ' in date_str:
                # İlk kısmı al (orijinal tarih)
                first_part = date_str.split(' ~ ')[0].strip()
                # Eğer ilk kısımda tam tarih varsa onu kullan
                date_pattern_with_time = r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})'
                match = re.match(date_pattern_with_time, first_part)
                if match:
                    day, month, year, hour, minute = map(int, match.groups())
                    return datetime(year, month, day, hour, minute)
                # Sadece tarih varsa
                date_pattern_date_only = r'(\d{1,2})\.(\d{1,2})\.(\d{4})'
                match = re.match(date_pattern_date_only, first_part)
                if match:
                    day, month, year = map(int, match.groups())
                    return datetime(year, month, day)
                # Eğer ilk kısım parse edilemezse, ikinci kısmı dene
                second_part = date_str.split(' ~ ')[-1].strip()
                date_str = second_part
            
            # Bugün/dün kontrolü
            if date_str.startswith('bugün'):
                today = datetime.now()
                time_part = re.search(r'(\d{1,2}):(\d{2})', date_str)
                if time_part:
                    hour, minute = int(time_part.group(1)), int(time_part.group(2))
                    return today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return datetime.now()
            
            if date_str.startswith('dün'):
                yesterday = datetime.now() - timedelta(days=1)
                time_part = re.search(r'(\d{1,2}):(\d{2})', date_str)
                if time_part:
                    hour, minute = int(time_part.group(1)), int(time_part.group(2))
                    return yesterday.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return datetime.now() - timedelta(days=1)
            
            # Normal tarih formatı: DD.MM.YYYY HH:MM
            date_pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})'
            match = re.match(date_pattern, date_str)
            if match:
                day, month, year, hour, minute = map(int, match.groups())
                return datetime(year, month, day, hour, minute)
            
            # Sadece tarih: DD.MM.YYYY
            date_pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{4})'
            match = re.match(date_pattern, date_str)
            if match:
                day, month, year = map(int, match.groups())
                return datetime(year, month, day)
            
        except Exception as e:
            print(f"WARNING: Tarih parse hatası: {date_str} - {e}", file=sys.stderr)
        
        return None
    
    def _find_last_page(self, soup: BeautifulSoup, title: str, title_id: Optional[str] = None, pagination_format: Optional[str] = None) -> Optional[int]:
        """Son sayfa numarasını pagination linklerinden bulur"""
        try:
            # Pagination linklerini kontrol et
            pagination_links = soup.find_all('a', href=re.compile(r'p=\d+'))
            
            max_page_from_links = 1
            for link in pagination_links:
                href = link.get('href', '')
                page_match = re.search(r'p=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page_from_links = max(max_page_from_links, page_num)
            
            # Eğer pagination linklerinden sayfa bulduysak, onu döndür
            if max_page_from_links > 1:
                return max_page_from_links
            
            return None
        except Exception as e:
            print(f"WARNING: Son sayfa bulunamadı: {e}", file=sys.stderr)
            return None
    
    def _find_last_page_from_pagination(self, soup: BeautifulSoup) -> Optional[int]:
        """İlk sayfadaki pagination'dan son sayfa numarasını bulur"""
        try:
            # Öncelikle data-pagecount attribute'undan al
            pagination_div = soup.find('div', class_='pager')
            if pagination_div and pagination_div.get('data-pagecount'):
                try:
                    pagecount = int(pagination_div.get('data-pagecount'))
                    if pagecount > 0:
                        return pagecount
                except (ValueError, TypeError):
                    pass
            
            # Fallback: pagination linklerinden bul
            pagination_links = soup.find_all('a', href=re.compile(r'p=\d+'))
            max_page = 1
            for link in pagination_links:
                href = link.get('href', '')
                page_match = re.search(r'p=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page = max(max_page, page_num)
            
            # Sayfa numaralarını içeren text içinde de ara
            pagination_text = soup.get_text()
            page_matches = re.findall(r'\b(\d+)\s*(?:sayfa|page)', pagination_text, re.I)
            for match in page_matches:
                try:
                    page_num = int(match)
                    max_page = max(max_page, page_num)
                except ValueError:
                    pass
            
            return max_page if max_page > 1 else None
        except Exception as e:
            print(f"WARNING: Son sayfa bulunamadı: {e}", file=sys.stderr)
            return None
    
    def scrape_title(self, title: str, time_filter: Optional[timedelta] = None) -> List[Dict]:
        """Bir başlıktaki tüm entry'leri scrape eder"""
        entries = []
        page = 1
        title_id = None  # Topic ID'yi saklamak için
        title_slug = None  # Slug'ı saklamak için
        pagination_format = None  # Pagination URL formatını sakla
        
        print(f"Başlık scrape ediliyor: {title}", file=sys.stderr)
        
        # Eğer zaman filtresi varsa, son sayfadan başlayıp geriye doğru gideceğiz
        reverse_order = False
        last_page = None  # Son sayfa numarası
        
        while True:
            # Başlık URL'i oluştur
            if page == 1:
                url = f"{self.BASE_URL}/{title}"
            else:
                # Doğru pagination formatını kullan
                if pagination_format:
                    url = f"{self.BASE_URL}{pagination_format.format(page=page)}"
                elif title_id:
                    url = f"{self.BASE_URL}/{title}--{title_id}?p={page}"
                else:
                    url = f"{self.BASE_URL}/{title}?p={page}"
            
            # URL'i logla
            print(f"INFO: Erişilen URL: {url}", file=sys.stderr)
            
            response = self._make_request(url)
            if not response:
                # 404 veya başka bir hata - sayfa yok veya erişilemiyor
                if page > 1:
                    print(f"INFO: Sayfa {page} bulunamadı, scraping sonlandırılıyor", file=sys.stderr)
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # İlk sayfada topic ID ve pagination formatını çıkar
            if page == 1 and not title_id:
                response_url = response.url
                # URL formatı: https://eksisozluk.com/gauge--93891 veya https://eksisozluk.com/gauge--93891?p=1
                # Title'ı escape et
                escaped_title = re.escape(title)
                title_id_match = re.search(rf'/{escaped_title}--(\d+)', response_url)
                if title_id_match:
                    title_id = title_id_match.group(1)
                    print(f"INFO: Topic ID bulundu: {title_id}", file=sys.stderr)
                else:
                    # Alternatif: URL'de -- ile başlayan sayı ara
                    alt_match = re.search(r'--(\d+)', response_url)
                    if alt_match:
                        title_id = alt_match.group(1)
                        print(f"INFO: Topic ID bulundu (alternatif yöntem): {title_id}", file=sys.stderr)
                
                # Basit format: /slug--id?p=X kullan (daha güvenilir)
                # Pagination linklerindeki /basliklar/gundem formatı yanlış sonuçlara yol açıyor
                if title_id:
                    pagination_format = f"/{title}--{title_id}?p={{page}}"
                    print(f"INFO: Pagination formatı bulundu (basit format): {pagination_format}", file=sys.stderr)
                else:
                    # Son çare: pagination linklerinden formatı çıkar
                    pagination_link = soup.find('a', href=re.compile(r'p=\d+'))
                    if pagination_link and pagination_link.get('href'):
                        href = pagination_link['href']
                        parsed_url = urlparse(href)
                        params = parse_qs(parsed_url.query)
                        
                        if 'id' in params and 'slug' in params:
                            title_id = params['id'][0]
                            title_slug = params['slug'][0]
                            pagination_format = f"{parsed_url.path}?p={{page}}&id={title_id}&slug={title_slug}"
                            print(f"INFO: Pagination formatı bulundu: {pagination_format}", file=sys.stderr)
            
            # İlk sayfada pagination'dan son sayfa numarasını bul
            if page == 1 and not last_page:
                last_page = self._find_last_page_from_pagination(soup)
                
                if last_page:
                    print(f"INFO: Son sayfa bulundu: {last_page}", file=sys.stderr)
                    
                    # Zaman filtresi varsa son sayfadan başla
                    if time_filter:
                        page = last_page
                        reverse_order = True
                        print(f"INFO: Son sayfadan başlayarak geriye doğru taranacak (sayfa {last_page})", file=sys.stderr)
                        # İlk sayfayı atla, direkt son sayfaya git
                        continue
                else:
                    print(f"WARNING: Son sayfa bulunamadı", file=sys.stderr)
            
            # Entry'leri bul - çoklu selector stratejisi (önce entry'leri bul, sonra kontrol et)
            # ÖNEMLİ: Ekşi Sözlük'te entry'ler ul#entry-item-list içinde
            entry_elements = soup.find_all('li', {'data-id': True})
            
            # Önce doğru container'ı bul
            if not entry_elements:
                entry_elements = soup.select('ul#entry-item-list > li')
            
            if not entry_elements:
                entry_elements = soup.select('ul#entry-list > li')
            
            if not entry_elements:
                # entry-item-list veya entry-list container'ını bul
                entry_list = (soup.find('ul', id='entry-item-list') or 
                            soup.find('ul', id='entry-list') or 
                            soup.find('ul', class_=re.compile('entry.*list')))
                if entry_list:
                    entry_elements = entry_list.find_all('li', {'data-id': True})
            
            if not entry_elements:
                entry_elements = soup.find_all('li', class_=re.compile('entry'))
            
            if not entry_elements:
                entry_elements = soup.find_all('div', {'class': 'content-item'})
            
            if not entry_elements:
                print(f"INFO: Sayfa {page}'de entry bulunamadı, scraping sonlandırılıyor", file=sys.stderr)
                break
            
            page_entries = []
            all_entries_too_old = True
            
            for elem in entry_elements:
                entry = self._parse_entry(elem)
                if entry:
                    # Zaman filtresi kontrolü
                    if time_filter:
                        entry_dt = self._parse_datetime(entry.get('date', ''))
                        if not entry_dt:
                            # Tarih parse edilemezse, zaman filtresi aktifken entry'yi dahil etme
                            # (güvenli tarafta kal: parse edilemeyen tarihleri hariç tut)
                            continue
                        
                        # Entry'nin zaman filtresi içinde olup olmadığını kontrol et
                        entry_age = datetime.now() - entry_dt
                        if entry_age <= time_filter:
                            # Zaman filtresi içinde, ekle
                            entry['title'] = title
                            page_entries.append(entry)
                            all_entries_too_old = False
                        # Eğer entry çok eskiyse, sadece skip et (durma)
                    else:
                        # Zaman filtresi yok, tüm entry'leri ekle
                        entry['title'] = title
                        page_entries.append(entry)
                        all_entries_too_old = False
            
            entries.extend(page_entries)
            print(f"INFO: Sayfa {page} tamamlandı, {len(page_entries)} entry bulundu (toplam: {len(entries)})", file=sys.stderr)
            
            # Eğer zaman filtresi varsa ve bu sayfadaki TÜM entry'ler belirtilen süreyi aşmışsa dur
            if time_filter and all_entries_too_old:
                if entry_elements:
                    # Sayfada entry var ama hepsi çok eski
                    print(f"INFO: Zaman filtresi nedeniyle scraping durduruldu (sayfa {page}'deki tüm entry'ler belirtilen süreyi ({time_filter.days} gün) aştı)", file=sys.stderr)
                    break
                else:
                    # Sayfada entry yok, bir sonraki sayfaya geç
                    pass
            
            # Sayfa navigasyonu
            if reverse_order:
                # Ters sırada: önceki sayfaya git
                page -= 1
                if page < 1:
                    break
            else:
                # Normal sırada: sonraki sayfaya git
                # Eğer bu sayfada entry yoksa dur (zaman filtresi yoksa)
                if not page_entries and not time_filter:
                    break
                
                # Son sayfa numarasından fazla gidebiliyor muyuz kontrol et
                if last_page and page >= last_page:
                    print(f"INFO: Son sayfa numarasına ulaşıldı ({last_page}), scraping sonlandırılıyor", file=sys.stderr)
                    break
                
                # Bir sonraki sayfaya geç
                page += 1
            
            time.sleep(self.delay)
        
        return entries
    
    def scrape_entry_and_following(self, entry_url: str) -> List[Dict]:
        """Belirli bir entry'den başlayarak sonraki entry'leri scrape eder"""
        entries = []
        
        # Entry URL'inden başlık ve entry ID'yi çıkar
        parsed_url = urlparse(entry_url)
        path_parts = parsed_url.path.strip('/').split('--')
        
        if len(path_parts) < 2:
            print(f"ERROR: Geçersiz entry URL formatı: {entry_url}", file=sys.stderr)
            return entries
        
        title = path_parts[0]
        entry_id = path_parts[1]
        
        print(f"Entry scrape ediliyor: {title} (entry #{entry_id})", file=sys.stderr)
        
        # Önce belirtilen entry'yi bul
        found_start_entry = False
        page = 1
        
        while not found_start_entry:
            if page == 1:
                url = f"{self.BASE_URL}/{title}"
            else:
                url = f"{self.BASE_URL}/{title}?p={page}"
            
            response = self._make_request(url)
            if not response:
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            # Entry'leri bul - çoklu selector stratejisi
            # ÖNEMLİ: Ekşi Sözlük'te entry'ler ul#entry-item-list içinde
            entry_elements = soup.find_all('li', {'data-id': True})
            
            if not entry_elements:
                entry_elements = soup.select('ul#entry-item-list > li')
            
            if not entry_elements:
                entry_elements = soup.select('ul#entry-list > li')
            
            if not entry_elements:
                entry_list = (soup.find('ul', id='entry-item-list') or 
                            soup.find('ul', id='entry-list') or 
                            soup.find('ul', class_=re.compile('entry.*list')))
                if entry_list:
                    entry_elements = entry_list.find_all('li', {'data-id': True})
            
            if not entry_elements:
                entry_elements = soup.find_all('li', class_=re.compile('entry'))
            
            if not entry_elements:
                entry_elements = soup.find_all('div', {'class': 'content-item'})
            
            if not entry_elements:
                break
            
            for elem in entry_elements:
                entry = self._parse_entry(elem)
                if entry and entry.get('entry_id') == entry_id:
                    found_start_entry = True
                    entry['title'] = title
                    entries.append(entry)
                    print(f"INFO: Başlangıç entry bulundu", file=sys.stderr)
                    break
            
            if found_start_entry:
                # Bu sayfadaki kalan entry'leri de ekle
                start_index = None
                for i, elem in enumerate(entry_elements):
                    parsed = self._parse_entry(elem)
                    if parsed and parsed.get('entry_id') == entry_id:
                        start_index = i
                        break
                
                if start_index is not None:
                    for elem in entry_elements[start_index + 1:]:
                        entry = self._parse_entry(elem)
                        if entry:
                            entry['title'] = title
                            entries.append(entry)
            
            if found_start_entry:
                break
            
            page += 1
            time.sleep(self.delay)
            
            # Sayfa limiti (sonsuz döngüyü önlemek için)
            if page > 100:
                print(f"WARNING: Başlangıç entry bulunamadı (100 sayfa limit)", file=sys.stderr)
                break
        
        # Sonraki sayfalardaki entry'leri de scrape et
        if found_start_entry:
            page += 1
            while True:
                url = f"{self.BASE_URL}/{title}?p={page}"
                response = self._make_request(url)
                if not response:
                    break
                
                soup = BeautifulSoup(response.content, 'html.parser')
                # Entry'leri bul - ul#entry-item-list öncelikli
                entry_elements = soup.find_all('li', {'data-id': True})
                
                if not entry_elements:
                    entry_elements = soup.select('ul#entry-item-list > li')
                
                if not entry_elements:
                    entry_elements = soup.select('ul#entry-list > li')
                
                if not entry_elements:
                    entry_list = (soup.find('ul', id='entry-item-list') or 
                                soup.find('ul', id='entry-list'))
                    if entry_list:
                        entry_elements = entry_list.find_all('li', {'data-id': True})
                
                if not entry_elements:
                    entry_elements = soup.find_all('div', {'class': 'content-item'})
                
                if not entry_elements:
                    break
                
                page_entries = []
                for elem in entry_elements:
                    entry = self._parse_entry(elem)
                    if entry:
                        entry['title'] = title
                        page_entries.append(entry)
                
                if not page_entries:
                    break
                
                entries.extend(page_entries)
                print(f"INFO: Sayfa {page} tamamlandı, {len(page_entries)} entry bulundu (toplam: {len(entries)})", file=sys.stderr)
                
                next_link = soup.find('a', {'rel': 'next'}) or soup.find('a', string=re.compile(r'→|sonraki', re.I))
                if not next_link:
                    break
                
                page += 1
                time.sleep(self.delay)
        
        return entries


def main():
    parser = argparse.ArgumentParser(
        description='Ekşi Sözlük Scraper - AI-friendly output üreten terminal tabanlı scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  # Başlıktaki tüm entry'leri scrape et:
  python eksisozluk_scraper.py "python"

  # Son 1 günlük entry'leri scrape et:
  python eksisozluk_scraper.py "python" --days 1

  # Son 1 haftalık entry'leri scrape et:
  python eksisozluk_scraper.py "python" --days 7

  # Belirli bir entry'den itibaren scrape et:
  python eksisozluk_scraper.py "https://eksisozluk.com/python--123456"

  # Özel parametreler:
  python eksisozluk_scraper.py "python" --delay 2.0 --max-retries 5
        """
    )
    
    parser.add_argument('input', help='Başlık adı veya entry URL\'si')
    parser.add_argument('--days', type=int, help='Son N günlük entry\'leri scrape et')
    parser.add_argument('--weeks', type=int, help='Son N haftalık entry\'leri scrape et')
    parser.add_argument('--delay', type=float, default=1.5, help='Request\'ler arası bekleme süresi (saniye, varsayılan: 1.5)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maksimum tekrar deneme sayısı (varsayılan: 3)')
    parser.add_argument('--retry-delay', type=float, default=5.0, help='Retry arası bekleme süresi (saniye, varsayılan: 5.0)')
    parser.add_argument('--timeout', type=float, default=60.0, help='Toplam timeout süresi (saniye, varsayılan: 60.0)')
    parser.add_argument('--output', '-o', help='Çıktı dosyası (varsayılan: stdout)')
    
    args = parser.parse_args()
    
    # Zaman filtresi hesapla
    time_filter = None
    if args.days:
        time_filter = timedelta(days=args.days)
    elif args.weeks:
        time_filter = timedelta(weeks=args.weeks)
    
    # Scraper oluştur
    scraper = EksisozlukScraper(
        delay=args.delay,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout
    )
    
    # Input'un URL mi başlık mı olduğunu kontrol et
    if args.input.startswith('http://') or args.input.startswith('https://'):
        entries = scraper.scrape_entry_and_following(args.input)
    else:
        entries = scraper.scrape_title(args.input, time_filter)
    
    # Çıktıyı hazırla
    output_data = {
        'scrape_info': {
            'timestamp': datetime.now().isoformat(),
            'total_entries': len(entries),
            'input': args.input,
            'time_filter': f"{args.days} days" if args.days else (f"{args.weeks} weeks" if args.weeks else None)
        },
        'entries': entries
    }
    
    # JSON olarak çıktı ver
    output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"INFO: Çıktı {args.output} dosyasına kaydedildi", file=sys.stderr)
    else:
        print(output_json)


if __name__ == '__main__':
    main()

