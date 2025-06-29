"""Data loading utilities for market research data."""

import re
import pandas as pd
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, init_db
from app.db.models import MarketResearchData
import logging

logger = logging.getLogger(__name__)


def parse_markdown_table(markdown_content: str) -> list[str]:
    """Parse the markdown table and extract text statements."""
    statements = []
    
    # Split by lines and find the data rows
    lines = markdown_content.strip().split('\n')
    
    for line in lines:
        # Skip header and separator lines
        if line.startswith('|') and 'text' not in line and '---' not in line:
            # Extract the text content between the pipes
            text = line.split('|')[1].strip()
            if text and text != 'text':
                statements.append(text)
    
    return statements


def load_market_research_data(file_path: str, db: Session = None) -> int:
    """Load market research data from markdown file into database."""
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        # Read the markdown file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the statements
        statements = parse_markdown_table(content)
        
        # Clear existing data
        db.query(MarketResearchData).delete()
        
        # Insert new data
        loaded_count = 0
        for statement in statements:
            if statement.strip():  # Only add non-empty statements
                research_data = MarketResearchData(text=statement.strip())
                db.add(research_data)
                loaded_count += 1
        
        db.commit()
        logger.info(f"Successfully loaded {loaded_count} market research statements")
        return loaded_count
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error loading market research data: {e}")
        raise
    finally:
        if close_db:
            db.close()


def initialize_database_with_data(data_file_path: str):
    """Initialize database and load market research data."""
    logger.info("Initializing database...")
    init_db()
    
    logger.info(f"Loading market research data from {data_file_path}...")
    count = load_market_research_data(data_file_path)
    
    logger.info(f"Database initialization complete. Loaded {count} statements.")
    return count


if __name__ == "__main__":
    # Script can be run directly to load data
    import sys
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = "../data.md"  # Default relative to project root
    
    logging.basicConfig(level=logging.INFO)
    initialize_database_with_data(data_file)
