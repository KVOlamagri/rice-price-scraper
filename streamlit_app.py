"""
Streamlit Web App for Rice Price Scraper
Business-friendly interface for scraping rice prices from multiple retailers
"""

import streamlit as st
import pandas as pd
import subprocess
import os
import time
from datetime import datetime
import glob

# Page configuration
st.set_page_config(
    page_title="Rice Price Scraper",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2e7d32;
        font-weight: bold;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2e7d32;
    }
    .success-message {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        color: #155724;
    }
    .error-message {
        padding: 1rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

def get_output_directory():
    """Get the output directory path"""
    return os.path.join(os.getcwd(), "output")

def get_latest_files():
    """Get the latest scraped files"""
    output_dir = get_output_directory()
    csv_files = glob.glob(os.path.join(output_dir, "rice_prices_*.csv"))
    
    if not csv_files:
        return []
    
    # Sort by modification time
    csv_files.sort(key=os.path.getmtime, reverse=True)
    return csv_files[:10]  # Return latest 10 files

def load_csv_data(file_path):
    """Load CSV data safely"""
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def run_scraper(retailer=None, country=None):
    """Run the scraper with optional filters"""
    try:
        cmd = ["python", "main.py"]
        
        if retailer:
            cmd.extend(["-r", retailer])
        if country:
            cmd.extend(["-n", country])
        
        # Run the scraper
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        return process
    except Exception as e:
        st.error(f"Error starting scraper: {e}")
        return None

def display_metrics(df):
    """Display key metrics from the data"""
    if df is None or df.empty:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Products", len(df))
    
    with col2:
        if 'retailer' in df.columns:
            st.metric("Retailers", df['retailer'].nunique())
    
    with col3:
        if 'category' in df.columns:
            st.metric("Categories", df['category'].nunique())
    
    with col4:
        if 'regular_price' in df.columns:
            avg_price = df['regular_price'].mean()
            st.metric("Avg Price", f"{avg_price:.2f}")

def main():
    # Header
    st.markdown('<div class="main-header">🌾 Rice Price Scraper</div>', unsafe_allow_html=True)
    st.markdown("### Automated rice price tracking from multiple retailers")
    
    # Sidebar
    st.sidebar.title("⚙️ Scraper Settings")
    
    # Retailer selection
    retailer_options = {
        "All Retailers": None,
        "Carrefour": "carrefour",
        "Lulu Hypermarket": "lulu"
    }
    
    selected_retailer_label = st.sidebar.selectbox(
        "Select Retailer",
        list(retailer_options.keys())
    )
    selected_retailer = retailer_options[selected_retailer_label]
    
    # Country selection
    country_options = {
        "All Countries": None,
        "UAE": "uae",
        "KSA": "ksa"
    }
    
    selected_country_label = st.sidebar.selectbox(
        "Select Country",
        list(country_options.keys())
    )
    selected_country = country_options[selected_country_label]
    
    st.sidebar.markdown("---")
    
    # Run button
    run_button = st.sidebar.button("🚀 Run Scraper", use_container_width=True, type="primary")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📊 Run Scraper", "📁 View Results", "📈 Analysis"])
    
    # Tab 1: Run Scraper
    with tab1:
        if run_button:
            st.markdown('<div class="success-message">✅ Scraper started! Please wait...</div>', unsafe_allow_html=True)
            
            # Progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Run the scraper
            process = run_scraper(selected_retailer, selected_country)
            
            if process:
                output_lines = []
                
                # Read output in real-time
                for line in process.stdout:
                    output_lines.append(line.strip())
                    
                    # Update status based on log output
                    if "Scraping" in line:
                        status_text.text(f"🔄 {line.strip()}")
                    elif "Total products" in line:
                        status_text.text(f"✅ {line.strip()}")
                    elif "Successfully scraped" in line:
                        status_text.text(f"🎉 {line.strip()}")
                    
                    # Update progress (simple estimation)
                    if len(output_lines) % 5 == 0:
                        progress = min(len(output_lines) * 2, 100)
                        progress_bar.progress(progress / 100)
                
                # Wait for process to complete
                process.wait()
                
                progress_bar.progress(100)
                
                if process.returncode == 0:
                    st.markdown('<div class="success-message">🎉 Scraping completed successfully!</div>', unsafe_allow_html=True)
                    st.balloons()
                    
                    # Show output log
                    with st.expander("View Detailed Log"):
                        st.code("\n".join(output_lines))
                else:
                    st.markdown('<div class="error-message">❌ Scraping encountered errors. Check the log below.</div>', unsafe_allow_html=True)
                    with st.expander("View Error Log"):
                        error_output = process.stderr.read()
                        st.code(error_output)
        else:
            st.info("👈 Configure settings in the sidebar and click 'Run Scraper' to start")
            
            # Display configuration summary
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Current Configuration")
                st.write(f"**Retailer:** {selected_retailer_label}")
                st.write(f"**Country:** {selected_country_label}")
            
            with col2:
                st.markdown("#### What will be scraped?")
                if selected_retailer and selected_country:
                    st.write(f"✓ {selected_retailer_label} in {selected_country_label}")
                elif selected_retailer:
                    st.write(f"✓ {selected_retailer_label} in all countries")
                elif selected_country:
                    st.write(f"✓ All retailers in {selected_country_label}")
                else:
                    st.write("✓ All retailers in all countries")
                    st.write("  - Carrefour UAE")
                    st.write("  - Carrefour KSA")
                    st.write("  - Lulu UAE")
                    st.write("  - Lulu KSA")
    
    # Tab 2: View Results
    with tab2:
        st.markdown("### 📁 Recent Scraping Results")
        
        latest_files = get_latest_files()
        
        if not latest_files:
            st.warning("No results found. Run the scraper first to generate data.")
        else:
            # File selector
            file_names = [os.path.basename(f) for f in latest_files]
            selected_file = st.selectbox("Select a file to view", file_names)
            
            if selected_file:
                file_path = os.path.join(get_output_directory(), selected_file)
                df = load_csv_data(file_path)
                
                if df is not None and not df.empty:
                    # Display metrics
                    display_metrics(df)
                    
                    st.markdown("---")
                    
                    # Filters
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if 'category' in df.columns:
                            categories = ['All'] + list(df['category'].unique())
                            selected_category = st.selectbox("Filter by Category", categories)
                            if selected_category != 'All':
                                df = df[df['category'] == selected_category]
                    
                    with col2:
                        if 'retailer' in df.columns:
                            retailers = ['All'] + list(df['retailer'].unique())
                            selected_retailer_filter = st.selectbox("Filter by Retailer", retailers)
                            if selected_retailer_filter != 'All':
                                df = df[df['retailer'] == selected_retailer_filter]
                    
                    with col3:
                        if 'pack_size' in df.columns:
                            pack_sizes = ['All'] + sorted(df['pack_size'].unique())
                            selected_pack = st.selectbox("Filter by Pack Size", pack_sizes)
                            if selected_pack != 'All':
                                df = df[df['pack_size'] == selected_pack]
                    
                    # Display data
                    st.dataframe(df, use_container_width=True, height=400)
                    
                    # Download buttons
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=f"filtered_{selected_file}",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        # Excel download
                        excel_path = file_path.replace('.csv', '.xlsx')
                        if os.path.exists(excel_path):
                            with open(excel_path, 'rb') as f:
                                excel_data = f.read()
                            st.download_button(
                                label="📥 Download Excel",
                                data=excel_data,
                                file_name=f"filtered_{os.path.basename(excel_path)}",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
    
    # Tab 3: Analysis
    with tab3:
        st.markdown("### 📈 Price Analysis")
        
        latest_files = get_latest_files()
        
        if not latest_files:
            st.warning("No data available for analysis. Run the scraper first.")
        else:
            # Load the latest combined file or first file
            combined_files = [f for f in latest_files if 'combined' in f]
            file_to_analyze = combined_files[0] if combined_files else latest_files[0]
            
            df = load_csv_data(file_to_analyze)
            
            if df is not None and not df.empty:
                st.write(f"Analyzing: {os.path.basename(file_to_analyze)}")
                
                # Price statistics by category
                if 'category' in df.columns and 'regular_price' in df.columns:
                    st.markdown("#### Price Statistics by Category")
                    
                    price_stats = df.groupby('category')['regular_price'].agg([
                        ('Count', 'count'),
                        ('Min Price', 'min'),
                        ('Max Price', 'max'),
                        ('Avg Price', 'mean'),
                        ('Median Price', 'median')
                    ]).round(2)
                    
                    st.dataframe(price_stats, use_container_width=True)
                
                # Price statistics by retailer
                if 'retailer' in df.columns and 'regular_price' in df.columns:
                    st.markdown("#### Price Statistics by Retailer")
                    
                    retailer_stats = df.groupby('retailer')['regular_price'].agg([
                        ('Products', 'count'),
                        ('Min Price', 'min'),
                        ('Max Price', 'max'),
                        ('Avg Price', 'mean')
                    ]).round(2)
                    
                    st.dataframe(retailer_stats, use_container_width=True)
                
                # Top 10 cheapest products
                if 'regular_price' in df.columns:
                    st.markdown("#### Top 10 Cheapest Products")
                    
                    cheapest = df.nsmallest(10, 'regular_price')[
                        ['product_name', 'pack_size', 'regular_price', 'retailer', 'country']
                    ]
                    
                    st.dataframe(cheapest, use_container_width=True)
                
                # Products with promotions
                if 'is_promo' in df.columns:
                    promo_count = df['is_promo'].sum()
                    if promo_count > 0:
                        st.markdown(f"#### Products with Promotions ({promo_count})")
                        
                        promo_df = df[df['is_promo'] == True][
                            ['product_name', 'pack_size', 'regular_price', 'promo_price', 'retailer']
                        ]
                        
                        if not promo_df.empty:
                            promo_df['Savings'] = promo_df['regular_price'] - promo_df['promo_price']
                            st.dataframe(promo_df, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Rice Price Scraper v1.0 | Last updated: {}</p>
        <p>Powered by Playwright & Streamlit</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
