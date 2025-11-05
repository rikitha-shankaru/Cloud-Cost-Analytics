"""
Export utilities for generating CSV and PDF reports.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import base64
from io import BytesIO
import plotly.graph_objects as go


def export_to_csv(data, filename=None):
    """
    Export data to CSV format.
    
    Args:
        data: DataFrame or list of dictionaries
        filename: Optional filename
        
    Returns:
        CSV string
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data
    
    if filename:
        df.to_csv(filename, index=False)
        return f"Exported to {filename}"
    
    return df.to_csv(index=False)


def generate_pdf_report(pricing_data, comparisons=None, output_path=None):
    """
    Generate a PDF report with pricing data and charts.
    
    Args:
        pricing_data: List of pricing dictionaries
        comparisons: Optional TCO comparisons
        output_path: Optional output file path
        
    Returns:
        BytesIO object with PDF content
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Cloud Cost Analytics Report", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # Date
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_para = Paragraph(f"Generated: {date_str}", styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 0.3*inch))
        
        # Summary
        compute_count = len([p for p in pricing_data if p.get('price_per_hour')])
        storage_count = len([p for p in pricing_data if p.get('price_per_gb_month')])
        
        summary_text = f"""
        <b>Summary:</b><br/>
        Total SKUs: {len(pricing_data)}<br/>
        Compute Instances: {compute_count}<br/>
        Storage Options: {storage_count}
        """
        story.append(Paragraph(summary_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Pricing Table
        if pricing_data:
            df = pd.DataFrame(pricing_data)
            display_df = df[["provider", "instance_type", "price_per_hour", "price_per_gb_month", 
                            "vcpu", "memory_gb"]].fillna("-")
            
            table_data = [["Provider", "Instance Type", "Price/Hour", "Price/GB-Month", "vCPU", "Memory (GB)"]]
            for _, row in display_df.iterrows():
                table_data.append([
                    str(row['provider']),
                    str(row['instance_type']),
                    f"${row['price_per_hour']:.4f}" if row['price_per_hour'] != "-" else "-",
                    f"${row['price_per_gb_month']:.4f}" if row['price_per_gb_month'] != "-" else "-",
                    str(row['vcpu']) if row['vcpu'] != "-" else "-",
                    str(row['memory_gb']) if row['memory_gb'] != "-" else "-"
                ])
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(table)
            story.append(Spacer(1, 0.3*inch))
        
        # TCO Comparisons
        if comparisons:
            story.append(Paragraph("<b>TCO Comparisons:</b>", styles['Heading3']))
            comp_data = [["Provider", "Total Cost", "Hourly", "Monthly", "Yearly"]]
            for comp in comparisons:
                if "error" not in comp:
                    comp_data.append([
                        comp['provider'].upper(),
                        f"${comp['total_cost_5yr']:,.2f}",
                        f"${comp['hourly_price']:.4f}",
                        f"${comp['monthly_cost']:,.2f}",
                        f"${comp['yearly_cost']:,.2f}"
                    ])
            
            if len(comp_data) > 1:
                comp_table = Table(comp_data)
                comp_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(comp_table)
        
        doc.build(story)
        buffer.seek(0)
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
            return f"PDF exported to {output_path}"
        
        return buffer
        
    except ImportError:
        return "PDF generation requires reportlab. Install with: pip install reportlab"


def detect_cost_anomalies(pricing_data, threshold=0.3):
    """
    Detect cost anomalies in pricing data.
    
    Args:
        pricing_data: List of pricing dictionaries
        threshold: Anomaly threshold (default 30% deviation from mean)
        
    Returns:
        List of anomalies detected
    """
    if not pricing_data:
        return []
    
    df = pd.DataFrame(pricing_data)
    compute_df = df[df['price_per_hour'].notna()].copy()
    
    if compute_df.empty:
        return []
    
    compute_df['cost_per_vcpu'] = compute_df['price_per_hour'] / compute_df['vcpu']
    mean_cost = compute_df['cost_per_vcpu'].mean()
    std_cost = compute_df['cost_per_vcpu'].std()
    
    anomalies = []
    for _, row in compute_df.iterrows():
        deviation = abs(row['cost_per_vcpu'] - mean_cost) / mean_cost
        if deviation > threshold:
            anomalies.append({
                'provider': row['provider'],
                'instance_type': row['instance_type'],
                'cost_per_vcpu': row['cost_per_vcpu'],
                'deviation': f"{deviation*100:.1f}%",
                'status': 'high' if row['cost_per_vcpu'] > mean_cost else 'low'
            })
    
    return anomalies

