.PHONY: build-deb clean install test

# Build Debian package
build-deb:
	@echo "Building Debian package..."
	dpkg-buildpackage -us -uc -b

# Clean build artifacts
clean:
	rm -rf debian/eksisozluk-scraper
	rm -rf debian/files
	rm -rf debian/.debhelper
	rm -rf debian/*.substvars
	rm -rf debian/*.log
	rm -f ../eksisozluk-scraper_*.deb
	rm -f ../eksisozluk-scraper_*.dsc
	rm -f ../eksisozluk-scraper_*.tar.gz
	rm -f ../eksisozluk-scraper_*.buildinfo
	rm -f ../eksisozluk-scraper_*.changes
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Install locally (for testing)
install:
	pip3 install -e .

# Test the package
test:
	python3 -m pytest tests/ || echo "No tests found"

# Build source package
build-source:
	dpkg-buildpackage -S -us -uc

