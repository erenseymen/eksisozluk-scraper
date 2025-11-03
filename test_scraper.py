#!/usr/bin/env python3
"""
Ekşi Sözlük Scraper Automated Tests
Test scripts for verification of scraper functionality
"""

import sys
import json
import time
import os
from contextlib import contextmanager
from datetime import timedelta
from eksisozluk_scraper import EksisozlukScraper


@contextmanager
def suppress_stderr():
    """Context manager to suppress stderr output"""
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test_header(test_name: str):
    """Print formatted test header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}TEST: {test_name}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print formatted test result"""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"{test_name}: {status}")
    if details:
        print(f"  {details}")


def test_1_basic_scraping():
    """Test 1: Basic scraping without time filter"""
    print_test_header("Basic Scraping (No Time Filter)")
    
    scraper = EksisozlukScraper()
    with suppress_stderr():
        entries = scraper.scrape_title("gauge", time_filter=None)
    
    passed = len(entries) > 0
    details = f"Found {len(entries)} entries"
    print_result("Basic scraping", passed, details)
    
    return passed, len(entries)


def test_2_pagination_stops_at_last_page():
    """Test 2: Verify scraper stops at the last page"""
    print_test_header("Pagination Stop at Last Page")
    
    scraper = EksisozlukScraper()
    
    # Mock the internal method to count pages
    pages_visited = []
    original_make_request = scraper._make_request
    
    def counting_make_request(url):
        # Extract page number from URL
        if '?p=' in url:
            page_match = scraper.__class__.__module__.split('.')[-1]
            # Simple regex for page number
            import re
            match = re.search(r'[?&]p=(\d+)', url)
            if match:
                pages_visited.append(int(match.group(1)))
        return original_make_request(url)
    
    scraper._make_request = counting_make_request
    
    with suppress_stderr():
        entries = scraper.scrape_title("gauge", time_filter=None)
    
    # Restore original method
    scraper._make_request = original_make_request
    
    # Check if we visited pages 1, 2, 3 and stopped
    passed = len(set(pages_visited)) <= 3  # Should visit max 3 pages
    details = f"Pages visited: {sorted(set(pages_visited))}"
    print_result("Pagination stops correctly", passed, details)
    
    return passed, len(entries)


def test_3_time_filter_reverse_order():
    """Test 3: Time filter uses reverse order (from last page)"""
    print_test_header("Time Filter Reverse Order")
    
    scraper = EksisozlukScraper()
    
    # Track which URL is accessed first after page 1
    accessed_urls = []
    original_make_request = scraper._make_request
    
    def tracking_make_request(url):
        accessed_urls.append(url)
        return original_make_request(url)
    
    scraper._make_request = tracking_make_request
    
    with suppress_stderr():
        entries = scraper.scrape_title("gauge", time_filter=timedelta(days=1))
    
    # Restore original method
    scraper._make_request = original_make_request
    
    # Should go to page 3 first (reverse order)
    has_reverse_order = any('?p=3' in url for url in accessed_urls[1:3])  # After page 1
    details = f"URLs accessed: {[u.split('?')[0] + '...' if '?' in u else u for u in accessed_urls[1:4]]}"
    print_result("Reverse order for time filter", has_reverse_order, details)
    
    return has_reverse_order, len(entries)


def test_4_pagination_format():
    """Test 4: Verify correct pagination URL format"""
    print_test_header("Pagination URL Format")
    
    scraper = EksisozlukScraper()
    accessed_urls = []
    original_make_request = scraper._make_request
    
    def tracking_make_request(url):
        accessed_urls.append(url)
        return original_make_request(url)
    
    scraper._make_request = tracking_make_request
    
    with suppress_stderr():
        entries = scraper.scrape_title("gauge", time_filter=None)
    
    scraper._make_request = original_make_request
    
    # Check URLs use the correct format: /slug--id?p=X
    correct_format = all(
        '/gauge--93891' in url or page == 1
        for page, url in enumerate(accessed_urls, 1)
    )
    details = f"First few URLs: {accessed_urls[:3]}"
    print_result("Correct pagination format", correct_format, details)
    
    return correct_format, None


def test_5_last_page_count():
    """Test 5: Verify last page count is read correctly"""
    print_test_header("Last Page Count Detection")
    
    import cloudscraper
    from bs4 import BeautifulSoup
    
    scraper_session = cloudscraper.create_scraper()
    response = scraper_session.get('https://eksisozluk.com/gauge')
    soup = BeautifulSoup(response.content, 'html.parser')
    
    pagination_div = soup.find('div', class_='pager')
    data_pagecount = pagination_div.get('data-pagecount') if pagination_div else None
    
    # Test our method
    test_scraper = EksisozlukScraper()
    detected_last_page = test_scraper._find_last_page_from_pagination(soup)
    
    passed = detected_last_page == int(data_pagecount) if data_pagecount else False
    details = f"data-pagecount: {data_pagecount}, detected: {detected_last_page}"
    print_result("Last page detection", passed, details)
    
    return passed, detected_last_page


def test_6_entry_structure():
    """Test 6: Verify entry structure and required fields"""
    print_test_header("Entry Structure Validation")
    
    scraper = EksisozlukScraper()
    with suppress_stderr():
        entries = scraper.scrape_title("gauge", time_filter=None)
    
    if not entries:
        print_result("Entry structure", False, "No entries found")
        return False, None
    
    first_entry = entries[0]
    required_fields = ['entry_id', 'content', 'title']
    
    has_all_fields = all(field in first_entry for field in required_fields)
    missing_fields = [f for f in required_fields if f not in first_entry]
    
    details = f"Fields present: {list(first_entry.keys())}" if has_all_fields else f"Missing: {missing_fields}"
    print_result("Entry structure", has_all_fields, details)
    
    return has_all_fields, len(entries)


def test_7_rate_limiting():
    """Test 7: Verify rate limiting (delay between requests)"""
    print_test_header("Rate Limiting")
    
    scraper = EksisozlukScraper(delay=0.1)  # Short delay for testing
    start_time = time.time()
    
    with suppress_stderr():
        entries = scraper.scrape_title("gauge", time_filter=None)
    
    elapsed = time.time() - start_time
    min_expected_time = 0.1 * 3  # At least 0.1s per request * 3 pages
    
    passed = elapsed >= min_expected_time
    details = f"Elapsed: {elapsed:.2f}s (expected at least {min_expected_time:.2f}s)"
    print_result("Rate limiting", passed, details)
    
    return passed, elapsed


def run_all_tests():
    """Run all tests and print summary"""
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"{Colors.BOLD}AUTOMATED TEST SUITE FOR EKŞI SÖZLÜK SCRAPER")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}")
    
    tests = [
        ("Basic Scraping", test_1_basic_scraping),
        ("Pagination Stop", test_2_pagination_stops_at_last_page),
        ("Time Filter Reverse", test_3_time_filter_reverse_order),
        ("Pagination Format", test_4_pagination_format),
        ("Last Page Detection", test_5_last_page_count),
        ("Entry Structure", test_6_entry_structure),
        ("Rate Limiting", test_7_rate_limiting),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed, data = test_func()
            results.append((test_name, passed, data))
        except Exception as e:
            print(f"\n{Colors.RED}ERROR in {test_name}: {str(e)}{Colors.RESET}")
            results.append((test_name, False, None))
    
    # Print summary
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"{Colors.BOLD}TEST SUMMARY")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)
    
    for test_name, passed, data in results:
        print_result(test_name, passed, f"Data: {data}" if data is not None else "")
    
    print(f"\n{Colors.BOLD}Overall: {passed_count}/{total_count} tests passed{Colors.RESET}\n")
    
    # Return exit code
    return 0 if passed_count == total_count else 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)

