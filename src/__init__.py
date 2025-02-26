# Update src/__init__.py to fix the MRO error

"""Vogue Runway Scraper package.

This package provides functionality for scraping fashion show data from Vogue Runway
with support for parallel processing and different storage backends.
"""

# Instead of trying to modify the base class after import,
# let's create a proper inheritance structure

def initialize_scraper_classes():
    """Initialize the scraper classes with proper inheritance."""
    from .scraper_orchestrator import VogueRunwayScraper
    from .scraper_orchestrator_part2 import VogueRunwayScraperPart2
    
    # Create a new class that properly inherits from both
    class CombinedVogueRunwayScraper(VogueRunwayScraper, VogueRunwayScraperPart2):
        """Combined scraper class with all functionality."""
        pass
    
    # Replace the original class in the module
    import sys
    from . import scraper_orchestrator
    scraper_orchestrator.VogueRunwayScraper = CombinedVogueRunwayScraper
    sys.modules['src.scraper_orchestrator'].VogueRunwayScraper = CombinedVogueRunwayScraper
    
    return CombinedVogueRunwayScraper

# Initialize and get the combined class
VogueRunwayScraper = initialize_scraper_classes()

__all__ = ['VogueRunwayScraper']