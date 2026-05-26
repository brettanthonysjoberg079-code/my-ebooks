"""
Airtable Service
CRUD operations with REST API and local JSON fallback for fault tolerance.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os

from config import config


@dataclass
class AirtableRecord:
    """Structured Airtable record with metadata."""
    id: str
    title: str
    author: Optional[str]
    niche: Optional[str]
    current_status: str  # e.g., "draft", "generated", "compiled", "published"
    render_path: Optional[str]
    created_at: str
    updated_at: str
    extra_fields: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class AirtableService:
    """
    Airtable API wrapper with graceful fallback to local JSON state files.
    Handles CRUD operations and provides resilience when the API is unavailable.
    """

    def __init__(self):
        """Initialize Airtable service."""
        self.token = config.airtable_token
        self.base_id = config.airtable_base_id
        self.table_name = config.airtable_table_name
        self.state_dir = config.pipeline_state_dir
        self.fallback_file = os.path.join(self.state_dir, "airtable_fallback.json")
        
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table_name}"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        self._fallback_cache = self._load_fallback_cache()
        
        if self.token and self.base_id:
            print(f"✓ Airtable service initialized (base: {self.base_id})")
        else:
            print("⚠ Airtable credentials missing; will use local JSON fallback only")

    def _load_fallback_cache(self) -> Dict[str, AirtableRecord]:
        """Load fallback JSON cache from disk."""
        os.makedirs(self.state_dir, exist_ok=True)
        
        if not os.path.exists(self.fallback_file):
            return {}
        
        try:
            with open(self.fallback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cache = {}
                for record_id, record_data in data.items():
                    cache[record_id] = AirtableRecord(**record_data)
                print(f"✓ Loaded {len(cache)} records from fallback cache")
                return cache
        except Exception as e:
            print(f"✗ Failed to load fallback cache: {e}")
            return {}

    def _save_fallback_cache(self) -> None:
        """Save current cache to fallback JSON file."""
        try:
            data = {record_id: record.to_dict() for record_id, record in self._fallback_cache.items()}
            with open(self.fallback_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"✓ Fallback cache saved ({len(self._fallback_cache)} records)")
        except Exception as e:
            print(f"✗ Failed to save fallback cache: {e}")

    def create_record(
        self,
        title: str,
        author: Optional[str] = None,
        niche: Optional[str] = None,
        status: str = "draft",
        render_path: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> Optional[AirtableRecord]:
        """
        Create a new book record in Airtable.
        Falls back to local JSON if API unavailable.
        
        Args:
            title: Book title
            author: Author name
            niche: Book niche/category
            status: Current production status
            render_path: Path to output file
            extra_fields: Additional fields specific to your base
        
        Returns:
            AirtableRecord if successful, None on error
        """
        now = datetime.utcnow().isoformat()
        
        # Try Airtable API first
        if self.token and self.base_id:
            try:
                import requests
                
                payload = {
                    "records": [{
                        "fields": {
                            "Title": title,
                            "Author": author or "",
                            "Niche": niche or "",
                            "Current Status": status,
                            "Render Path": render_path or "",
                            **(extra_fields or {})
                        }
                    }]
                }
                
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=config.request_timeout_seconds
                )
                
                if response.status_code == 200:
                    data = response.json()
                    record_data = data['records'][0]
                    record = AirtableRecord(
                        id=record_data['id'],
                        title=title,
                        author=author,
                        niche=niche,
                        current_status=status,
                        render_path=render_path,
                        created_at=now,
                        updated_at=now,
                        extra_fields=extra_fields
                    )
                    
                    # Cache locally
                    self._fallback_cache[record.id] = record
                    self._save_fallback_cache()
                    
                    print(f"✓ Created Airtable record: {record.id}")
                    return record
                else:
                    print(f"✗ Airtable API error: {response.status_code} - {response.text[:200]}")
            
            except Exception as e:
                print(f"✗ Airtable API call failed: {e}")
        
        # Fallback: use local JSON
        print("  → Using local JSON fallback")
        record_id = f"local_{datetime.utcnow().timestamp()}"
        record = AirtableRecord(
            id=record_id,
            title=title,
            author=author,
            niche=niche,
            current_status=status,
            render_path=render_path,
            created_at=now,
            updated_at=now,
            extra_fields=extra_fields
        )
        
        self._fallback_cache[record_id] = record
        self._save_fallback_cache()
        
        return record

    def update_record(
        self,
        record_id: str,
        updates: Dict[str, Any]
    ) -> Optional[AirtableRecord]:
        """
        Update an existing record.
        
        Args:
            record_id: Airtable record ID
            updates: Dict of fields to update
        
        Returns:
            Updated AirtableRecord or None on error
        """
        # Try Airtable API first
        if self.token and self.base_id:
            try:
                import requests
                
                payload = {
                    "records": [{
                        "id": record_id,
                        "fields": updates
                    }]
                }
                
                response = requests.patch(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=config.request_timeout_seconds
                )
                
                if response.status_code == 200:
                    print(f"✓ Updated Airtable record: {record_id}")
                    
                    # Update cache
                    if record_id in self._fallback_cache:
                        record = self._fallback_cache[record_id]
                        for key, value in updates.items():
                            if hasattr(record, key.lower()):
                                setattr(record, key.lower(), value)
                        record.updated_at = datetime.utcnow().isoformat()
                        self._save_fallback_cache()
                    
                    return self._fallback_cache.get(record_id)
                else:
                    print(f"✗ Airtable API error: {response.status_code}")
            
            except Exception as e:
                print(f"✗ Airtable update failed: {e}")
        
        # Fallback: update local cache
        print("  → Using local JSON fallback")
        if record_id in self._fallback_cache:
            record = self._fallback_cache[record_id]
            for key, value in updates.items():
                key_lower = key.lower().replace(" ", "_")
                if hasattr(record, key_lower):
                    setattr(record, key_lower, value)
            record.updated_at = datetime.utcnow().isoformat()
            self._save_fallback_cache()
            return record
        
        return None

    def get_record(self, record_id: str) -> Optional[AirtableRecord]:
        """
        Retrieve a single record by ID.
        
        Args:
            record_id: Airtable record ID
        
        Returns:
            AirtableRecord or None if not found
        """
        # Check local cache first
        if record_id in self._fallback_cache:
            return self._fallback_cache[record_id]
        
        # Try API
        if self.token and self.base_id:
            try:
                import requests
                
                url = f"{self.base_url}/{record_id}"
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=config.request_timeout_seconds
                )
                
                if response.status_code == 200:
                    data = response.json()
                    fields = data.get('fields', {})
                    record = AirtableRecord(
                        id=data['id'],
                        title=fields.get('Title', ''),
                        author=fields.get('Author'),
                        niche=fields.get('Niche'),
                        current_status=fields.get('Current Status', 'unknown'),
                        render_path=fields.get('Render Path'),
                        created_at=fields.get('created_at', datetime.utcnow().isoformat()),
                        updated_at=datetime.utcnow().isoformat()
                    )
                    
                    # Cache it
                    self._fallback_cache[record_id] = record
                    return record
            
            except Exception as e:
                print(f"✗ Failed to fetch record {record_id}: {e}")
        
        return None

    def list_records(self, filter_formula: Optional[str] = None) -> List[AirtableRecord]:
        """
        List all records, optionally filtered by Airtable formula.
        
        Args:
            filter_formula: Optional Airtable filter formula
        
        Returns:
            List of AirtableRecord objects
        """
        # Try API first
        if self.token and self.base_id:
            try:
                import requests
                
                params = {}
                if filter_formula:
                    params['filterByFormula'] = filter_formula
                
                response = requests.get(
                    self.base_url,
                    headers=self.headers,
                    params=params,
                    timeout=config.request_timeout_seconds
                )
                
                if response.status_code == 200:
                    data = response.json()
                    records = []
                    
                    for record_data in data.get('records', []):
                        fields = record_data.get('fields', {})
                        record = AirtableRecord(
                            id=record_data['id'],
                            title=fields.get('Title', ''),
                            author=fields.get('Author'),
                            niche=fields.get('Niche'),
                            current_status=fields.get('Current Status', 'unknown'),
                            render_path=fields.get('Render Path'),
                            created_at=fields.get('created_at', datetime.utcnow().isoformat()),
                            updated_at=datetime.utcnow().isoformat()
                        )
                        records.append(record)
                        
                        # Cache it
                        self._fallback_cache[record.id] = record
                    
                    self._save_fallback_cache()
                    print(f"✓ Retrieved {len(records)} records from Airtable")
                    return records
            
            except Exception as e:
                print(f"✗ Failed to list Airtable records: {e}")
        
        # Fallback: return from cache
        print("  → Using local cache for list")
        return list(self._fallback_cache.values())

    def delete_record(self, record_id: str) -> bool:
        """
        Delete a record from Airtable.
        
        Args:
            record_id: Airtable record ID
        
        Returns:
            True if successful, False otherwise
        """
        # Try API first
        if self.token and self.base_id:
            try:
                import requests
                
                url = f"{self.base_url}/{record_id}"
                response = requests.delete(
                    url,
                    headers=self.headers,
                    timeout=config.request_timeout_seconds
                )
                
                if response.status_code == 200:
                    print(f"✓ Deleted Airtable record: {record_id}")
                    
                    # Remove from cache
                    if record_id in self._fallback_cache:
                        del self._fallback_cache[record_id]
                        self._save_fallback_cache()
                    
                    return True
            
            except Exception as e:
                print(f"✗ Failed to delete record {record_id}: {e}")
        
        # Fallback: remove from local cache
        if record_id in self._fallback_cache:
            del self._fallback_cache[record_id]
            self._save_fallback_cache()
            print(f"  → Removed from local cache: {record_id}")
            return True
        
        return False

    def get_cache_summary(self) -> Dict[str, Any]:
        """Get summary statistics of cached records."""
        statuses = {}
        for record in self._fallback_cache.values():
            status = record.current_status
            statuses[status] = statuses.get(status, 0) + 1
        
        return {
            "total_records": len(self._fallback_cache),
            "status_breakdown": statuses,
            "cache_file": self.fallback_file
        }
