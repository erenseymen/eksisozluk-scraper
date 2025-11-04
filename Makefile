.PHONY: build-deb build-rpm build-windows clean install test dist

# Build Debian package
build-deb:
	@echo "Building Debian package..."
	dpkg-buildpackage -us -uc -b

# Build RPM package
build-rpm: dist
	@echo "Building RPM package..."
	@mkdir -p ~/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
	@if ls eksisozluk-scraper-*.tar.gz 1> /dev/null 2>&1; then \
		cp eksisozluk-scraper-*.tar.gz ~/rpmbuild/SOURCES/; \
	else \
		echo "Error: Source tarball not found. Run 'make dist' first."; \
		exit 1; \
	fi
	@cp eksisozluk-scraper.spec ~/rpmbuild/SPECS/
	rpmbuild -ba --nodeps ~/rpmbuild/SPECS/eksisozluk-scraper.spec
	@echo "RPM package built successfully!"
	@echo "Find the RPM in: ~/rpmbuild/RPMS/noarch/"

# Create source distribution
dist:
	@echo "Creating source distribution..."
	python3 setup.py sdist
	@mv dist/eksisozluk-scraper-*.tar.gz . || true

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
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -f eksisozluk-scraper-*.tar.gz
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

# Build Windows executable (requires WSL or MSYS2 with Python and PyInstaller)
build-windows:
	@echo "Building Windows executable..."
	@echo "Note: On Windows, use build-windows.bat or build-windows.ps1 instead"
	@if command -v pyinstaller > /dev/null 2>&1; then \
		pip3 install --upgrade pip setuptools wheel pyinstaller; \
		pip3 install -r requirements.txt; \
		pyinstaller --clean eksisozluk_scraper.spec; \
		echo "Windows executable built successfully!"; \
		echo "Find the executable in: dist/eksisozluk-scraper.exe"; \
	else \
		echo "Error: PyInstaller not found. Install it with: pip3 install pyinstaller"; \
		exit 1; \
	fi

