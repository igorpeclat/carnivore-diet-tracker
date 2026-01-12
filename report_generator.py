import os
import json
import csv
from datetime import datetime
from typing import List, Dict


def generate_daily_report(user_name: str, date: str, meals: List[Dict], totals: Dict) -> str:
    css = """
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 700px; margin: 0 auto; background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { color: #ff5252; text-align: center; border-bottom: 2px solid #ff5252; padding-bottom: 10px; }
        h2 { color: #ffffff; margin-top: 30px; }
        .summary-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 20px; }
        .card { background: #2c2c2c; padding: 15px; border-radius: 8px; text-align: center; }
        .card-value { font-size: 24px; font-weight: bold; display: block; }
        .card-label { font-size: 12px; color: #aaa; text-transform: uppercase; }
        .p-color { color: #f48fb1; }
        .f-color { color: #fff59d; }
        .c-color { color: #ffab91; }
        .meal-item { background: #252525; border-left: 4px solid #ff5252; margin-bottom: 10px; padding: 15px; border-radius: 4px; }
        .meal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
        .meal-time { color: #888; font-size: 14px; }
        .meal-title { font-weight: bold; font-size: 16px; }
        .meal-macros { font-size: 13px; color: #bbb; }
        .tag { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
        .footer { text-align: center; margin-top: 40px; color: #666; font-size: 12px; }
        .chart-container { background: #252525; border-radius: 8px; padding: 20px; margin: 20px 0; }
        .timeline { position: relative; padding: 20px 0; }
        .timeline-item { display: flex; align-items: center; margin: 10px 0; }
        .timeline-dot { width: 12px; height: 12px; background: #ff5252; border-radius: 50%; margin-right: 15px; }
        .timeline-content { flex: 1; background: #2c2c2c; padding: 10px 15px; border-radius: 6px; }
        .timeline-time { color: #888; font-size: 12px; }
        .progress-bar { background: #333; border-radius: 10px; height: 20px; overflow: hidden; margin: 5px 0; }
        .progress-fill { height: 100%; border-radius: 10px; transition: width 0.3s; }
    </style>
    """
    
    summary_html = f"""
    <div class="summary-grid">
        <div class="card">
            <span class="card-value p-color">{totals.get('protein', 0)}g</span>
            <span class="card-label">Proteína</span>
        </div>
        <div class="card">
            <span class="card-value f-color">{totals.get('fat', 0)}g</span>
            <span class="card-label">Gordura</span>
        </div>
        <div class="card">
            <span class="card-value c-color">{totals.get('calories', 0)}</span>
            <span class="card-label">Kcal</span>
        </div>
    </div>
    """
    
    chart_html = _generate_macro_pie_chart(totals)
    
    timeline_html = _generate_timeline(meals)
    
    meals_html = ""
    for m in meals:
        icon = '📸' if m.get('source') == 'photo' else '🎙️' if m.get('source') == 'voice' else '📝'
        macros = m.get('macros', {})
        p = macros.get('protein', 0)
        f = macros.get('fat', 0)
        
        meals_html += f"""
        <div class="meal-item">
            <div class="meal-header">
                <span class="meal-title">{icon} {m.get('summary', 'Refeição')}</span>
                <span class="meal-time">{m.get('time', '')}</span>
            </div>
            <div class="meal-macros">
                P: {p}g | G: {f}g | {m.get('calories', 0)} kcal
            </div>
        </div>
        """
        
    if not meals:
        meals_html = "<p style='text-align:center; color:#555;'>Nenhum registro hoje. Está em jejum? 🦁</p>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório Carnívoro - {date}</title>
        {css}
    </head>
    <body>
        <div class="container">
            <h1>🦁 Diário Carnívoro</h1>
            <p style="text-align:center; color:#888;">{date} • {user_name}</p>
            
            {summary_html}
            
            <h2>📊 Distribuição de Macros</h2>
            {chart_html}
            
            <h2>⏰ Linha do Tempo</h2>
            {timeline_html}
            
            <h2>🍽️ Refeições</h2>
            {meals_html}
            
            <div class="footer">
                Carnivore Tracker • Stay Meat-Based 🥩
            </div>
        </div>
    </body>
    </html>
    """
    
    filename = f"/tmp/report_{user_name}_{date}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    return filename


def _generate_macro_pie_chart(totals: Dict) -> str:
    protein = totals.get('protein', 0)
    fat = totals.get('fat', 0)
    
    protein_cal = protein * 4
    fat_cal = fat * 9
    total_cal = protein_cal + fat_cal
    
    if total_cal == 0:
        return "<p style='text-align:center; color:#666;'>Sem dados para gráfico</p>"
    
    protein_pct = (protein_cal / total_cal) * 100
    fat_pct = (fat_cal / total_cal) * 100
    
    protein_angle = (protein_pct / 100) * 360
    
    return f"""
    <div class="chart-container" style="text-align: center;">
        <svg width="200" height="200" viewBox="0 0 200 200">
            <circle cx="100" cy="100" r="80" fill="none" stroke="#fff59d" stroke-width="30" 
                    stroke-dasharray="{fat_pct * 5.02} 502" transform="rotate(-90 100 100)"/>
            <circle cx="100" cy="100" r="80" fill="none" stroke="#f48fb1" stroke-width="30" 
                    stroke-dasharray="{protein_pct * 5.02} 502" 
                    stroke-dashoffset="-{fat_pct * 5.02}" transform="rotate(-90 100 100)"/>
            <text x="100" y="95" text-anchor="middle" fill="#fff" font-size="14">
                {totals.get('calories', 0)} kcal
            </text>
            <text x="100" y="115" text-anchor="middle" fill="#888" font-size="11">
                G/P: {round(fat/protein, 1) if protein > 0 else 0}
            </text>
        </svg>
        <div style="display: flex; justify-content: center; gap: 20px; margin-top: 10px;">
            <span><span style="color:#f48fb1;">●</span> Proteína {protein_pct:.0f}%</span>
            <span><span style="color:#fff59d;">●</span> Gordura {fat_pct:.0f}%</span>
        </div>
    </div>
    """


def _generate_timeline(meals: List[Dict]) -> str:
    if not meals:
        return "<p style='text-align:center; color:#666;'>Nenhuma refeição registrada</p>"
    
    html = '<div class="timeline">'
    for m in sorted(meals, key=lambda x: x.get('time', '')):
        icon = '📸' if m.get('source') == 'photo' else '🎙️' if m.get('source') == 'voice' else '📝'
        html += f"""
        <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-time">{m.get('time', '')}</div>
                <div>{icon} {m.get('summary', 'Refeição')[:40]}</div>
                <div style="color:#888; font-size:12px;">{m.get('calories', 0)} kcal</div>
            </div>
        </div>
        """
    html += '</div>'
    return html


def generate_weekly_report(user_name: str, weekly_data: Dict) -> str:
    css = """
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background-color: #1e1e1e; padding: 20px; border-radius: 10px; }
        h1 { color: #ff5252; text-align: center; border-bottom: 2px solid #ff5252; padding-bottom: 10px; }
        h2 { color: #ffffff; margin-top: 30px; }
        .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }
        .stat-card { background: #2c2c2c; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 28px; font-weight: bold; color: #ff5252; }
        .stat-label { font-size: 11px; color: #888; text-transform: uppercase; }
        .bar-chart { margin: 20px 0; }
        .bar-row { display: flex; align-items: center; margin: 8px 0; }
        .bar-label { width: 80px; font-size: 12px; color: #888; }
        .bar-container { flex: 1; background: #333; height: 24px; border-radius: 4px; overflow: hidden; }
        .bar-fill { height: 100%; background: linear-gradient(90deg, #ff5252, #ff8a80); border-radius: 4px; }
        .bar-value { width: 80px; text-align: right; font-size: 12px; }
        .footer { text-align: center; margin-top: 40px; color: #666; font-size: 12px; }
    </style>
    """
    
    daily = weekly_data.get('daily_breakdown', {})
    max_cal = max((d.get('calories', 0) for d in daily.values()), default=1) or 1
    
    bars_html = ""
    for day in sorted(daily.keys()):
        d = daily[day]
        pct = (d.get('calories', 0) / max_cal) * 100
        day_label = day[-5:]
        bars_html += f"""
        <div class="bar-row">
            <span class="bar-label">{day_label}</span>
            <div class="bar-container">
                <div class="bar-fill" style="width: {pct}%;"></div>
            </div>
            <span class="bar-value">{d.get('calories', 0):.0f} kcal</span>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório Semanal</title>
        {css}
    </head>
    <body>
        <div class="container">
            <h1>📈 Relatório Semanal</h1>
            <p style="text-align:center; color:#888;">{user_name} • Últimos 7 dias</p>
            
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-value">{weekly_data.get('total_meals', 0)}</div>
                    <div class="stat-label">Refeições</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{weekly_data.get('avg_daily_calories', 0):.0f}</div>
                    <div class="stat-label">Kcal/dia</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{weekly_data.get('compliance', 0):.0f}%</div>
                    <div class="stat-label">Aderência</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{weekly_data.get('weight_change', 0):+.1f}</div>
                    <div class="stat-label">Peso (kg)</div>
                </div>
            </div>
            
            <h2>📊 Calorias por Dia</h2>
            <div class="bar-chart">
                {bars_html}
            </div>
            
            <h2>📋 Resumo</h2>
            <p>💪 Proteína média: {weekly_data.get('avg_daily_protein', 0):.0f}g/dia</p>
            <p>🧈 Gordura média: {weekly_data.get('avg_daily_fat', 0):.0f}g/dia</p>
            <p>⏳ Jejuns: {weekly_data.get('fasts_completed', 0)} ({weekly_data.get('total_fasting_hours', 0):.1f}h total)</p>
            <p>🩺 Sintomas: {weekly_data.get('symptoms_logged', 0)} registros</p>
            
            <div class="footer">
                Carnivore Tracker • Weekly Summary 🥩
            </div>
        </div>
    </body>
    </html>
    """
    
    filename = f"/tmp/weekly_report_{user_name}_{datetime.now().strftime('%Y-%m-%d')}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    return filename


def export_to_csv(user_name: str, meals: List[Dict], date_range: str = "daily") -> str:
    filename = f"/tmp/export_{user_name}_{date_range}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['datetime', 'summary', 'calories', 'protein_g', 'fat_g', 'carnivore_level', 'source'])
        
        for m in meals:
            macros = m.get('macros', {})
            writer.writerow([
                m.get('datetime', m.get('time', '')),
                m.get('summary', ''),
                m.get('calories', 0),
                macros.get('protein', m.get('protein_g', 0)),
                macros.get('fat', m.get('fat_g', 0)),
                m.get('carnivore_level', 'unknown'),
                m.get('source', 'unknown'),
            ])
    
    return filename


def export_to_json(user_name: str, data: Dict, date_range: str = "daily") -> str:
    filename = f"/tmp/export_{user_name}_{date_range}_{datetime.now().strftime('%Y%m%d')}.json"
    
    export_data = {
        "user": user_name,
        "exported_at": datetime.now().isoformat(),
        "date_range": date_range,
        "data": data,
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    return filename
