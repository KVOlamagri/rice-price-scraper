"""Data export utilities for CSV and Excel."""
import os
import csv
import logging
from typing import List
from datetime import datetime
import pandas as pd
from src.models import Product


logger = logging.getLogger(__name__)


class DataExporter:
    """Export scraped data to CSV and Excel formats."""
    
    def __init__(self, output_config: dict):
        """
        Initialize data exporter.
        
        Args:
            output_config: Output configuration dictionary
        """
        self.config = output_config
        self.output_dir = output_config.get('output_dir', 'output')
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"Output directory: {self.output_dir}")
    
    def export(self, products: List[Product], retailer: str, country: str):
        """
        Export products to configured formats.
        
        Args:
            products: List of Product objects
            retailer: Retailer name
            country: Country code
        """
        if not products:
            logger.warning(f"No products to export for {retailer} {country}")
            return
        
        # Convert to list of dictionaries
        data = [p.to_dict() for p in products]
        df = pd.DataFrame(data)
        
        # Export to CSV
        if self.config.get('csv_enabled', True):
            csv_path = self._export_csv(df, retailer, country)
            logger.info(f"Exported to CSV: {csv_path}")
        
        # Export to Excel
        if self.config.get('excel_enabled', True):
            excel_path = self._export_excel(df, retailer, country)
            logger.info(f"Exported to Excel: {excel_path}")
    
    def _export_csv(self, df: pd.DataFrame, retailer: str, country: str) -> str:
        """
        Export data to CSV.
        
        Args:
            df: Pandas DataFrame
            retailer: Retailer name
            country: Country code
            
        Returns:
            Path to CSV file
        """
        filename = self._generate_filename(retailer, country, 'csv')
        filepath = os.path.join(self.output_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        return filepath
    
    def _export_excel(self, df: pd.DataFrame, retailer: str, country: str) -> str:
        """
        Export data to Excel with formatting.
        
        Args:
            df: Pandas DataFrame
            retailer: Retailer name
            country: Country code
            
        Returns:
            Path to Excel file
        """
        filename = self._generate_filename(retailer, country, 'xlsx')
        filepath = os.path.join(self.output_dir, filename)
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Rice Prices', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Rice Prices']
            for idx, col in enumerate(df.columns):
                try:
                    # Get max length of column values
                    col_values = df[col].fillna('').astype(str)
                    max_length = max(
                        col_values.str.len().max(),
                        len(col)
                    )
                    # Calculate column letter (A, B, C, ..., Z, AA, AB, etc.)
                    col_letter = self._get_column_letter(idx)
                    worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
                except Exception as e:
                    logger.warning(f"Could not auto-size column {col}: {e}")
        
        return filepath
    
    def _generate_filename(self, retailer: str, country: str, extension: str) -> str:
        """
        Generate filename based on configuration.
        
        Args:
            retailer: Retailer name
            country: Country code
            extension: File extension
            
        Returns:
            Filename string
        """
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_format = self.config.get(
            'filename_format',
            'rice_prices_{date}_{retailer}_{country}.{ext}'
        )
        
        return filename_format.format(
            date=date_str,
            retailer=retailer.lower(),
            country=country.lower(),
            ext=extension
        )
    
    def _get_column_letter(self, idx: int) -> str:
        """
        Convert column index to Excel column letter (A, B, ..., Z, AA, AB, ...).
        
        Args:
            idx: Column index (0-based)
            
        Returns:
            Column letter string
        """
        result = ""
        idx += 1  # Excel columns are 1-indexed
        while idx > 0:
            idx -= 1
            result = chr(65 + (idx % 26)) + result
            idx //= 26
        return result
    
    def export_combined(self, all_products: List[Product], filename: str = None):
        """
        Export all products to a single combined file.
        
        Args:
            all_products: List of all Product objects
            filename: Optional custom filename
        """
        if not all_products:
            logger.warning("No products to export")
            return
        
        data = [p.to_dict() for p in all_products]
        df = pd.DataFrame(data)
        
        if filename is None:
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'rice_prices_combined_{date_str}'
        
        # Export to CSV
        if self.config.get('csv_enabled', True):
            csv_path = os.path.join(self.output_dir, f'{filename}.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8')
            logger.info(f"Exported combined CSV: {csv_path}")
        
        # Export to Excel
        if self.config.get('excel_enabled', True):
            excel_path = os.path.join(self.output_dir, f'{filename}.xlsx')
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # All products
                df.to_excel(writer, sheet_name='All Products', index=False)
                
                # By retailer
                for retailer in df['retailer'].unique():
                    retailer_df = df[df['retailer'] == retailer]
                    sheet_name = f'{retailer}'[:31]  # Excel sheet name limit
                    retailer_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # By country
                for country in df['country'].unique():
                    country_df = df[df['country'] == country]
                    sheet_name = f'{country}'[:31]
                    country_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logger.info(f"Exported combined Excel: {excel_path}")
