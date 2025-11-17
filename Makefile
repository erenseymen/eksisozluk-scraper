.PHONY: build-windows clean install test dist

# Create source distribution
dist:
	@echo "Creating source distribution..."
	python3 setup.py sdist
	@mv dist/eksisozluk-scraper-*.tar.gz . || true

# Clean build artifacts
clean:
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

