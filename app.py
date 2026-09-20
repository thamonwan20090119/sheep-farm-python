from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
import os
import json

app = Flask(__name__)


# ============================================================
# 🐑 SHEEP FARM SMART SYSTEM
# Python Analysis Service
# ============================================================

HOT_THRESHOLD = 35


# ============================================================
# 🔐 เชื่อมต่อ Google Sheets
# ============================================================

def connect_google_sheet():

    credentials_json = os.environ.get(
        "GOOGLE_CREDENTIALS"
    )

    if not credentials_json:
        raise Exception(
            "ไม่พบ GOOGLE_CREDENTIALS"
        )

    credentials_info = json.loads(
        credentials_json
    )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=scopes
    )

    gc = gspread.authorize(credentials)

    return gc


# ============================================================
# 🧠 วิเคราะห์ข้อมูล
# ============================================================

def analyze_data(spreadsheet_id):

    gc = connect_google_sheet()

    spreadsheet = gc.open_by_key(
        spreadsheet_id
    )

    worksheet = spreadsheet.worksheet(
        "DHTData"
    )

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    if df.empty:
        raise Exception(
            "ยังไม่มีข้อมูลใน DHTData"
        )


    # ========================================================
    # เตรียมข้อมูล
    # ========================================================

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce"
    )

    df["Temperature"] = pd.to_numeric(
        df["Temperature"],
        errors="coerce"
    )

    df["Humidity"] = pd.to_numeric(
        df["Humidity"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "Timestamp",
            "Temperature",
            "Humidity"
        ]
    )

    df = df.sort_values(
        "Timestamp"
    )


    if df.empty:
        raise Exception(
            "ไม่พบข้อมูลที่ใช้วิเคราะห์"
        )


    # ========================================================
    # ข้อมูลล่าสุด
    # ========================================================

    latest = df.iloc[-1]

    latest_temp = latest["Temperature"]

    latest_humidity = latest["Humidity"]

    latest_time = latest["Timestamp"]


    # ========================================================
    # สถิติพื้นฐาน
    # ========================================================

    avg_temp = df["Temperature"].mean()

    max_temp = df["Temperature"].max()

    min_temp = df["Temperature"].min()

    avg_humidity = df["Humidity"].mean()

    max_humidity = df["Humidity"].max()

    min_humidity = df["Humidity"].min()


    # ========================================================
    # อุณหภูมิสูงสุด
    # ========================================================

    max_temp_row = df.loc[
        df["Temperature"].idxmax()
    ]

    max_temp_time = (
        max_temp_row["Timestamp"]
    )

    max_temp_value = (
        max_temp_row["Temperature"]
    )


    # ========================================================
    # ความชื้นต่ำสุด
    # ========================================================

    min_humidity_row = df.loc[
        df["Humidity"].idxmin()
    ]

    min_humidity_time = (
        min_humidity_row["Timestamp"]
    )

    min_humidity_value = (
        min_humidity_row["Humidity"]
    )


    # ========================================================
    # การเปลี่ยนแปลงอุณหภูมิ
    # ========================================================

    first_temp = (
        df.iloc[0]["Temperature"]
    )

    last_temp = (
        df.iloc[-1]["Temperature"]
    )

    temp_change = (
        last_temp - first_temp
    )


    # ========================================================
    # การเปลี่ยนแปลงความชื้น
    # ========================================================

    first_humidity = (
        df.iloc[0]["Humidity"]
    )

    last_humidity = (
        df.iloc[-1]["Humidity"]
    )

    humidity_change = (
        last_humidity - first_humidity
    )


    # ========================================================
    # แนวโน้มอุณหภูมิ
    # ========================================================

    x = np.arange(len(df))

    y_temp = df[
        "Temperature"
    ].values

    if len(df) >= 2:

        slope = np.polyfit(
            x,
            y_temp,
            1
        )[0]

    else:

        slope = 0


    if slope > 0.05:

        temperature_trend = (
            "อุณหภูมิมีแนวโน้มเพิ่มขึ้น"
        )

    elif slope < -0.05:

        temperature_trend = (
            "อุณหภูมิมีแนวโน้มลดลง"
        )

    else:

        temperature_trend = (
            "อุณหภูมิค่อนข้างคงที่"
        )


    # ========================================================
    # ความสัมพันธ์อุณหภูมิ / ความชื้น
    # ========================================================

    if len(df) >= 2:

        correlation = df[
            "Temperature"
        ].corr(
            df["Humidity"]
        )

    else:

        correlation = 0


    if correlation <= -0.7:

        relation = (
            "อุณหภูมิและความชื้นมีแนวโน้มสวนทางกันอย่างชัดเจน"
        )

    elif correlation <= -0.3:

        relation = (
            "อุณหภูมิและความชื้นมีแนวโน้มสวนทางกัน"
        )

    elif correlation >= 0.7:

        relation = (
            "อุณหภูมิและความชื้นมีแนวโน้มเพิ่มขึ้นไปในทิศทางเดียวกัน"
        )

    elif correlation >= 0.3:

        relation = (
            "อุณหภูมิและความชื้นมีแนวโน้มไปในทิศทางเดียวกันเล็กน้อย"
        )

    else:

        relation = (
            "ไม่พบความสัมพันธ์ที่ชัดเจน"
        )


    # ========================================================
    # ช่วงที่ควรเฝ้าระวัง
    # ========================================================

    watch_data = df[
        df["Temperature"] > HOT_THRESHOLD
    ]

    watch_count = len(
        watch_data
    )


    if watch_count > 0:

        watch_start = (
            watch_data.iloc[0]["Timestamp"]
        )

        watch_end = (
            watch_data.iloc[-1]["Timestamp"]
        )

        watch_message = (
            f"พบช่วงอุณหภูมิสูงกว่า "
            f"{HOT_THRESHOLD}°C "
            f"จำนวน {watch_count} ครั้ง "
            f"ช่วงประมาณ "
            f"{watch_start.strftime('%H:%M')} - "
            f"{watch_end.strftime('%H:%M')} น."
        )

    else:

        watch_message = (
            f"ไม่พบช่วงอุณหภูมิสูงกว่า "
            f"{HOT_THRESHOLD}°C"
        )


    # ========================================================
    # ข้อเสนอแนะ
    # ========================================================

    if latest_temp > HOT_THRESHOLD:

        recommendation = (
            "ควรติดตามสภาพแวดล้อมอย่างใกล้ชิด "
            "เนื่องจากอุณหภูมิล่าสุดอยู่ในช่วงที่ระบบกำหนดให้เฝ้าระวัง"
        )

    elif temperature_trend == (
        "อุณหภูมิมีแนวโน้มเพิ่มขึ้น"
    ):

        recommendation = (
            "ควรติดตามข้อมูลการตรวจวัดครั้งถัดไป "
            "เนื่องจากอุณหภูมิมีแนวโน้มเพิ่มขึ้น"
        )

    elif min_humidity_value < 55:

        recommendation = (
            "ควรติดตามการเปลี่ยนแปลงของความชื้น "
            "เนื่องจากพบค่าความชื้นค่อนข้างต่ำในข้อมูลที่ตรวจวัด"
        )

    else:

        recommendation = (
            "ควรติดตามข้อมูลตามช่วงเวลาที่กำหนด "
            "เพื่อดูการเปลี่ยนแปลงของสภาพแวดล้อม"
        )


    # ========================================================
    # สร้าง Analysis Sheet
    # ========================================================

    analysis_data = [

        [
            "รายการวิเคราะห์",
            "ผลลัพธ์"
        ],

        [
            "อุณหภูมิล่าสุด",
            f"{latest_temp:.1f} °C"
        ],

        [
            "ความชื้นล่าสุด",
            f"{latest_humidity:.1f} %"
        ],

        [
            "อุณหภูมิสูงสุด",
            f"{max_temp_value:.1f} °C"
        ],

        [
            "ช่วงเวลาที่อุณหภูมิสูงสุด",
            max_temp_time.strftime(
                "%Y-%m-%d %H:%M"
            )
        ],

        [
            "ความชื้นต่ำสุด",
            f"{min_humidity_value:.1f} %"
        ],

        [
            "ช่วงเวลาที่ความชื้นต่ำสุด",
            min_humidity_time.strftime(
                "%Y-%m-%d %H:%M"
            )
        ],

        [
            "การเปลี่ยนแปลงอุณหภูมิ",
            f"{temp_change:+.1f} °C"
        ],

        [
            "การเปลี่ยนแปลงความชื้น",
            f"{humidity_change:+.1f} %"
        ],

        [
            "แนวโน้มอุณหภูมิ",
            temperature_trend
        ],

        [
            "ความสัมพันธ์อุณหภูมิและความชื้น",
            relation
        ],

        [
            "ช่วงที่ควรเฝ้าระวัง",
            watch_message
        ],

        [
            "ข้อเสนอแนะ",
            recommendation
        ]

    ]


    # ========================================================
    # เปิด / สร้าง Analysis
    # ========================================================

    try:

        analysis_sheet = (
            spreadsheet.worksheet(
                "Analysis"
            )
        )

    except gspread.WorksheetNotFound:

        analysis_sheet = (
            spreadsheet.add_worksheet(
                title="Analysis",
                rows=30,
                cols=3
            )
        )


    # ========================================================
    # เขียนผลวิเคราะห์
    # ========================================================

    analysis_sheet.clear()

    analysis_sheet.update(
        "A1",
        analysis_data
    )


    return {

        "success": True,

        "message":
            "วิเคราะห์ข้อมูลสำเร็จ",

        "latest_temperature":
            float(latest_temp),

        "latest_humidity":
            float(latest_humidity),

        "temperature_trend":
            temperature_trend

    }


# ============================================================
# 🌐 API
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return jsonify({

        "system":
            "Sheep Farm Smart System",

        "status":
            "Python Service Online"

    })


@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        spreadsheet_id = data.get(
            "spreadsheetId"
        )


        if not spreadsheet_id:

            return jsonify({

                "success": False,

                "error":
                    "ไม่พบ spreadsheetId"

            }), 400


        result = analyze_data(
            spreadsheet_id
        )


        return jsonify(
            result
        )


    except Exception as error:

        return jsonify({

            "success": False,

            "error":
                str(error)

        }), 500


# ============================================================
# 🚀 Run
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            8080
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )