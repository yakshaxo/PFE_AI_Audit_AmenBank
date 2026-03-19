cd

import psycopg2
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import json
import os
import sys

# Database settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'StrongPassword123'
}

def get_stats():
    """Get all statistics from database"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Total problems
    cursor.execute("SELECT COUNT(*) FROM problem WHERE clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')")
    total = cursor.fetchone()[0]
    
    # Critical problems
    cursor.execute("SELECT COUNT(*) FROM problem WHERE clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour') AND severity >= 4")
    critical = cursor.fetchone()[0]
    
    # Recent problems (top 8 for single page)
    cursor.execute("""
        SELECT TO_TIMESTAMP(clock), name, severity
        FROM problem 
        WHERE clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')
        ORDER BY severity DESC, clock DESC 
        LIMIT 8
    """)
    problems = cursor.fetchall()
    
    conn.close()
    return total, critical, problems

def get_ai_stats():
    """Parse AI audit log"""
    ai_stats = {'total': 0, 'anomalies': 0}
    
    try:
        log_path = os.path.join('..', 'logs', 'audit.log')
        if os.path.exists(log_path):
            cutoff = datetime.now().timestamp() - 86400  # 24h ago
            
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        
                        # Check timestamp
                        timestamp_str = entry.get('timestamp', '')
                        try:
                            entry_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if entry_time.timestamp() < cutoff:
                                continue
                        except:
                            pass
                        
                        if entry.get('action') == 'AI_PREDICTION':
                            ai_stats['total'] += 1
                            prediction = entry.get('data', {}).get('prediction', '')
                            if 'ANOMALY' in prediction or 'CRITICAL' in prediction or 'WARNING' in prediction:
                                ai_stats['anomalies'] += 1
                    except:
                        continue
    except Exception as e:
        print(f"Note: Could not read AI audit log: {e}")
    
    return ai_stats

def generate_pdf(total, critical, problems, ai_stats):
    """Generate single-page PDF"""
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    
    doc = SimpleDocTemplate(
        filename, 
        pagesize=A4,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a237e'),
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=15
    )
    
    story = []
    
    # === HEADER ===
    story.append(Paragraph("RAPPORT QUOTIDIEN DE MONITORING", title_style))
    story.append(Paragraph(f"Amen Bank - {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
    
    # === SUMMARY TABLE ===
    summary_data = [
        ["Indicateur", "Valeur", "Intelligence Artificielle"],
        [f"Problemes (24h)", str(total), f"Alertes analysees: {ai_stats['total']}"],
        [f"Critiques", str(critical), f"Anomalies detectees: {ai_stats['anomalies']}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[7*cm, 3*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))
    
    # === PROBLEMS TABLE ===
    story.append(Paragraph("<b>Problemes Recents:</b>", styles['Heading3']))
    story.append(Spacer(1, 5))
    
    if problems:
        prob_data = [["Heure", "Probleme", "Severite"]]
        
        for p in problems:
            time_str = p[0].strftime('%d/%m %H:%M')
            problem_name = p[1][:55] + "..." if len(p[1]) > 55 else p[1]
            severity_map = {5: "DISASTER", 4: "HIGH", 3: "AVERAGE", 2: "WARNING", 1: "INFO"}
            severity = severity_map.get(p[2], "INFO")
            prob_data.append([time_str, problem_name, severity])
        
        prob_table = Table(prob_data, colWidths=[3*cm, 9*cm, 2.5*cm])
        prob_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d32f2f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ffebee')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(prob_table)
    else:
        story.append(Paragraph("[OK] Aucun probleme detecte.", styles['Normal']))
    
    story.append(Spacer(1, 15))
    
    # === RECOMMENDATIONS ===
    story.append(Paragraph("<b>Recommandations:</b>", styles['Heading3']))
    story.append(Spacer(1, 5))
    
    recs = []
    if critical > 3:
        recs.append("[URGENT] Action urgente: Plus de 3 problemes critiques detectes.")
    if ai_stats['anomalies'] > 5:
        recs.append("[IA] Anomalies detectees - verifier les serveurs concernes.")
    if total == 0:
        recs.append("[OK] Systeme stable - Aucune action requise.")
    if not recs:
        recs.append("[INFO] Surveillance continue recommandee.")
    
    for rec in recs:
        story.append(Paragraph(f"• {rec}", styles['Normal']))
    
    story.append(Spacer(1, 10))
    
    # === FOOTER ===
    story.append(Paragraph(
        "<i>Genere automatiquement par le Systeme de Monitoring Intelligent - PFE ESPRIT</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(story)
    return filename

def main():
    """Main function"""
    print("=" * 50)
    print("GENERATION DU RAPPORT QUOTIDIEN - AMEN BANK")
    print("=" * 50)
    print()
    
    try:
        # Get data
        print("Connexion a la base de donnees...")
        total, critical, problems = get_stats()
        print(f"[OK] Problemes: {total} (dont {critical} critiques)")
        
        print("Analyse des logs IA...")
        ai_stats = get_ai_stats()
        print(f"[OK] IA: {ai_stats['total']} alertes analysees, {ai_stats['anomalies']} anomalies")
        
        # Generate PDF
        print()
        print("Generation du PDF...")
        pdf_file = generate_pdf(total, critical, problems, ai_stats)
        
        print()
        print("=" * 50)
        print(f"[SUCCESS] Rapport genere: {pdf_file}")
        print("=" * 50)
        
    except Exception as e:
        print()
        print("=" * 50)
        print(f"[ERROR] Erreur: {e}")
        print("=" * 50)
        sys.exit(1)

if __name__ == "__main__":
    main()