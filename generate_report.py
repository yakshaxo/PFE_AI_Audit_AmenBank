
import psycopg2
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib import colors
import os
import json
import sys

# ============================================
# CONFIGURATION
# ============================================

DB_CONFIG = {
    'host': 'localhost',  # PostgreSQL exposed on localhost:5432
    'port': 5432,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'StrongPassword123'
}

AUDIT_LOG_PATH = '../logs/audit.log'  # Path to AI engine audit log
REPORTS_DIR = '.'  # Current directory (reports/)

# ============================================
# DATABASE FUNCTIONS
# ============================================

def get_db_connection():
    """Create database connection to Zabbix PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected to Zabbix database")
        return conn
    except Exception as e:
        print(f" Database connection failed: {e}")
        sys.exit(1)

def get_summary_stats(conn):
    """Get executive summary statistics"""
    cursor = conn.cursor()
    
    stats = {}
    
    # Total problems last 24h
    cursor.execute("""
        SELECT COUNT(*) 
        FROM problem 
        WHERE clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')
    """)
    stats['total_problems'] = cursor.fetchone()[0]
    
    # Critical problems (severity >= 4)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM problem 
        WHERE clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')
        AND severity >= 4
    """)
    stats['critical_problems'] = cursor.fetchone()[0]
    
    # Active unresolved problems
    cursor.execute("""
        SELECT COUNT(*) 
        FROM problem 
        WHERE r_eventid IS NULL
    """)
    stats['active_problems'] = cursor.fetchone()[0]
    
    # Most affected host
    cursor.execute("""
        SELECT h.host, COUNT(*) as problem_count
        FROM problem p
        INNER JOIN triggers t ON p.objectid = t.triggerid
        INNER JOIN functions f ON t.triggerid = f.triggerid
        INNER JOIN items i ON f.itemid = i.itemid
        INNER JOIN hosts h ON i.hostid = h.hostid
        WHERE p.clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')
        GROUP BY h.host
        ORDER BY problem_count DESC
        LIMIT 1
    """)
    result = cursor.fetchone()
    stats['top_host'] = result[0] if result else "Aucun"
    stats['top_host_count'] = result[1] if result else 0
    
    cursor.close()
    return stats

def get_recent_problems(conn, limit=20):
    """Get recent problems from last 24 hours"""
    cursor = conn.cursor()
    
    query = """
    SELECT 
        TO_TIMESTAMP(p.clock) as time,
        h.host as host,
        t.description as problem,
        CASE 
            WHEN p.severity = 5 THEN 'DISASTER'
            WHEN p.severity = 4 THEN 'HIGH'
            WHEN p.severity = 3 THEN 'AVERAGE'
            WHEN p.severity = 2 THEN 'WARNING'
            ELSE 'INFO'
        END as severity,
        p.severity as severity_num
    FROM problem p
    INNER JOIN triggers t ON p.objectid = t.triggerid
    INNER JOIN functions f ON t.triggerid = f.triggerid
    INNER JOIN items i ON f.itemid = i.itemid
    INNER JOIN hosts h ON i.hostid = h.hostid
    WHERE p.clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')
    ORDER BY p.severity DESC, p.clock DESC
    LIMIT %s
    """
    
    cursor.execute(query, (limit,))
    results = cursor.fetchall()
    cursor.close()
    
    return results

# ============================================
# AI AUDIT LOG FUNCTIONS
# ============================================

def parse_audit_log():
    """Parse AI engine audit log and extract statistics"""
    
    ai_stats = {
        'total_alerts_processed': 0,
        'anomalies_detected': 0,
        'normal_predictions': 0,
        'warnings': 0,
        'criticals': 0
    }
    
    try:
        if not os.path.exists(AUDIT_LOG_PATH):
            print(f" Audit log not found at {AUDIT_LOG_PATH}")
            return ai_stats
            
        # Read last 24h of audit log
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        with open(AUDIT_LOG_PATH, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry.get('timestamp', ''))
                    
                    if entry_time < cutoff_time:
                        continue
                    
                    action = entry.get('action', '')
                    data = entry.get('data', {})
                    
                    if action == 'AI_PREDICTION':
                        ai_stats['total_alerts_processed'] += 1
                        
                        prediction = data.get('prediction', '')
                        if 'CRITICAL' in prediction:
                            ai_stats['criticals'] += 1
                            ai_stats['anomalies_detected'] += 1
                        elif 'WARNING' in prediction or 'UNUSUAL' in prediction:
                            ai_stats['warnings'] += 1
                            ai_stats['anomalies_detected'] += 1
                        elif 'NORMAL' in prediction:
                            ai_stats['normal_predictions'] += 1
                            
                except (json.JSONDecodeError, ValueError):
                    continue
        
        print(f" Parsed audit log: {ai_stats['total_alerts_processed']} alerts processed")
        
    except Exception as e:
        print(f" Error parsing audit log: {e}")
    
    return ai_stats

# ============================================
# PDF GENERATION
# ============================================

def generate_pdf_report(stats, problems, ai_stats):
    """Generate the PDF report"""
    
    report_date = datetime.now()
    filename = os.path.join(REPORTS_DIR, f"daily_report_{report_date.strftime('%Y%m%d')}.pdf")
    
    print(f"📄 Generating PDF report: {filename}")
    
    # Create PDF
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#455a64'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1976d2'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#e3f2fd'),
        borderPadding=5
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8
    )
    
    # Build document
    story = []
    
    # === HEADER ===
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("RAPPORT QUOTIDIEN DE MONITORING", title_style))
    story.append(Paragraph("Système d'Audit Intelligent - Amen Bank", subtitle_style))
    story.append(Paragraph(f"Généré le {report_date.strftime('%d/%m/%Y à %H:%M')}", subtitle_style))
    
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1976d2'), spaceBefore=10, spaceAfter=20))
    
    # === EXECUTIVE SUMMARY ===
    story.append(Paragraph("I. SYNTHÈSE EXÉCUTIVE", section_style))
    story.append(Spacer(1, 0.3*cm))
    
    summary_data = [
        ["Indicateur", "Valeur", "Status"],
        ["Problèmes détectés (24h)", str(stats['total_problems']), "🔍"],
        ["Problèmes critiques", str(stats['critical_problems']), 
         "🔴" if stats['critical_problems'] > 0 else "✅"],
        ["Problèmes actifs (non résolus)", str(stats['active_problems']),
         "⚠️" if stats['active_problems'] > 5 else "✅"],
        ["Serveur le plus affecté", f"{stats['top_host']} ({stats['top_host_count']} alertes)", "📊"]
    ]
    
    summary_table = Table(summary_data, colWidths=[7*cm, 5*cm, 2*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
    ]))
    story.append(summary_table)
    
    # === AI ANALYSIS SUMMARY ===
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("II. ANALYSE PAR INTELLIGENCE ARTIFICIELLE", section_style))
    story.append(Spacer(1, 0.3*cm))
    
    ai_data = [
        ["Métrique IA", "Valeur"],
        ["Alertes analysées (24h)", str(ai_stats['total_alerts_processed'])],
        ["Anomalies détectées", str(ai_stats['anomalies_detected'])],
        ["  └─ Critiques", str(ai_stats['criticals'])],
        ["  └─ Avertissements", str(ai_stats['warnings'])],
        ["Prédictions normales", str(ai_stats['normal_predictions'])],
        ["Taux de détection d'anomalies", 
         f"{(ai_stats['anomalies_detected'] / max(ai_stats['total_alerts_processed'], 1) * 100):.1f}%"]
    ]
    
    ai_table = Table(ai_data, colWidths=[10*cm, 4*cm])
    ai_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6f00')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff3e0')])
    ]))
    story.append(ai_table)
    
    story.append(PageBreak())
    
    # === PROBLEMS DETAIL ===
    story.append(Paragraph("III. DÉTAIL DES PROBLÈMES (24 DERNIÈRES HEURES)", section_style))
    story.append(Spacer(1, 0.3*cm))
    
    if problems:
        problems_data = [["Heure", "Serveur", "Problème", "Sévérité"]]
        
        for problem in problems[:15]:  # Top 15
            time_str = problem[0].strftime('%d/%m %H:%M')
            host = problem[1][:20] if len(problem[1]) > 20 else problem[1]
            desc = problem[2][:50] + "..." if len(problem[2]) > 50 else problem[2]
            severity = problem[3]
            
            problems_data.append([time_str, host, desc, severity])
        
        problems_table = Table(problems_data, colWidths=[3*cm, 3.5*cm, 6*cm, 1.5*cm])
        problems_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d32f2f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ffebee')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        story.append(problems_table)
    else:
        story.append(Paragraph("✅ Aucun problème détecté dans les dernières 24 heures.", normal_style))
    
    # === RECOMMENDATIONS ===
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("IV. RECOMMANDATIONS", section_style))
    story.append(Spacer(1, 0.3*cm))
    
    recommendations = []
    
    if stats['critical_problems'] > 3:
        recommendations.append("🔴 <b>Action urgente:</b> Plus de 3 problèmes critiques détectés. Intervention immédiate requise.")
    
    if stats['active_problems'] > 10:
        recommendations.append("⚠️ <b>Attention:</b> Nombre élevé de problèmes non résolus. Planifier une session de maintenance.")
    
    if ai_stats['criticals'] > 5:
        recommendations.append("🤖 <b>IA:</b> Anomalies critiques détectées par l'IA. Vérifier les serveurs concernés.")
    
    if stats['top_host_count'] > 5:
        recommendations.append(f"📊 <b>Surveillance accrue:</b> Le serveur {stats['top_host']} nécessite une attention particulière ({stats['top_host_count']} alertes).")
    
    if not recommendations:
        recommendations.append("✅ <b>Système stable:</b> Tous les indicateurs sont dans les normes. Aucune action requise.")
    
    for rec in recommendations:
        story.append(Paragraph(f"• {rec}", normal_style))
    
    story.append(Spacer(1, 1.5*cm))
    
    # === FOOTER ===
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceBefore=20, spaceAfter=10))
    story.append(Paragraph(
        f"<i>Rapport généré automatiquement par le Système de Monitoring Intelligent - Amen Bank</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    ))
    story.append(Paragraph(
        f"<i>Projet PFE - ESPRIT 2024/2025 | Contact: louay@esprit.tn</i>",
        ParagraphStyle('Footer2', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    ))
    
    # Build PDF
    doc.build(story)
    print(f"✅ Rapport PDF généré avec succès: {filename}")
    return filename

# ============================================
# MAIN FUNCTION
# ============================================

def main():
    """Main function to generate daily report"""
    
    print("=" * 60)
    print("📊 GÉNÉRATION DU RAPPORT QUOTIDIEN - AMEN BANK")
    print("=" * 60)
    print()
    
    # 1. Connect to database
    conn = get_db_connection()
    
    # 2. Get summary statistics
    print("📈 Récupération des statistiques...")
    stats = get_summary_stats(conn)
    print(f"  - Total problèmes: {stats['total_problems']}")
    print(f"  - Problèmes critiques: {stats['critical_problems']}")
    print(f"  - Problèmes actifs: {stats['active_problems']}")
    
    # 3. Get recent problems
    print("📋 Récupération des problèmes récents...")
    problems = get_recent_problems(conn, limit=20)
    print(f"  - {len(problems)} problèmes trouvés")
    
    # 4. Parse AI audit log
    print("🤖 Analyse des logs IA...")
    ai_stats = parse_audit_log()
    print(f"  - {ai_stats['total_alerts_processed']} alertes analysées par l'IA")
    print(f"  - {ai_stats['anomalies_detected']} anomalies détectées")
    
    # 5. Generate PDF
    print()
    pdf_file = generate_pdf_report(stats, problems, ai_stats)
    
    # 6. Close database connection
    conn.close()
    
    print()
    print("=" * 60)
    print(f"✅ RAPPORT GÉNÉRÉ: {pdf_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()
