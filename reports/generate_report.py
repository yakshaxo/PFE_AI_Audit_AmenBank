import psycopg2
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import sys

# Zabbix database
ZABBIX_DB = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zabbix',
    'user': 'zabbix',
    'password': 'StrongPassword123'
}

# AI audit database
AI_DB = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ai_audit',
    'user': 'zabbix',
    'password': 'StrongPassword123'
}


def get_zabbix_stats():
    """Get problem statistics from Zabbix database"""
    conn = psycopg2.connect(**ZABBIX_DB)
    cursor = conn.cursor()

    # Total problems in last 24h
    cursor.execute("""
        SELECT COUNT(*) FROM problem
        WHERE clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')
    """)
    total = cursor.fetchone()[0]

    # Critical problems
    cursor.execute("""
        SELECT COUNT(*) FROM problem
        WHERE clock > EXTRACT(epoch FROM NOW() - INTERVAL '24 hour')
        AND severity >= 4
    """)
    critical = cursor.fetchone()[0]

    # Recent problems (top 8)
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
    """Get AI analysis statistics from ai_audit database"""
    try:
        conn = psycopg2.connect(**AI_DB)
        cursor = conn.cursor()

        # Total analyses in last 24h
        cursor.execute("""
            SELECT COUNT(*) FROM ai_results
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)
        total = cursor.fetchone()[0]

        # Total anomalies
        cursor.execute("""
            SELECT COUNT(*) FROM ai_results
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            AND prediction = 'ANOMALY'
        """)
        anomalies = cursor.fetchone()[0]

        # Top anomalous hosts
        cursor.execute("""
            SELECT host, COUNT(*) as count, MAX(severity) as max_severity
            FROM ai_results
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            AND prediction = 'ANOMALY'
            GROUP BY host
            ORDER BY count DESC
            LIMIT 5
        """)
        anomalous_hosts = cursor.fetchall()

        # Recent AI results
        cursor.execute("""
            SELECT timestamp, host, prediction, severity, score
            FROM ai_results
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY timestamp DESC
            LIMIT 8
        """)
        recent_results = cursor.fetchall()

        conn.close()
        return {
            'total': total,
            'anomalies': anomalies,
            'anomalous_hosts': anomalous_hosts,
            'recent_results': recent_results
        }

    except Exception as e:
        print(f"Warning: Could not read AI database: {e}")
        return {
            'total': 0,
            'anomalies': 0,
            'anomalous_hosts': [],
            'recent_results': []
        }


def get_sla_stats():
    """Get SLA for all monitored hosts from Zabbix"""
    try:
        conn = psycopg2.connect(**ZABBIX_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                ho.host,
                AVG(CASE WHEN h.value = 1 THEN 1.0 ELSE 0.0 END) * 100 AS uptime_pct,
                COUNT(CASE WHEN h.value = 0 THEN 1 END) AS incidents
            FROM history_uint h
            JOIN items i ON h.itemid = i.itemid
            JOIN hosts ho ON i.hostid = ho.hostid
            WHERE i.key_ LIKE 'agent.ping%%'
              AND h.clock > EXTRACT(epoch FROM NOW() - INTERVAL '30 days')
            GROUP BY ho.host
            ORDER BY uptime_pct ASC
        """)
        sla_data = cursor.fetchall()
        conn.close()
        return sla_data

    except Exception as e:
        print(f"Warning: Could not read SLA data: {e}")
        return []


def generate_pdf(total, critical, problems, ai_stats, sla_data):
    """Generate single-page PDF report"""
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

    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=5
    )

    story = []

    # === HEADER ===
    story.append(Paragraph("RAPPORT QUOTIDIEN DE MONITORING", title_style))
    story.append(Paragraph(f"Amen Bank - {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))

    # === SUMMARY TABLE ===
    summary_data = [
        ["Indicateur", "Zabbix", "Intelligence Artificielle"],
        ["Problemes (24h)", str(total), f"Alertes analysees: {ai_stats['total']}"],
        ["Critiques", str(critical), f"Anomalies detectees: {ai_stats['anomalies']}"],
    ]

    summary_table = Table(summary_data, colWidths=[6*cm, 3*cm, 6*cm])
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
    story.append(Spacer(1, 12))

    # === ZABBIX PROBLEMS TABLE ===
    story.append(Paragraph("Problemes Zabbix Recents (24h):", section_style))

    if problems:
        prob_data = [["Heure", "Probleme", "Severite"]]
        severity_map = {5: "DISASTER", 4: "HIGH", 3: "AVERAGE", 2: "WARNING", 1: "INFO"}
        for p in problems:
            time_str = p[0].strftime('%d/%m %H:%M')
            problem_name = p[1][:55] + "..." if len(p[1]) > 55 else p[1]
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

    story.append(Spacer(1, 12))

    # === AI RESULTS TABLE ===
    story.append(Paragraph("Analyses IA Recentes (24h):", section_style))

    if ai_stats['recent_results']:
        ai_data = [["Heure", "Hote", "Prediction", "Severite", "Score"]]
        for r in ai_stats['recent_results']:
            ai_data.append([
                r[0].strftime('%d/%m %H:%M'),
                r[1][:20],
                r[2],
                r[3],
                str(r[4])
            ])

        ai_table = Table(ai_data, colWidths=[3*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2*cm])
        ai_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#e8eaf6')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(ai_table)
    else:
        story.append(Paragraph("[OK] Aucune analyse IA dans les dernieres 24h.", styles['Normal']))

    story.append(Spacer(1, 12))

    # === SLA TABLE ===
    story.append(Paragraph("SLA des Serveurs (30 derniers jours):", section_style))

    if sla_data:
        sla_table_data = [["Hote", "Disponibilite", "Incidents", "Statut"]]
        for row in sla_data:
            host = row[0]
            uptime = round(float(row[1]), 2) if row[1] else 100.0
            incidents = row[2] or 0
            status = "GOOD" if uptime >= 99.5 else "POOR"
            status_color = "[OK]" if uptime >= 99.5 else "[!]"
            sla_table_data.append([host, f"{uptime}%", str(incidents), f"{status_color} {status}"])

        sla_table = Table(sla_table_data, colWidths=[5*cm, 3.5*cm, 2.5*cm, 3.5*cm])
        sla_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e7d32')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#e8f5e9')]),
        ]))
        story.append(sla_table)
    else:
        story.append(Paragraph("[INFO] Aucune donnee SLA disponible.", styles['Normal']))

    story.append(Spacer(1, 12))

    # === RECOMMENDATIONS ===
    story.append(Paragraph("Recommandations:", section_style))

    recs = []
    if critical > 3:
        recs.append("[URGENT] Plus de 3 problemes critiques — intervention immediate requise.")
    if ai_stats['anomalies'] > 5:
        recs.append(f"[IA] {ai_stats['anomalies']} anomalies detectees — verifier les serveurs concernes.")
    if ai_stats['anomalous_hosts']:
        top_host = ai_stats['anomalous_hosts'][0]
        recs.append(f"[IA] Hote le plus affecte: {top_host[0]} ({top_host[1]} anomalies).")
    poor_sla = [r for r in sla_data if r[1] and float(r[1]) < 99.5]
    if poor_sla:
        recs.append(f"[SLA] {len(poor_sla)} serveur(s) sous le seuil SLA de 99.5%.")
    if total == 0 and ai_stats['anomalies'] == 0:
        recs.append("[OK] Systeme stable — aucune action requise.")
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

    doc.build(story)
    return filename


def main():
    print("=" * 50)
    print("GENERATION DU RAPPORT QUOTIDIEN - AMEN BANK")
    print("=" * 50)
    print()

    try:
        print("Connexion a Zabbix...")
        total, critical, problems = get_zabbix_stats()
        print(f"[OK] Problemes: {total} (dont {critical} critiques)")

        print("Lecture des analyses IA...")
        ai_stats = get_ai_stats()
        print(f"[OK] IA: {ai_stats['total']} analyses, {ai_stats['anomalies']} anomalies")

        print("Calcul des SLA...")
        sla_data = get_sla_stats()
        print(f"[OK] SLA: {len(sla_data)} serveur(s) analyses")

        print()
        print("Generation du PDF...")
        pdf_file = generate_pdf(total, critical, problems, ai_stats, sla_data)

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