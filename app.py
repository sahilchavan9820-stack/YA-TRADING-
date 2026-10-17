import os
from flask import Flask, jsonify, render_template, request
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

template_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=template_dir)

tickers = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "SENSEX": "^BSESN"
}

@app.route('/')
def home():
    return render_template('index.html')

# १. जेव्हा युजर 'Chart' वर क्लिक करेल तेव्हा हा रूट chart.html उघडेल
@app.route('/chart')
def chart_page():
    return render_template('chart.html')

# २. लाईव्ह कँडलस्टिक चार्टसाठी डेटा देणारा API रूट
@app.route('/api/chart-data')
def chart_data():
    interval = request.args.get('interval', '1m')
    period_map = {'1m': '1d', '3m': '1d', '5m': '5d', '15m': '5d', '30m': '1mo', '1h': '1mo'}
    period = period_map.get(interval, '1d')
    
    try:
        df = yf.download('^NSEI', period=period, interval=interval, progress=False)
        
        if df.empty:
            return jsonify({'status': 'error', 'message': 'No data found'})

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()
        
        candles = []
        ist = pytz.timezone('Asia/Kolkata')

        for index, row in df.iterrows():
            if index.tzinfo is not None:
                dt_ist = index.astimezone(ist)
            else:
                dt_ist = pytz.utc.localize(index).astimezone(ist)
            
            timestamp = int(dt_ist.timestamp())
            
            candles.append({
                'time': timestamp,
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close'])
            })

        return jsonify({'status': 'success', 'candles': candles})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/market-data')
def get_market_data():
    results = {}
    for name, symbol in tickers.items():
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="1d", interval="1m")
            
            if not data.empty:
                current_price = float(data['Close'].iloc[-1])
                hist_5d = stock.history(period="5d")
                if len(hist_5d) >= 2:
                    prev_close = float(hist_5d['Close'].iloc[-2])
                else:
                    prev_close = current_price
                
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close else 0.0
                
                results[name] = {
                    "price": f"{current_price:,.2f}",
                    "change": f"{change_pct:+.2f}",
                    "is_positive": change >= 0
                }
            else:
                results[name] = {"price": "N/A", "change": "0.00", "is_positive": True}
        except Exception as e:
            print(f"Error for {name}: {e}")
            results[name] = {"price": "Error", "change": "0.00", "is_positive": True}
            
    return jsonify(results)

if __name__ == '__main__':
    print("--- MAZA TRADE SETUP SERVER RUNNING ---")
    app.run(debug=True, port=8000)