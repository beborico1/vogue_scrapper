"""Data validation and debugging module for storage operations."""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

class DataValidator:
    """Validates data consistency and tracks storage operations."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.operation_log = []
        
    def validate_designer_context(
        self,
        data: Dict[str, Any],
        season_index: int,
        designer_index: int,
        designer_url: str
    ) -> bool:
        """Validate that indices point to correct designer."""
        try:
            season = data["seasons"][season_index]
            designer = season["designers"][designer_index]
            
            if designer["url"] != designer_url:
                self.logger.error(
                    f"Designer mismatch: Expected {designer_url}, "
                    f"found {designer['url']} at indices [{season_index}, {designer_index}]"
                )
                return False
                
            self._log_operation("validate_context", {
                "season_index": season_index,
                "designer_index": designer_index,
                "designer_url": designer_url,
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False
            
    def validate_look_assignment(
        self,
        data: Dict[str, Any],
        season_index: int,
        designer_index: int,
        look_number: int,
        images: List[Dict[str, str]]
    ) -> bool:
        """Validate look data before assignment."""
        try:
            designer = data["seasons"][season_index]["designers"][designer_index]
            
            # Check if look already exists
            existing_look = None
            for look in designer["looks"]:
                if look["look_number"] == look_number:
                    existing_look = look
                    break
            
            if existing_look and existing_look.get("completed", False):
                self.logger.warning(
                    f"Attempting to modify completed look {look_number} "
                    f"for designer {designer['name']}"
                )
                return False
                
            self._log_operation("validate_look", {
                "season_index": season_index,
                "designer_index": designer_index,
                "look_number": look_number,
                "image_count": len(images),
                "timestamp": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Look validation error: {str(e)}")
            return False
            
    def get_designer_by_url(
        self,
        data: Dict[str, Any],
        designer_url: str
    ) -> Optional[tuple[int, int]]:
        """Find correct indices for a designer URL."""
        for season_idx, season in enumerate(data["seasons"]):
            for designer_idx, designer in enumerate(season["designers"]):
                if designer["url"] == designer_url:
                    return (season_idx, designer_idx)
        return None
    
    def _log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Log storage operation details."""
        self.operation_log.append({
            "operation": operation,
            "details": details
        })
        
    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get log of all storage operations."""
        return self.operation_log

    def analyze_storage_operations(self) -> Dict[str, Any]:
        """Analyze storage operations for patterns and issues."""
        analysis = {
            "total_operations": len(self.operation_log),
            "operations_by_type": {},
            "potential_issues": []
        }
        
        last_designer_url = None
        for op in self.operation_log:
            # Track operation types
            op_type = op["operation"]
            analysis["operations_by_type"][op_type] = \
                analysis["operations_by_type"].get(op_type, 0) + 1
                
            # Check for rapid designer switches
            if op_type == "validate_context":
                current_url = op["details"]["designer_url"]
                if last_designer_url and current_url != last_designer_url:
                    analysis["potential_issues"].append({
                        "type": "designer_switch",
                        "from_url": last_designer_url,
                        "to_url": current_url,
                        "timestamp": op["details"]["timestamp"]
                    })
                last_designer_url = current_url
        
        return analysis