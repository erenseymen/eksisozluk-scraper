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
                response.raise_for_status()
                return response
                
            except Exception as e:
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
            
            # Tarih aralığı formatı: "20.02.1999 ~ 06.05.2007 01:16" - son tarihi al
            if ' ~ ' in date_str:
                date_str = date_str.split(' ~ ')[-1].strip()
            
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
    
    def _find_last_page(self, soup: BeautifulSoup, title: str) -> Optional[int]:
        """Son sayfa numarasını binary search ile bulur"""
        try:
            # Önce pagination linklerini kontrol et
            pagination_links = soup.find_all('a', href=re.compile(r'p=\d+'))
            
            max_page_from_links = 1
            for link in pagination_links:
                href = link.get('href', '')
                page_match = re.search(r'p=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page_from_links = max(max_page_from_links, page_num)
            
            # Eğer pagination linklerinden sayfa bulamazsak, binary search yap
            if max_page_from_links == 1:
                # Binary search ile son sayfayı bul
                low, high = 1, 1000  # Başlangıç aralığı
                last_valid_page = 1
                
                while low <= high:
                    mid = (low + high) // 2
                    test_url = f"{self.BASE_URL}/{title}?p={mid}"
                    response = self._make_request(test_url)
                    
                    if response:
                        test_soup = BeautifulSoup(response.content, 'html.parser')
                        test_entries = test_soup.find_all('li', {'data-id': True})
                        
                        if test_entries:
                            last_valid_page = mid
                            low = mid + 1
                            time.sleep(0.5)  # Rate limiting
                        else:
                            high = mid - 1
                    else:
                        high = mid - 1
                
                if last_valid_page > 1:
                    print(f"INFO: Binary search ile son sayfa bulundu: {last_valid_page}", file=sys.stderr)
                    return last_valid_page
            
            return max_page_from_links if max_page_from_links > 1 else None
        except Exception as e:
            print(f"WARNING: Son sayfa bulunamadı: {e}", file=sys.stderr)
            return None
    
    def scrape_title(self, title: str, time_filter: Optional[timedelta] = None) -> List[Dict]:
        """Bir başlıktaki tüm entry'leri scrape eder"""
        entries = []
        page = 1
        
        print(f"Başlık scrape ediliyor: {title}", file=sys.stderr)
        
        # Eğer zaman filtresi varsa, en yeni entry'ler genelde son sayfalarda
        # reverse_order başlangıçta False, sadece gerekirse True yapılacak
        reverse_order = False
        
        while True:
            # Başlık URL'i oluştur
            if page == 1:
                url = f"{self.BASE_URL}/{title}"
            else:
                url = f"{self.BASE_URL}/{title}?p={page}"
            
            response = self._make_request(url)
            if not response:
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
            
            # Eğer ilk sayfadaysak ve zaman filtresi varsa, son sayfayı bul
            if page == 1 and time_filter and not reverse_order and entry_elements:
                # Önce pagination'dan son sayfayı bulmaya çalış (hızlı kontrol)
                last_page = None
                try:
                    # Hızlı kontrol - sadece pagination linklerine bak, binary search yapma
                    pagination_links = soup.find_all('a', href=re.compile(r'p=\d+'))
                    max_page_from_links = 1
                    for link in pagination_links:
                        href = link.get('href', '')
                        page_match = re.search(r'p=(\d+)', href)
                        if page_match:
                            page_num = int(page_match.group(1))
                            max_page_from_links = max(max_page_from_links, page_num)
                    
                    if max_page_from_links > 1:
                        last_page = max_page_from_links
                        print(f"INFO: Pagination'dan son sayfa bulundu: {last_page}", file=sys.stderr)
                except Exception as e:
                    pass
                
                # Eğer pagination sadece 2 sayfa gösteriyorsa ama entry'ler çok eskiyse,
                # gerçek son sayfa çok daha yüksek olabilir - yüksek sayfaları dene
                if last_page and last_page <= 10:
                    # Pagination'dan bulunan sayfa çok düşükse, yüksek sayfaları dene
                    print(f"INFO: Pagination sadece {last_page} sayfa gösteriyor, yüksek sayfalar deneniyor...", file=sys.stderr)
                    last_page = None  # Yüksek sayfa kontrolü yap
                
                # Eğer pagination'dan bulamazsak veya çok düşükse, yüksek bir sayfadan başla
                if not last_page or last_page == 1:
                    # İlk sayfadaki entry'lerin hepsi eski mi kontrol et
                    first_page_all_old = True
                    for elem in entry_elements[:3]:  # İlk 3 entry'yi kontrol et
                        test_entry = self._parse_entry(elem)
                        if test_entry:
                            entry_dt = self._parse_datetime(test_entry.get('date', ''))
                            if entry_dt:
                                entry_age = datetime.now() - entry_dt
                                if entry_age <= time_filter:
                                    first_page_all_old = False
                                    break
                    
                    # Eğer ilk sayfa tamamen eskiyse, yüksek sayfalardan başla
                    if first_page_all_old:
                        print(f"INFO: İlk sayfa entry'leri çok eski, yeni entry'ler için yüksek sayfalardan başlanıyor...", file=sys.stderr)
                        # Binary search benzeri yaklaşım: önce yüksek sayfaları dene
                        start_pages = [1000, 500, 250, 100, 50, 25, 10, 5]
                        found_recent = False
                        found_page = None
                        
                        for start_page in start_pages:
                            print(f"INFO: Sayfa {start_page} kontrol ediliyor...", file=sys.stderr)
                            test_url = f"{self.BASE_URL}/{title}?p={start_page}"
                            test_response = self._make_request(test_url)
                            if test_response:
                                test_soup = BeautifulSoup(test_response.content, 'html.parser')
                                test_entries = test_soup.find_all('li', {'data-id': True})
                                
                                if test_entries:
                                    print(f"INFO: Sayfa {start_page}'de {len(test_entries)} entry bulundu", file=sys.stderr)
                                    # Bu sayfada yeni entry var mı kontrol et
                                    for test_elem in test_entries[:5]:
                                        test_entry = self._parse_entry(test_elem)
                                        if test_entry:
                                            test_entry_dt = self._parse_datetime(test_entry.get('date', ''))
                                            if test_entry_dt:
                                                test_entry_age = datetime.now() - test_entry_dt
                                                date_text = test_entry.get('date', '')
                                                print(f"INFO:   Entry tarihi: {date_text}, Yaş: {test_entry_age.days} gün", file=sys.stderr)
                                                if test_entry_age <= time_filter:
                                                    print(f"INFO: Sayfa {start_page}'de yeni entry'ler bulundu! (Entry: {date_text})", file=sys.stderr)
                                                    found_page = start_page
                                                    found_recent = True
                                                    break
                                    
                                    if found_recent:
                                        break
                                    
                                    # Eğer bu sayfada entry varsa ama hepsi eskiyse, daha düşük sayfa dene
                                    # (çünkü entry'ler en eskiden en yeniye sıralı, yeni entry'ler daha yüksek sayfalarda)
                                    if not found_recent:
                                        # Sayfanın entry'lerinden birinin tarihini kontrol et
                                        sample_entry = self._parse_entry(test_entries[0])
                                        if sample_entry:
                                            sample_dt = self._parse_datetime(sample_entry.get('date', ''))
                                            if sample_dt:
                                                sample_age = datetime.now() - sample_dt
                                                if sample_age.days > 30:  # Eğer sayfa hala eski entry'ler içeriyorsa, daha yüksek sayfa dene
                                                    continue
                        
                        if found_recent and found_page:
                            page = found_page
                            reverse_order = True
                            print(f"INFO: Sayfa {page}'den geriye doğru tarama başlatılıyor", file=sys.stderr)
                            continue
                        else:
                            print(f"INFO: Yeni entry bulunamadı (belki gerçekten yeni entry yok)", file=sys.stderr)
                else:
                    if last_page > 1:
                        print(f"INFO: En yeni entry'ler için son sayfadan başlanıyor (sayfa {last_page})", file=sys.stderr)
                        page = last_page
                        reverse_order = True
                        continue
            
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
                            # Tarih parse edilemezse, filtreyi atlayalım
                            entry['title'] = title
                            page_entries.append(entry)
                            all_entries_too_old = False
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
            
            # Eğer zaman filtresi varsa ve bu sayfadaki tüm entry'ler çok eskiyse dur
            if time_filter and all_entries_too_old and page_entries:
                print(f"INFO: Zaman filtresi nedeniyle scraping durduruldu (sayfa {page}'deki tüm entry'ler çok eski)", file=sys.stderr)
                # Ters sırada gidiyorsak, geriye doğru devam et
                if reverse_order:
                    page -= 1
                    if page < 1:
                        break
                    time.sleep(self.delay)
                    continue
                else:
                    break
            
            # Sayfa navigasyonu
            if reverse_order:
                # Ters sırada: önceki sayfaya git
                page -= 1
                if page < 1:
                    break
            else:
                # Normal sırada: sonraki sayfaya git
                next_link = soup.find('a', {'rel': 'next'}) or soup.find('a', string=re.compile(r'→|sonraki', re.I))
                if not next_link or (not page_entries and not time_filter):
                    break
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

