import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
from utils.data_processor import DataProcessor
import time
from plotly.subplots import make_subplots

# Set page config to wide mode and dark theme
st.set_page_config(
    page_title="FinMem India Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Bloomberg terminal style
st.markdown("""
<style>
    .stApp {
        background-color: #0D1117;
        color: #E6EDF3;
    }
    .stButton>button {
        background-color: #238636;
        color: white;
    }
    .stTextInput>div>div>input {
        background-color: #161B22;
        color: #E6EDF3;
    }
    .stSelectbox>div>div>select {
        background-color: #161B22;
        color: #E6EDF3;
    }
    .stDataFrame {
        background-color: #161B22;
        color: #E6EDF3;
    }
    .css-1d391kg {
        background-color: #161B22;
    }
    div[data-testid="stMetricValue"] {
        color: #238636;
    }
    div[data-testid="stMetricDelta"] {
        background-color: transparent;
    }
    div[data-testid="stMetricDelta"][data-direction="up"] {
        color: #238636;
    }
    div[data-testid="stMetricDelta"][data-direction="down"] {
        color: #f85149;
    }
    .news-item {
        background-color: #161B22;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
        border: 1px solid #30363D;
    }
    .news-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
        color: #8B949E;
        font-size: 0.8rem;
    }
    .news-symbol {
        color: #58A6FF;
        font-weight: bold;
    }
    .news-type {
        color: #238636;
    }
    .news-title {
        color: #E6EDF3;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .news-summary {
        color: #C9D1D9;
        margin-bottom: 0.5rem;
    }
    .news-source {
        color: #8B949E;
        font-size: 0.8rem;
    }
    
    .log-container {
        background-color: #0D1117;
        border: 1px solid #30363D;
        border-radius: 5px;
        padding: 1rem;
        height: 400px;
        overflow-y: auto;
        font-family: monospace;
    }
    .log-entry {
        padding: 0.2rem 0;
        border-bottom: 1px solid #21262D;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .log-time {
        color: #8B949E;
        margin-right: 1rem;
    }
    .log-level {
        display: inline-block;
        width: 70px;
        margin-right: 1rem;
        font-weight: bold;
    }
    .log-message {
        color: #C9D1D9;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.page = "Dashboard"
    st.session_state.data_mode = "Test Data"
    st.session_state.processor = DataProcessor()

# Sidebar
with st.sidebar:
    st.title("FinMem India")
    
    # Data mode selection
    data_mode = st.selectbox(
        "Data Source",
        ["Test Data", "Real-time Data"],
        index=0 if st.session_state.data_mode == "Test Data" else 1
    )
    
    if data_mode != st.session_state.data_mode:
        st.session_state.data_mode = data_mode
        if st.session_state.processor.is_running():
            st.session_state.processor.stop()
        st.rerun()
    
    # Simulation controls
    if not st.session_state.processor.is_running():
        st.subheader("Start Trading")
        
        with st.form("start_trading"):
            user = st.text_input("Username", value="Trader")
            
            initial_capital = st.number_input(
                "Initial Capital (₹)",
                min_value=100000,
                max_value=10000000,
                value=1000000,
                step=100000
            )
            
            risk_profile = st.selectbox(
                "Risk Profile",
                ["Risk-Averse", "Balanced", "Risk-Seeking"]
            )
            
            # Add reset option for real-time mode
            reset_capital = False
            if data_mode == "Real-time Data":
                reset_capital = st.checkbox("Reset Capital", help="Start fresh with new capital amount")
            
            start = st.form_submit_button("Start Trading")
            
            if start:
                config = {
                    "user": user,
                    "initial_capital": initial_capital,
                    "risk_profile": risk_profile,
                    "reset_capital": reset_capital
                }
                
                mode = "test" if st.session_state.data_mode == "Test Data" else "real"
                st.session_state.processor.start(mode, config)
                st.rerun()
    
    else:
        st.success("Trading Active")
        if st.session_state.processor.last_update:
            st.text(f"Last update: {st.session_state.processor.last_update.strftime('%H:%M:%S')}")
        
        # Add capital reset option for real-time mode
        if data_mode == "Real-time Data":
            st.subheader("Capital Management")
            with st.form("reset_capital"):
                new_capital = st.number_input(
                    "New Capital Amount (₹)",
                    min_value=100000,
                    max_value=10000000,
                    value=1000000,
                    step=100000
                )
                
                if st.form_submit_button("Reset Capital"):
                    st.session_state.processor.reset_capital(new_capital)
                    st.rerun()
        
        if st.button("Stop Trading"):
            st.session_state.processor.stop()
            st.rerun()
    
    # Navigation
    st.session_state.page = st.radio(
        "Navigation",
        ["Dashboard", "Portfolio", "Transaction History", "Monthly Results"]
    )

def format_currency(value: float) -> str:
    """Format value as currency"""
    return f"₹{value:,.2f}"

def format_percentage(value: float) -> str:
    """Format value as percentage"""
    return f"{value:,.2f}%"

def format_news(news_items):
    """Format news items with custom HTML"""
    html = ""
    for item in news_items:
        timestamp = item.get('timestamp', '')
        symbol = item.get('symbol', '')
        title = item.get('title', '')
        summary = item.get('summary', '')
        source = item.get('source', '')
        news_type = item.get('type', '')
        
        html += f"""
        <div class="news-item">
            <div class="news-header">
                <span class="news-symbol">{symbol}</span>
                <span class="news-type">{news_type}</span>
                <span class="news-time">{timestamp}</span>
            </div>
            <div class="news-title">{title}</div>
            <div class="news-summary">{summary}</div>
            <div class="news-source">Source: {source}</div>
        </div>
        """
    return html

def format_log_entry(log):
    """Format a log entry with custom HTML"""
    level_colors = {
        'INFO': '#58a6ff',
        'ERROR': '#f85149',
        'WARNING': '#d29922'
    }
    color = level_colors.get(log['level'], '#8b949e')
    
    return f"""
    <div class="log-entry">
        <span class="log-time">{log['timestamp']}</span>
        <span class="log-level" style="color: {color}">{log['level']}</span>
        <span class="log-message">{log['message']}</span>
    </div>
    """

def render_market_status():
    """Render market status section"""
    status = st.session_state.processor.get_market_status()
    
    if status:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            status_color = {
                'OPEN': 'green',
                'CLOSED': 'red',
                'PRE-MARKET': 'orange',
                'POST-MARKET': 'orange'
            }.get(status['status'], 'white')
            
            st.markdown(
                f"""
                <div style='
                    background-color: {status_color};
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                '>
                    {status['status']}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""
                <div style='
                    background-color: #1E1E1E;
                    padding: 10px;
                    border-radius: 5px;
                    color: white;
                '>
                    {status['message']}
                </div>
                """,
                unsafe_allow_html=True
            )

def render_portfolio_tab(state):
    """Render portfolio tab"""
    st.subheader("Portfolio Overview")
    
    # Market Status
    render_market_status()
    st.markdown("---")
    
    # Portfolio Summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Value",
            format_currency(state['total_value']),
            format_currency(state['total_pl']) + f" ({format_percentage(state['pl_pct'])})",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "Initial Capital",
            format_currency(state['initial_capital'])
        )
    
    with col3:
        st.metric(
            "Available Capital",
            format_currency(state['capital'])
        )
    
    with col4:
        invested = state['initial_capital'] - state['capital']
        st.metric(
            "Invested Amount",
            format_currency(invested)
        )
    
    # Portfolio Holdings
    st.subheader("Holdings")
    if state['portfolio']:
        df = pd.DataFrame(state['portfolio'].values())
        df['current_value'] = df['quantity'] * df['current_price']
        df['pl_amount'] = df['current_value'] - (df['quantity'] * df['avg_price'])
        df['pl_percentage'] = (df['pl_amount'] / (df['quantity'] * df['avg_price'])) * 100
        
        # Format the dataframe
        df = df[[
            'symbol', 'quantity', 'avg_price', 'current_price',
            'current_value', 'pl_amount', 'pl_percentage'
        ]]
        df.columns = [
            'Symbol', 'Quantity', 'Avg Price', 'Current Price',
            'Current Value', 'P/L Amount', 'P/L %'
        ]
        
        # Apply formatting
        df['Avg Price'] = df['Avg Price'].apply(format_currency)
        df['Current Price'] = df['Current Price'].apply(format_currency)
        df['Current Value'] = df['Current Value'].apply(format_currency)
        df['P/L Amount'] = df['P/L Amount'].apply(format_currency)
        df['P/L %'] = df['P/L %'].apply(format_percentage)
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No holdings in portfolio")
    
    # Recent Transactions
    st.subheader("Recent Transactions")
    if state['transactions']:
        df = pd.DataFrame(state['transactions'])
        df['value'] = df['quantity'] * df['price']
        
        # Format the dataframe
        df = df[['timestamp', 'symbol', 'action', 'quantity', 'price', 'value']]
        df.columns = ['Timestamp', 'Symbol', 'Action', 'Quantity', 'Price', 'Value']
        
        # Apply formatting
        df['Price'] = df['Price'].apply(format_currency)
        df['Value'] = df['Value'].apply(format_currency)
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No recent transactions")

def render_news_tab(state):
    """Render news tab"""
    st.subheader("Market News")
    
    # Market Status
    render_market_status()
    st.markdown("---")
    
    # News filters
    col1, col2 = st.columns([1, 3])
    
    with col1:
        news_type = st.selectbox(
            "Filter by Type",
            ["All"] + sorted(set(news['type'] for news in state['news']))
        )
    
    with col2:
        symbols = ["All"] + sorted(set(news['symbol'] for news in state['news']))
        symbol = st.selectbox("Filter by Symbol", symbols)
    
    # Filter news
    filtered_news = state['news']
    if news_type != "All":
        filtered_news = [n for n in filtered_news if n['type'] == news_type]
    if symbol != "All":
        filtered_news = [n for n in filtered_news if n['symbol'] == symbol]
    
    # Display news
    for news in filtered_news:
        with st.container():
            st.markdown(
                f"""
                <div style='
                    background-color: #1E1E1E;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                '>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 10px;'>
                        <span style='color: #00FF00;'>{news['symbol']}</span>
                        <span style='color: #FFA500;'>{news['type']}</span>
                        <span style='color: #808080;'>{news['timestamp']}</span>
                    </div>
                    <div style='margin-bottom: 10px;'>
                        <strong style='color: #FFFFFF;'>{news['title']}</strong>
                    </div>
                    <div style='color: #CCCCCC;'>{news['summary']}</div>
                    <div style='margin-top: 10px;'>
                        <span style='color: #4A90E2;'>{news['source']}</span>
                        {f" • <a href='{news['link']}' target='_blank'>Read More</a>" if 'link' in news else ''}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_logs_tab(state):
    """Render system logs tab"""
    st.subheader("System Logs")
    
    # Market Status
    render_market_status()
    st.markdown("---")
    
    # Log filters
    col1, col2 = st.columns([1, 3])
    
    with col1:
        log_level = st.selectbox(
            "Filter by Level",
            ["All"] + sorted(set(log['level'] for log in state['logs']))
        )
    
    with col2:
        search_term = st.text_input("Search Logs", "")
    
    # Filter logs
    filtered_logs = state['logs']
    if log_level != "All":
        filtered_logs = [log for log in filtered_logs if log['level'] == log_level]
    if search_term:
        filtered_logs = [
            log for log in filtered_logs
            if search_term.lower() in log['message'].lower()
        ]
    
    # Display logs
    for log in filtered_logs:
        level_color = {
            'INFO': '#4A90E2',
            'WARNING': '#FFA500',
            'ERROR': '#FF0000'
        }.get(log['level'], '#FFFFFF')
        
        st.markdown(
            f"""
            <div style='
                background-color: #1E1E1E;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 5px;
                font-family: monospace;
            '>
                <span style='color: #808080;'>{log['timestamp']}</span>
                <span style='color: {level_color}; margin-left: 10px;'>[{log['level']}]</span>
                <span style='color: #FFFFFF; margin-left: 10px;'>{log['message']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

def show_dashboard():
    st.title("Dashboard")
    
    if not st.session_state.processor.is_running():
        st.warning("Please start trading to view dashboard")
        return
    
    # Get current state
    state = st.session_state.processor.get_current_state()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Portfolio", "Market News", "System Logs"])
    
    with tab1:
        render_portfolio_tab(state)
    
    with tab2:
        render_news_tab(state)
    
    with tab3:
        render_logs_tab(state)
    
    # Auto-refresh
    time.sleep(0.1)
    st.rerun()

def show_portfolio():
    st.title("Portfolio Analysis")
    
    if not st.session_state.processor.is_running():
        st.warning("Please start trading to view portfolio")
        return
    
    # Get current state
    state = st.session_state.processor.get_current_state()
    
    # Portfolio composition
    st.subheader("Portfolio Composition")
    
    if state['portfolio']:
        # Create pie chart
        values = [pos['market_value'] for pos in state['portfolio'].values()]
        labels = list(state['portfolio'].keys())
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.3,
            marker=dict(colors=['#238636', '#2ea043', '#3fb950', '#4ac959', '#56d364'])
        )])
        
        fig.update_layout(
            plot_bgcolor='#161B22',
            paper_bgcolor='#161B22',
            font=dict(color='#E6EDF3'),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Position details
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Position Details")
            positions = []
            for symbol, data in state['portfolio'].items():
                positions.append({
                    'Symbol': symbol,
                    'Weight': f"{(data['market_value'] / sum(values) * 100):.1f}%",
                    'Market Value': format_currency(data['market_value']),
                    'P/L': format_currency(data['profit_loss'])
                })
            
            st.dataframe(pd.DataFrame(positions), use_container_width=True)
        
        with col2:
            st.subheader("Risk Analysis")
            st.info(
                f"Risk Profile: {state['risk_profile']}\n\n"
                f"Portfolio Concentration: {len(state['portfolio'])} positions\n\n"
                f"Largest Position: {max(pos['market_value'] for pos in state['portfolio'].values()) / state['total_value']:.1%} of total value"
            )
    else:
        st.info("No open positions")
    
    # Auto-refresh
    time.sleep(0.1)
    st.rerun()

def show_transactions():
    st.title("Transaction History")
    
    if not st.session_state.processor.is_running():
        st.warning("Please start trading to view transactions")
        return
    
    # Get current state
    state = st.session_state.processor.get_current_state()
    
    if state['transactions']:
        # Create DataFrame
        df = pd.DataFrame(state['transactions'])
        df['date'] = pd.to_datetime(df['date'])
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbols = ['All'] + sorted(df['symbol'].unique().tolist())
            symbol = st.selectbox("Symbol", symbols)
        
        with col2:
            actions = ['All'] + sorted(df['action'].unique().tolist())
            action = st.selectbox("Action", actions)
        
        with col3:
            date_range = st.date_input(
                "Date Range",
                value=(df['date'].min().date(), df['date'].max().date())
            )
        
        # Apply filters
        if symbol != 'All':
            df = df[df['symbol'] == symbol]
        if action != 'All':
            df = df[df['action'] == action]
        if len(date_range) == 2:
            df = df[
                (df['date'].dt.date >= date_range[0]) &
                (df['date'].dt.date <= date_range[1])
            ]
        
        # Sort by date
        df = df.sort_values('date', ascending=False)
        
        # Format values
        display_df = df.copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        display_df['price'] = display_df['price'].apply(format_currency)
        display_df['value'] = display_df['value'].apply(format_currency)
        display_df['profit_loss'] = display_df['profit_loss'].apply(format_currency)
        
        # Display with pagination
        page_size = 20
        total_pages = len(display_df) // page_size + (1 if len(display_df) % page_size > 0 else 0)
        
        if total_pages > 1:
            page = st.number_input("Page", min_value=1, max_value=total_pages, value=1) - 1
            start_idx = page * page_size
            end_idx = start_idx + page_size
            display_df = display_df.iloc[start_idx:end_idx]
        
        st.dataframe(display_df, use_container_width=True)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Trades", len(df))
        
        with col2:
            total_value = df['value'].sum()
            st.metric("Total Value", format_currency(total_value))
        
        with col3:
            total_pl = df['profit_loss'].sum()
            st.metric("Total P/L", format_currency(total_pl))
        
        with col4:
            win_rate = (df['profit_loss'] > 0).mean() * 100
            st.metric("Win Rate", format_percentage(win_rate))
    else:
        st.info("No transactions recorded")
    
    # Auto-refresh
    time.sleep(0.1)
    st.rerun()

def show_monthly_results():
    st.title("Monthly Results")
    
    if not st.session_state.processor.is_running():
        st.warning("Please start trading to view results")
        return
    
    # Get current state
    state = st.session_state.processor.get_current_state()
    
    if state['transactions']:
        # Create DataFrame
        df = pd.DataFrame(state['transactions'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate monthly metrics
        monthly = df.set_index('date').resample('M').agg({
            'value': 'sum',
            'profit_loss': 'sum'
        }).reset_index()
        
        monthly['return'] = monthly['profit_loss'] / monthly['value'] * 100
        monthly['cumulative_return'] = (1 + monthly['return'] / 100).cumprod() - 1
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Months", len(monthly))
        
        with col2:
            profitable_months = (monthly['profit_loss'] > 0).sum()
            st.metric(
                "Profitable Months",
                f"{profitable_months} / {len(monthly)}",
                format_percentage(profitable_months / len(monthly) * 100)
            )
        
        with col3:
            total_return = monthly['cumulative_return'].iloc[-1] * 100
            st.metric("Total Return", format_percentage(total_return))
        
        with col4:
            avg_monthly_return = monthly['return'].mean()
            st.metric("Avg Monthly Return", format_percentage(avg_monthly_return))
        
        # Charts
        tab1, tab2 = st.tabs(["Monthly Returns", "Cumulative Performance"])
        
        with tab1:
            fig1 = go.Figure()
            
            fig1.add_trace(go.Bar(
                x=monthly['date'],
                y=monthly['return'],
                name='Monthly Return',
                marker_color=['#238636' if x >= 0 else '#f85149' for x in monthly['return']]
            ))
            
            fig1.update_layout(
                title="Monthly Returns",
                plot_bgcolor='#161B22',
                paper_bgcolor='#161B22',
                font=dict(color='#E6EDF3'),
                xaxis=dict(gridcolor='#30363D'),
                yaxis=dict(
                    gridcolor='#30363D',
                    title='Return %',
                    tickformat='.1f',
                    ticksuffix='%'
                ),
                height=400
            )
            
            st.plotly_chart(fig1, use_container_width=True)
        
        with tab2:
            fig2 = go.Figure()
            
            fig2.add_trace(go.Scatter(
                x=monthly['date'],
                y=monthly['cumulative_return'] * 100,
                name='Cumulative Return',
                line=dict(color='#238636', width=2)
            ))
            
            fig2.update_layout(
                title="Cumulative Performance",
                plot_bgcolor='#161B22',
                paper_bgcolor='#161B22',
                font=dict(color='#E6EDF3'),
                xaxis=dict(gridcolor='#30363D'),
                yaxis=dict(
                    gridcolor='#30363D',
                    title='Return %',
                    tickformat='.1f',
                    ticksuffix='%'
                ),
                height=400
            )
            
            st.plotly_chart(fig2, use_container_width=True)
        
        # Monthly details table
        st.subheader("Monthly Details")
        
        display_df = monthly.copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m')
        display_df['value'] = display_df['value'].apply(format_currency)
        display_df['profit_loss'] = display_df['profit_loss'].apply(format_currency)
        display_df['return'] = display_df['return'].apply(format_percentage)
        display_df['cumulative_return'] = (display_df['cumulative_return'] * 100).apply(format_percentage)
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No monthly results available")
    
    # Auto-refresh
    time.sleep(0.1)
    st.rerun()

# Display selected page
if st.session_state.page == "Dashboard":
    show_dashboard()
elif st.session_state.page == "Portfolio":
    show_portfolio()
elif st.session_state.page == "Transaction History":
    show_transactions()
elif st.session_state.page == "Monthly Results":
    show_monthly_results()
