# Parallel Processing for Vogue Runway Scraper

This package provides parallel processing capabilities for the Vogue Runway scraper, allowing multiple components of the scraping process to run concurrently for improved performance.

## Architecture

The parallel processing system is organized into the following modules:

1. **parallel_processor.py** - Main manager class coordinating all parallel operations
2. **parallel_season_processor.py** - Handles season-level parallel processing
3. **parallel_designer_processor.py** - Handles designer-level parallel processing
4. **parallel_look_processor.py** - Handles look-level parallel processing
5. **parallel_utils.py** - Utility functions for parallel processing

## Parallelization Strategies

The system supports three levels of parallelism:

### 1. Multi-Season Parallelism

Process multiple seasons concurrently, each with its own browser instance. This is the highest level of parallelization and provides the greatest speed improvement, especially for initial data collection.

```python
manager = ParallelProcessingManager(max_workers=4, mode="multi-season")
manager.initialize_resources()
result = manager.process_seasons_parallel(seasons)
```

### 2. Multi-Designer Parallelism

Process multiple designers within a season concurrently, each with its own browser instance. This is the recommended approach for most scraping operations as it provides a good balance of performance and resource usage.

```python
manager = ParallelProcessingManager(max_workers=4, mode="multi-designer")
manager.initialize_resources()
result = manager.process_designers_parallel(season)
```

### 3. Multi-Look Parallelism

Process multiple looks for a designer concurrently, creating separate browser instances for each look. This approach is more resource-intensive but can speed up processing for designers with many looks.

```python
manager = ParallelProcessingManager(max_workers=4, mode="multi-look")
manager.initialize_resources()
result = manager.process_looks_parallel(designer_url, season_index, designer_index)
```

## Resource Management

The system includes several features for managing resources effectively:

- Automatic driver pool management
- Authentication sharing between browser instances
- Thread-safe storage operations
- Progress tracking and status monitoring
- Resource usage monitoring (CPU/memory)

## Error Handling

The parallel processing system includes robust error handling:

- Each worker operates independently, so failures in one thread don't affect others
- Comprehensive error logging and tracking
- Retry mechanisms for transient errors
- Session management to prevent data corruption

## Usage

To use parallel processing in the Vogue Runway scraper:

```python
from src.parallel_processor import ParallelProcessingManager

# Create a parallel processing manager
manager = ParallelProcessingManager(
    max_workers=4,              # Number of parallel workers
    mode="multi-designer",      # Parallelization strategy
    checkpoint_file="data.json" # Optional checkpoint file
)

# Initialize resources (drivers, storage)
manager.initialize_resources()

try:
    # Process a season with parallel designers
    result = manager.process_designers_parallel(season)
    
    # Check results
    print(f"Processed {result['processed_designers']} designers")
    print(f"Completed {result['completed_designers']} designers")
    
    if result["errors"]:
        print(f"Encountered {len(result['errors'])} errors")
        
finally:
    # Clean up resources
    manager.cleanup_resources()
```

## Performance Considerations

- **Memory Usage**: Each browser instance requires approximately 200-300MB of RAM
- **CPU Usage**: Browser instances can be CPU-intensive, especially when loading pages
- **Network**: Multiple concurrent connections may trigger rate limiting on the target site
- **Storage**: Ensure thread-safe storage operations to prevent data corruption

For optimal performance, adjust the `max_workers` parameter based on your system's capabilities and the specific scraping task.