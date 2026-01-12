import os

def generate_daily_report(user_name, date, meals, totals):
    """
    Gera um relatório HTML elegante e carnívoro.
    totals: {'protein': int, 'fat': int, 'calories': int}
    """
    
    # CSS Customizado (Dark Mode Carnivore)
    css = """
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #1e1e1e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { color: #ff5252; text-align: center; border-bottom: 2px solid #ff5252; padding-bottom: 10px; }
        h2 { color: #ffffff; margin-top: 30px; }
        .summary-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 20px; }
        .card { background: #2c2c2c; padding: 15px; border-radius: 8px; text-align: center; }
        .card-value { font-size: 24px; font-weight: bold; display: block; }
        .card-label { font-size: 12px; color: #aaa; text-transform: uppercase; }
        .p-color { color: #f48fb1; } /* Protein */
        .f-color { color: #fff59d; } /* Fat */
        .c-color { color: #ffab91; } /* Calories */
        
        .meal-item { background: #252525; border-left: 4px solid #ff5252; margin-bottom: 10px; padding: 15px; border-radius: 4px; }
        .meal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
        .meal-time { color: #888; font-size: 14px; }
        .meal-title { font-weight: bold; font-size: 16px; }
        .meal-macros { font-size: 13px; color: #bbb; }
        .tag { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
        .footer { text-align: center; margin-top: 40px; color: #666; font-size: 12px; }
    </style>
    """
    
    # Cards de Resumo
    summary_html = f"""
    <div class="summary-grid">
        <div class="card">
            <span class="card-value p-color">{totals['protein']}g</span>
            <span class="card-label">Proteína</span>
        </div>
        <div class="card">
            <span class="card-value f-color">{totals['fat']}g</span>
            <span class="card-label">Gordura</span>
        </div>
        <div class="card">
            <span class="card-value c-color">{totals['calories']}</span>
            <span class="card-label">Kcal</span>
        </div>
    </div>
    """
    
    # Lista de Refeições
    meals_html = ""
    for m in meals:
        icon = '📸' if m['source']=='photo' else '🎙️'
        macros = m.get('macros', {})
        p = macros.get('protein', 0)
        f = macros.get('fat', 0)
        
        meals_html += f"""
        <div class="meal-item">
            <div class="meal-header">
                <span class="meal-title">{icon} {m['summary']}</span>
                <span class="meal-time">{m['time']}</span>
            </div>
            <div class="meal-macros">
                P: {p}g | G: {f}g | {m['calories']} kcal
            </div>
        </div>
        """
        
    if not meals:
        meals_html = "<p style='text-align:center; color:#555;'>Nenhum registro hoje. Está em jejum? 🦁</p>"

    # Montagem Final
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Relatório Carnívoro</title>
        {css}
    </head>
    <body>
        <div class="container">
            <h1>🦁 Diário Carnívoro</h1>
            <p style="text-align:center; color:#888;">{date} • {user_name}</p>
            
            {summary_html}
            
            <h2>Refeições</h2>
            {meals_html}
            
            <div class="footer">
                NutriBot AI • Stay Carnivore
            </div>
        </div>
    </body>
    </html>
    """
    
    filename = f"/tmp/report_{user_name}_{date}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    return filename
