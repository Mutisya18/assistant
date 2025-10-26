"""CSV data management with SQLite caching"""
import logging
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class DataManager:
    """Manages CSV data with SQLite cache for fast lookups"""
    
    def __init__(self, warehouse_file: str, reasons_file: str):
        self.warehouse_file = Path(warehouse_file)
        self.reasons_file = Path(reasons_file)
        
        # Create cache directory
        self.cache_dir = Path("processors/digital_lending/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_db = self.cache_dir / "lending.db"
        
        # Load data and build cache
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Initialize SQLite cache from CSV files"""
        logger.info("Initializing data cache...")
        
        conn = sqlite3.connect(self.cache_db)
        
        try:
            # Load warehouse data
            if self.warehouse_file.exists():
                warehouse_df = pd.read_csv(self.warehouse_file)
                warehouse_df['ACCOUNT_NUMBER'] = warehouse_df['ACCOUNT_NUMBER'].astype(str).str.strip()
                warehouse_df.to_sql('warehouse', conn, if_exists='replace', index=False)
                logger.info(f"Cached {len(warehouse_df)} warehouse records")
            
            # Load reasons data
            if self.reasons_file.exists():
                reasons_df = pd.read_csv(self.reasons_file)
                
                # Normalize columns
                if 'CUSTOMERNO' in reasons_df.columns:
                    reasons_df['CUSTOMERNO'] = reasons_df['CUSTOMERNO'].astype(str).str.strip()
                if 'ACCOUNT_NUMBER' in reasons_df.columns:
                    reasons_df['ACCOUNT_NUMBER'] = reasons_df['ACCOUNT_NUMBER'].astype(str).str.strip()
                
                reasons_df.to_sql('reasons', conn, if_exists='replace', index=False)
                logger.info(f"Cached {len(reasons_df)} reasons records")
            
            # Create indexes for fast lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_account ON warehouse(ACCOUNT_NUMBER)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_reasons_customer ON reasons(CUSTOMERNO)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_reasons_account ON reasons(ACCOUNT_NUMBER)')
            
            conn.commit()
            logger.info("✓ Cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Cache initialization error: {e}")
            raise
        finally:
            conn.close()
    
    def is_in_warehouse(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """Check if customer is in warehouse (eligible)"""
        normalized_id = str(identifier).strip()
        is_customer_number = len(normalized_id) < 10
        
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        
        try:
            if is_customer_number:
                # Search by customer number prefix
                query = "SELECT ACCOUNT_NUMBER FROM warehouse WHERE ACCOUNT_NUMBER LIKE ?"
                cursor.execute(query, (f"{normalized_id}%",))
            else:
                # Direct account number match
                query = "SELECT ACCOUNT_NUMBER FROM warehouse WHERE ACCOUNT_NUMBER = ?"
                cursor.execute(query, (normalized_id,))
            
            result = cursor.fetchone()
            
            if result:
                return True, result[0]
            return False, None
            
        finally:
            conn.close()
    
    def get_customer_data(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get customer data from reasons file"""
        normalized_id = str(identifier).strip()
        is_customer_number = len(normalized_id) < 10
        
        conn = sqlite3.connect(self.cache_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            if is_customer_number:
                query = "SELECT * FROM reasons WHERE CUSTOMERNO = ? OR ACCOUNT_NUMBER LIKE ?"
                cursor.execute(query, (normalized_id, f"{normalized_id}%"))
            else:
                query = "SELECT * FROM reasons WHERE ACCOUNT_NUMBER = ?"
                cursor.execute(query, (normalized_id,))
            
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
            
        finally:
            conn.close()
