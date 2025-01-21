"""Progress tracker for monitoring data collection progress.

This module handles all progress-related calculations and updates,
tracking progress across seasons, designers, and looks.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime

class ProgressTracker:
    """Handles progress tracking and statistics calculations."""

    @staticmethod
    def update_overall_progress(data: Dict[str, Any]) -> Dict[str, Any]:
        """Update overall progress metrics in metadata.
        
        Args:
            data: Current data structure to update
            
        Returns:
            Updated data structure with new progress metrics
            
        Example:
            >>> data = {"metadata": {"overall_progress": {}}, "seasons": [...]}
            >>> updated_data = ProgressTracker.update_overall_progress(data)
        """
        progress_stats = ProgressTracker._calculate_progress_stats(data["seasons"])
        
        # Update progress metrics
        overall = data["metadata"]["overall_progress"]
        overall.update(progress_stats)
        
        # Update timestamp
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        
        return data

    @staticmethod
    def _calculate_progress_stats(seasons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate progress statistics from seasons data.
        
        Args:
            seasons: List of season dictionaries
            
        Returns:
            Dictionary containing calculated progress statistics
        """
        total_seasons = len(seasons)
        completed_seasons = sum(1 for s in seasons if s.get("completed", False))
        
        designer_stats = ProgressTracker._calculate_designer_stats(seasons)
        look_stats = ProgressTracker._calculate_look_stats(seasons)
        
        return {
            "total_seasons": total_seasons,
            "completed_seasons": completed_seasons,
            **designer_stats,
            **look_stats
        }

    @staticmethod
    def _calculate_designer_stats(seasons: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate designer-related statistics.
        
        Args:
            seasons: List of season dictionaries
            
        Returns:
            Dictionary containing designer statistics
        """
        total_designers = 0
        completed_designers = 0
        
        for season in seasons:
            designers = season.get("designers", [])
            total_designers += len(designers)
            completed_designers += sum(
                1 for d in designers if d.get("completed", False)
            )
        
        return {
            "total_designers": total_designers,
            "completed_designers": completed_designers
        }

    @staticmethod
    def _calculate_look_stats(seasons: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate look-related statistics.
        
        Args:
            seasons: List of season dictionaries
            
        Returns:
            Dictionary containing look statistics
        """
        total_looks = 0
        extracted_looks = 0
        
        for season in seasons:
            for designer in season.get("designers", []):
                total_looks += designer.get("total_looks", 0)
                extracted_looks += designer.get("extracted_looks", 0)
        
        return {
            "total_looks": total_looks,
            "extracted_looks": extracted_looks
        }

    @staticmethod
    def get_completion_percentages(data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate completion percentages for different metrics.
        
        Args:
            data: Current data structure
            
        Returns:
            Dictionary containing completion percentages
            
        Example:
            >>> stats = ProgressTracker.get_completion_percentages(data)
            >>> print(f"Season completion: {stats['season_completion']}%")
        """
        progress = data["metadata"]["overall_progress"]
        
        return {
            "season_completion": ProgressTracker._calculate_percentage(
                progress["completed_seasons"],
                progress["total_seasons"]
            ),
            "designer_completion": ProgressTracker._calculate_percentage(
                progress["completed_designers"],
                progress["total_designers"]
            ),
            "look_completion": ProgressTracker._calculate_percentage(
                progress["extracted_looks"],
                progress["total_looks"]
            )
        }

    @staticmethod
    def _calculate_percentage(completed: int, total: int) -> float:
        """Calculate completion percentage.
        
        Args:
            completed: Number of completed items
            total: Total number of items
            
        Returns:
            Completion percentage rounded to 2 decimal places
        """
        if total == 0:
            return 0.0
        return round((completed / total) * 100, 2)

    @staticmethod
    def get_progress_summary(data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a comprehensive progress summary.
        
        Args:
            data: Current data structure
            
        Returns:
            Dictionary containing progress summary
            
        Example:
            >>> summary = ProgressTracker.get_progress_summary(data)
            >>> print(f"Overall progress: {summary['overall_completion']}%")
        """
        percentages = ProgressTracker.get_completion_percentages(data)
        progress = data["metadata"]["overall_progress"]
        
        return {
            "last_updated": data["metadata"]["last_updated"],
            "overall_completion": sum(percentages.values()) / len(percentages),
            "progress_stats": {
                "seasons": f"{progress['completed_seasons']}/{progress['total_seasons']}",
                "designers": f"{progress['completed_designers']}/{progress['total_designers']}",
                "looks": f"{progress['extracted_looks']}/{progress['total_looks']}"
            },
            "completion_percentages": percentages
        }