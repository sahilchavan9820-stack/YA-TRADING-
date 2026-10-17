import os
from flask import Flask, jsonify, render_template, request
import yfinance as yf
import pytz

current_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=current_dir,
    static_folder=current_dir
)

IST = pytz.timezone("Asia/Kolkata")

# परवानगी असलेले टाइमफ्रेम
ALLOWED_INTERVALS = {
    "1m", "2m", "3m", "5m",
    "15m", "30m", "1h"
}


@app.route("/")
def chart_home():
    return render_template("chart.html")


@app.route("/api/chart-data")
def get_chart_data():
    try:
        interval = request.args.get("interval", "1m")

        # चुकीचा टाइमफ्रेम स्वीकारू नका
        if interval not in ALLOWED_INTERVALS:
            return jsonify({
                "status": "error",
                "message": "Invalid chart interval"
            }), 400

        # टाइमफ्रेमनुसार डेटा कालावधी
        if interval in ["1m", "2m", "3m", "5m", "15m"]:
            period = "5d"
        elif interval == "30m":
            period = "1mo"
        else:
            period = "1mo"

        # NIFTY 50 डेटा मिळवणे
        stock = yf.Ticker("^NSEI")

        df = stock.history(
            period=period,
            interval=interval,
            auto_adjust=False,
            raise_errors=True
        )

        if df.empty:
            return jsonify({
                "status": "error",
                "message": (
                    "डेटा उपलब्ध नाही. "
                    "बाजार बंद असू शकतो किंवा डेटा स्रोत प्रतिसाद देत नसेल."
                )
            })

        candles = []

        for index, row in df.iterrows():

            # वेळ IST मध्ये रूपांतरित करणे
            if index.tzinfo is None:
                localized_time = IST.localize(index)
            else:
                localized_time = index.astimezone(IST)

            unix_time = int(localized_time.timestamp())

            # अपूर्ण किंवा चुकीचा डेटा वगळणे
            values = [
                row["Open"],
                row["High"],
                row["Low"],
                row["Close"]
            ]

            if any(value is None for value in values):
                continue

            if not all(
                __import__("math").isfinite(float(value))
                for value in values
            ):
                continue

            candles.append({
                "time": unix_time,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2)
            })

        # वेळेनुसार क्रम लावणे
        candles.sort(key=lambda item: item["time"])

        # Lightweight Charts साठी प्रत्येक वेळ unique असावी
        unique_candles = []
        seen_times = set()

        for candle in candles:
            if candle["time"] not in seen_times:
                unique_candles.append(candle)
                seen_times.add(candle["time"])

        if not unique_candles:
            return jsonify({
                "status": "error",
                "message": "वैध कँडल डेटा उपलब्ध नाही."
            })

        response = jsonify({
            "status": "success",
            "interval": interval,
            "candles": unique_candles
        })

        # ब्राउझरने जुनाच API प्रतिसाद cache करू नये
        response.headers["Cache-Control"] = "no-store"

        return response

    except Exception as e:
        app.logger.exception("Chart data error")

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    print("--- NIFTY 50 CHART SERVER RUNNING ---")

    app.run(
        debug=True,
        port=5000,
        use_reloader=False
    )