"""
Interactive Plotly Dash dashboard for cloud cost analytics.
Enhanced with advanced features: recommendations, comparisons, exports, and more.
"""

import json
import sys
from pathlib import Path
import dash
from dash import dcc, html, Input, Output, dash_table, State
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import dash_bootstrap_components as dbc
from datetime import datetime
import base64

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cost_model import CostModel
from export_utils import export_to_csv, generate_pdf_report, detect_cost_anomalies

# Initialize Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

# Load pricing data
data_path = Path(__file__).parent.parent / "data" / "normalized.json"
try:
    with open(data_path, "r") as f:
        pricing_data = json.load(f)
    df = pd.DataFrame(pricing_data)
except FileNotFoundError:
    print(f"Warning: {data_path} not found. Run seed_sample_data.py first.")
    df = pd.DataFrame()
    pricing_data = []

# Initialize cost model
cost_model = CostModel(str(data_path))

# Calculate summary metrics
compute_df = df[df['price_per_hour'].notna()].copy() if not df.empty else pd.DataFrame()
if not compute_df.empty:
    compute_df['cost_per_vcpu'] = compute_df['price_per_hour'] / compute_df['vcpu']
    compute_df['cost_per_gb'] = compute_df['price_per_hour'] / compute_df['memory_gb']


# Helper functions
def get_instance_recommendations(vcpu_needed, memory_needed):
    """Recommend instances based on requirements."""
    if compute_df.empty:
        return []
    
    recommendations = []
    for _, row in compute_df.iterrows():
        if row['vcpu'] >= vcpu_needed and row['memory_gb'] >= memory_needed:
            score = (row['vcpu'] - vcpu_needed) + (row['memory_gb'] - memory_needed)  # Lower is better
            recommendations.append({
                'provider': row['provider'],
                'instance_type': row['instance_type'],
                'vcpu': row['vcpu'],
                'memory_gb': row['memory_gb'],
                'price_per_hour': row['price_per_hour'],
                'cost_per_vcpu': row['cost_per_vcpu'],
                'score': score,
                'region': row['region']
            })
    
    return sorted(recommendations, key=lambda x: x['score'])[:5]  # Top 5


def get_optimization_recommendations():
    """Generate cost optimization recommendations."""
    recommendations = []
    
    if compute_df.empty:
        return recommendations
    
    # Recommendation 1: Best value provider
    best_value = compute_df.loc[compute_df['cost_per_vcpu'].idxmin()]
    recommendations.append({
        'type': 'Best Value',
        'title': f"Switch to {best_value['provider'].upper()}",
        'description': f"{best_value['instance_type']} offers lowest cost per vCPU (${best_value['cost_per_vcpu']:.4f})",
        'savings': f"Up to {((compute_df['cost_per_vcpu'].max() - best_value['cost_per_vcpu']) / compute_df['cost_per_vcpu'].max() * 100):.1f}% savings",
        'icon': '💰'
    })
    
    # Recommendation 2: Reserved instances
    avg_hourly = compute_df['price_per_hour'].mean()
    reserved_savings = avg_hourly * 0.3 * 730 * 12  # 30% discount, monthly
    recommendations.append({
        'type': 'Reserved Instances',
        'title': "Consider Reserved Instances",
        'description': "Commit to 1-3 year terms for 30% discount",
        'savings': f"Save ~${reserved_savings:.2f}/year per instance",
        'icon': '💾'
    })
    
    # Recommendation 3: Spot instances
    spot_savings = avg_hourly * 0.6 * 730 * 12  # 60% discount
    recommendations.append({
        'type': 'Spot Instances',
        'title': "Use Spot Instances for Non-Critical Workloads",
        'description': "Save up to 60% for fault-tolerant workloads",
        'savings': f"Save ~${spot_savings:.2f}/year per instance",
        'icon': '⚡'
    })
    
    # Recommendation 4: Right-sizing
    high_cost = compute_df[compute_df['cost_per_vcpu'] > compute_df['cost_per_vcpu'].quantile(0.75)]
    if not high_cost.empty:
        recommendations.append({
            'type': 'Right-Sizing',
            'title': "Right-Size Your Instances",
            'description': f"Review {len(high_cost)} instances with high cost per vCPU",
            'savings': f"Potential 20-40% cost reduction",
            'icon': '📊'
        })
    
    return recommendations


# App layout with tabs
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("🌩 Cloud Cost Analytics Engine", 
                   className="text-center mb-2",
                   style={"fontWeight": "bold", "color": "#1a73e8", "marginTop": "20px"}),
            html.P("Multi-cloud pricing comparison and cost optimization dashboard",
                  className="text-center text-muted mb-4")
        ])
    ]),
    
    # Summary Metrics Cards
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("📊 Total SKUs", className="card-title"),
                    html.H2(f"{len(pricing_data)}", className="text-primary"),
                    html.P(f"{len([p for p in pricing_data if p.get('price_per_hour')])} Compute, {len([p for p in pricing_data if p.get('price_per_gb_month')])} Storage", 
                          className="text-muted mb-0")
                ])
            ], className="mb-4")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("💰 Avg Hourly", className="card-title"),
                    html.H2(f"${compute_df['price_per_hour'].mean():.4f}" if not compute_df.empty else "$0.0000", 
                           className="text-success"),
                    html.P("Across all providers", className="text-muted mb-0")
                ])
            ], className="mb-4")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("⚡ Cost/vCPU", className="card-title"),
                    html.H2(f"${compute_df['cost_per_vcpu'].mean():.4f}" if not compute_df.empty else "$0.0000", 
                           className="text-info"),
                    html.P("Average efficiency", className="text-muted mb-0")
                ])
            ], className="mb-4")
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("🏆 Best Value", className="card-title"),
                    html.H2(f"{compute_df.loc[compute_df['cost_per_vcpu'].idxmin(), 'provider'].upper()}" if not compute_df.empty else "N/A", 
                           className="text-warning"),
                    html.P("Lowest cost per vCPU", className="text-muted mb-0")
                ])
            ], className="mb-4")
        ], width=3)
    ]),
    
    # Tabs for different sections
    dbc.Tabs([
        dbc.Tab(label="📊 Overview", tab_id="overview"),
        dbc.Tab(label="🎯 Recommendations", tab_id="recommendations"),
        dbc.Tab(label="💰 Pricing Models", tab_id="pricing"),
        dbc.Tab(label="🔍 Instance Finder", tab_id="finder"),
        dbc.Tab(label="📈 Projections", tab_id="projections"),
    ], id="tabs", active_tab="overview", className="mb-4"),
    
    html.Div(id="tab-content"),
    
], fluid=True)


@app.callback(
    Output("tab-content", "children"),
    [Input("tabs", "active_tab")]
)
def render_tab_content(active_tab):
    """Render content based on active tab."""
    
    if active_tab == "overview":
        return dbc.Container([
            # Filters
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("🔍 Filters", className="card-title"),
                            html.Label("Provider", className="form-label"),
                            dcc.Dropdown(
                                id="provider-filter",
                                options=[
                                    {"label": "🌐 All Providers", "value": "all"},
                                    {"label": "☁️ AWS", "value": "aws"},
                                    {"label": "🔵 GCP", "value": "gcp"},
                                    {"label": "🟠 OCI", "value": "oci"}
                                ],
                                value="all",
                                className="mb-3"
                            ),
                            html.Label("Region", className="form-label"),
                            dcc.Dropdown(
                                id="region-filter",
                                options=[
                                    {"label": "🌍 All Regions", "value": "all"},
                                    {"label": "🇺🇸 US East", "value": "us-east-1"},
                                    {"label": "🇺🇸 US Central", "value": "us-central1"},
                                    {"label": "🇺🇸 US Ashburn", "value": "us-ashburn-1"}
                                ],
                                value="all",
                                className="mb-3"
                            ),
                            html.Label("Service Type", className="form-label"),
                            dcc.Dropdown(
                                id="service-filter",
                                options=[
                                    {"label": "📦 All Services", "value": "all"},
                                    {"label": "💻 Compute", "value": "compute"},
                                    {"label": "💾 Storage", "value": "storage"}
                                ],
                                value="all"
                            )
                        ])
                    ], className="mb-4")
                ], width=3),
                
                # Main Chart
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Graph(id="price-comparison-chart", style={"height": "500px"})
                        ])
                    ], className="mb-4")
                ], width=9)
            ]),
            
            # Additional Visualizations
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("📈 Cost Efficiency Analysis", className="card-title"),
                            dcc.Graph(id="efficiency-chart", style={"height": "400px"})
                        ])
                    ], className="mb-4")
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("💵 Storage Pricing", className="card-title"),
                            dcc.Graph(id="storage-chart", style={"height": "400px"})
                        ])
                    ], className="mb-4")
                ], width=6)
            ]),
            
            # Data Table with Export
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.H5("📋 Detailed Pricing Data", className="card-title", style={"display": "inline-block"}),
                                dbc.ButtonGroup([
                                    dbc.Button("📥 Export CSV", id="export-csv-btn", color="success", className="ms-3"),
                                    dbc.Button("📄 Export PDF", id="export-pdf-btn", color="danger", className="ms-2"),
                                ], className="float-end")
                            ]),
                            html.Div(id="data-table"),
                            html.Div(id="export-status", className="mt-3")
                        ])
                    ])
                ])
            ])
        ], fluid=True)
    
    elif active_tab == "recommendations":
        recommendations = get_optimization_recommendations()
        rec_cards = []
        for rec in recommendations:
            rec_cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(f"{rec['icon']} {rec['title']}", className="card-title"),
                            html.P(rec['description'], className="card-text"),
                            dbc.Badge(rec['savings'], color="success", className="mt-2"),
                            html.Hr(),
                            html.Small(f"Type: {rec['type']}", className="text-muted")
                        ])
                    ], className="mb-4")
                ], width=6)
            )
        
        return dbc.Container([
            html.H3("💡 Cost Optimization Recommendations", className="mb-4"),
            dbc.Row([
                dbc.Col([
                    html.Div(id="anomaly-alert", className="mb-4")
                ])
            ]),
            dbc.Row(rec_cards),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("📊 Cost Distribution", className="card-title"),
                            dcc.Graph(id="cost-distribution-chart")
                        ])
                    ])
                ], width=12)
            ])
        ], fluid=True)
    
    elif active_tab == "pricing":
        return dbc.Container([
            html.H3("💵 Pricing Model Comparison", className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Select Instance", className="card-title"),
                            html.Label("Provider", className="form-label"),
                            dcc.Dropdown(
                                id="pricing-provider",
                                options=[
                                    {"label": "AWS", "value": "aws"},
                                    {"label": "GCP", "value": "gcp"},
                                    {"label": "OCI", "value": "oci"}
                                ],
                                value="aws",
                                className="mb-3"
                            ),
                            html.Label("Instance Type", className="form-label"),
                            dcc.Dropdown(id="pricing-instance", className="mb-3"),
                            html.Label("Hours/Month", className="form-label"),
                            dcc.Input(id="pricing-hours", type="number", value=730, min=1, max=744, className="form-control mb-3"),
                            html.Label("Years", className="form-label"),
                            dcc.Input(id="pricing-years", type="number", value=3, min=1, max=10, className="form-control"),
                        ])
                    ])
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Cost Comparison", className="card-title"),
                            html.Div(id="pricing-comparison-results")
                        ])
                    ])
                ], width=8)
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dcc.Graph(id="pricing-model-chart")
                        ])
                    ])
                ])
            ])
        ], fluid=True)
    
    elif active_tab == "finder":
        return dbc.Container([
            html.H3("🔍 Instance Recommender", className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Workload Requirements", className="card-title"),
                            html.Label("vCPU Required", className="form-label"),
                            dcc.Input(id="req-vcpu", type="number", value=2, min=1, max=32, className="form-control mb-3"),
                            html.Label("Memory Required (GB)", className="form-label"),
                            dcc.Input(id="req-memory", type="number", value=8, min=1, max=256, className="form-control mb-3"),
                            dbc.Button("Find Instances", id="find-btn", color="primary", className="w-100"),
                        ])
                    ])
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Recommended Instances", className="card-title"),
                            html.Div(id="recommendations-results")
                        ])
                    ])
                ], width=8)
            ])
        ], fluid=True)
    
    elif active_tab == "projections":
        return dbc.Container([
            html.H3("📊 TCO Projection Calculator", className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Projection Parameters", className="card-title"),
                            html.Label("Hours per month:", className="form-label"),
                            dcc.Input(
                                id="hours-input", 
                                type="number", 
                                value=730, 
                                min=1, 
                                max=744,
                                className="form-control mb-3"
                            ),
                            html.Label("Years:", className="form-label"),
                            dcc.Input(
                                id="years-input", 
                                type="number", 
                                value=5, 
                                min=1, 
                                max=10,
                                className="form-control mb-3"
                            ),
                            dbc.Button(
                                "🚀 Calculate TCO", 
                                id="calculate-btn", 
                                n_clicks=0,
                                color="primary",
                                size="lg",
                                className="w-100"
                            )
                        ])
                    ])
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div(id="tco-results")
                        ])
                    ])
                ], width=8)
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("📈 Cost Timeline", className="card-title"),
                            dcc.Graph(id="cost-timeline-chart")
                        ])
                    ])
                ])
            ])
        ], fluid=True)
    
    return html.Div("Select a tab")


# Callbacks for Overview tab
@app.callback(
    [Output("price-comparison-chart", "figure"),
     Output("efficiency-chart", "figure"),
     Output("storage-chart", "figure"),
     Output("data-table", "children")],
    [Input("provider-filter", "value"),
     Input("region-filter", "value"),
     Input("service-filter", "value")]
)
def update_charts(provider, region, service):
    """Update all charts based on filters."""
    if df.empty:
        empty_fig = {"data": [], "layout": {"title": "No data available"}}
        return empty_fig, empty_fig, empty_fig, html.Div("No data available")
    
    try:
        filtered_df = df.copy()
        
        if provider != "all":
            filtered_df = filtered_df[filtered_df["provider"] == provider]
        if region != "all":
            filtered_df = filtered_df[filtered_df["region"] == region]
        if service != "all":
            if service == "compute":
                filtered_df = filtered_df[filtered_df["price_per_hour"].notna()]
            elif service == "storage":
                filtered_df = filtered_df[filtered_df["price_per_gb_month"].notna()]
        
        compute_df_filtered = filtered_df[filtered_df["price_per_hour"].notna()].copy()
        if not compute_df_filtered.empty:
            compute_df_filtered['cost_per_vcpu'] = compute_df_filtered['price_per_hour'] / compute_df_filtered['vcpu']
            
            fig1 = px.bar(
                compute_df_filtered,
                x="instance_type",
                y="price_per_hour",
                color="provider",
                barmode="group",
                title="💵 Hourly Pricing Comparison",
                labels={"price_per_hour": "Price per Hour ($)", "instance_type": "Instance Type"},
                color_discrete_map={"aws": "#FF9900", "gcp": "#4285F4", "oci": "#F80000"},
                text="price_per_hour"
            )
            fig1.update_traces(texttemplate='$%{text:.4f}', textposition='outside')
            fig1.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial", size=12)
            )
        else:
            fig1 = {"data": [], "layout": {"title": "No compute data matches filters"}}
        
        if not compute_df_filtered.empty:
            fig2 = px.scatter(
                compute_df_filtered,
                x="vcpu",
                y="memory_gb",
                size="price_per_hour",
                color="provider",
                hover_data=["instance_type", "cost_per_vcpu"],
                title="⚡ Cost Efficiency: vCPU vs Memory",
                color_discrete_map={"aws": "#FF9900", "gcp": "#4285F4", "oci": "#F80000"}
            )
            fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        else:
            fig2 = {"data": [], "layout": {"title": "No compute data available"}}
        
        storage_df = filtered_df[filtered_df["price_per_gb_month"].notna()].copy()
        if not storage_df.empty:
            fig3 = px.bar(
                storage_df,
                x="provider",
                y="price_per_gb_month",
                color="provider",
                title="💾 Storage Pricing (per GB/month)",
                color_discrete_map={"aws": "#FF9900", "gcp": "#4285F4", "oci": "#F80000"}
            )
            fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        else:
            fig3 = {"data": [], "layout": {"title": "No storage data matches filters"}}
        
        display_df = filtered_df[["provider", "instance_type", "price_per_hour", "price_per_gb_month", 
                                  "vcpu", "memory_gb"]].copy()
        display_df = display_df.fillna("-")
        
        table = dash_table.DataTable(
            data=display_df.to_dict('records'),
            columns=[
                {"name": "Provider", "id": "provider"},
                {"name": "Instance Type", "id": "instance_type"},
                {"name": "Price/Hour ($)", "id": "price_per_hour", "type": "numeric", "format": {"specifier": ".4f"}},
                {"name": "Price/GB-Month ($)", "id": "price_per_gb_month", "type": "numeric", "format": {"specifier": ".4f"}},
                {"name": "vCPU", "id": "vcpu"},
                {"name": "Memory (GB)", "id": "memory_gb"}
            ],
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#1a73e8', 'color': 'white', 'fontWeight': 'bold'},
            page_size=10,
            sort_action="native"
        )
        
        return fig1, fig2, fig3, table
        
    except Exception as e:
        error_fig = {"data": [], "layout": {"title": f"Error: {str(e)}"}}
        return error_fig, error_fig, error_fig, html.Div(f"Error: {str(e)}", style={"color": "red"})


# Callback for recommendations tab
@app.callback(
    Output("cost-distribution-chart", "figure"),
    [Input("tabs", "active_tab")]
)
def update_cost_distribution(active_tab):
    """Update cost distribution chart."""
    if active_tab != "recommendations" or compute_df.empty:
        return {"data": [], "layout": {"title": "No data"}}
    
    fig = px.pie(
        compute_df,
        values="price_per_hour",
        names="provider",
        title="Cost Distribution by Provider",
        color_discrete_map={"aws": "#FF9900", "gcp": "#4285F4", "oci": "#F80000"}
    )
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    return fig


# Callback for instance finder
@app.callback(
    Output("recommendations-results", "children"),
    [Input("find-btn", "n_clicks")],
    [State("req-vcpu", "value"), State("req-memory", "value")]
)
def find_instances(n_clicks, vcpu, memory):
    """Find recommended instances."""
    if n_clicks is None or n_clicks == 0:
        return html.Div("Enter your requirements and click 'Find Instances'", className="text-muted")
    
    if not vcpu or not memory:
        return dbc.Alert("Please enter both vCPU and memory requirements.", color="warning")
    
    recommendations = get_instance_recommendations(vcpu, memory)
    
    if not recommendations:
        return dbc.Alert("No instances found matching your requirements. Try lowering your requirements.", color="warning")
    
    cards = []
    for i, rec in enumerate(recommendations):
        cards.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"{i+1}. {rec['provider'].upper()} - {rec['instance_type']}", 
                               className="card-title"),
                        html.P(f"💻 {rec['vcpu']} vCPU | 💾 {rec['memory_gb']} GB RAM"),
                        html.H4(f"${rec['price_per_hour']:.4f}/hr", className="text-primary"),
                        html.P(f"Cost/vCPU: ${rec['cost_per_vcpu']:.4f}", className="text-muted"),
                        html.Small(f"Region: {rec['region']}", className="text-muted")
                    ])
                ], color="success" if i == 0 else "light", outline=True if i == 0 else False)
            ], width=4)
        )
    
    return dbc.Row(cards)


# Callback for TCO calculation
@app.callback(
    [Output("tco-results", "children"),
     Output("cost-timeline-chart", "figure")],
    [Input("calculate-btn", "n_clicks")],
    [State("hours-input", "value"), State("years-input", "value")]
)
def calculate_tco(n_clicks, hours, years):
    """Calculate and display TCO results."""
    if n_clicks is None or n_clicks == 0:
        return html.Div("Enter hours and years, then click 'Calculate TCO'", className="text-muted"), {"data": [], "layout": {}}
    
    try:
        hours_val = int(hours) if hours else 730
        years_val = int(years) if years else 5
        
        if hours_val <= 0 or years_val <= 0:
            return dbc.Alert("Please enter valid positive numbers.", color="danger"), {"data": [], "layout": {}}
        
        comparisons = cost_model.compare_providers("2vcpu-8gb", "us-east-1", hours_per_month=hours_val, years=years_val)
        valid_comps = [c for c in comparisons if "error" not in c]
        
        if not valid_comps:
            return dbc.Alert("No comparison data available.", color="warning"), {"data": [], "layout": {}}
        
        tco_df = pd.DataFrame(valid_comps)
        fig_tco = px.bar(
            tco_df,
            x="provider",
            y="total_cost_5yr",
            color="provider",
            title=f"💰 {years_val}-Year TCO Comparison",
            color_discrete_map={"aws": "#FF9900", "gcp": "#4285F4", "oci": "#F80000"},
            text="total_cost_5yr"
        )
        fig_tco.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig_tco.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        
        # Timeline chart
        timeline_data = []
        for comp in valid_comps:
            for year in range(1, years_val + 1):
                timeline_data.append({
                    'Year': year,
                    'Provider': comp['provider'].upper(),
                    'Cumulative Cost': comp['yearly_cost'] * year
                })
        
        timeline_df = pd.DataFrame(timeline_data)
        fig_timeline = px.line(
            timeline_df,
            x='Year',
            y='Cumulative Cost',
            color='Provider',
            title='📈 Cost Projection Timeline',
            color_discrete_map={"AWS": "#FF9900", "GCP": "#4285F4", "OCI": "#F80000"}
        )
        fig_timeline.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        
        cheapest = min(valid_comps, key=lambda x: x['total_cost_5yr'])
        most_expensive = max(valid_comps, key=lambda x: x['total_cost_5yr'])
        savings = ((most_expensive['total_cost_5yr'] - cheapest['total_cost_5yr']) / most_expensive['total_cost_5yr'] * 100)
        
        result_cards = []
        for comp in valid_comps:
            is_best = comp['provider'] == cheapest['provider']
            result_cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(f"{comp['provider'].upper()}{' 🏆' if is_best else ''}", className="card-title"),
                            html.H2(f"${comp['total_cost_5yr']:,.2f}", className="text-primary"),
                            html.P(f"${comp['hourly_price']:.4f}/hr", className="text-muted"),
                            html.P(f"${comp['monthly_cost']:,.2f}/mo", className="text-muted"),
                            html.P(f"${comp['yearly_cost']:,.2f}/yr", className="text-muted"),
                        ])
                    ], color="success" if is_best else "light", outline=True if is_best else False)
                ], width=4)
            )
        
        return html.Div([
            dbc.Row(result_cards, className="mb-4"),
            dbc.Alert([
                html.H4(f"💰 Best Option: {cheapest['provider'].upper()}", className="alert-heading"),
                html.P(f"Save {savings:.1f}% (${most_expensive['total_cost_5yr'] - cheapest['total_cost_5yr']:,.2f}) compared to {most_expensive['provider'].upper()}")
            ], color="success")
        ]), fig_timeline
        
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), {"data": [], "layout": {}}


# Callback for pricing model comparison
@app.callback(
    [Output("pricing-instance", "options"),
     Output("pricing-instance", "value")],
    [Input("pricing-provider", "value")]
)
def update_instance_options(provider):
    """Update instance options based on provider."""
    if df.empty:
        return [], None
    
    provider_df = df[(df['provider'] == provider) & (df['price_per_hour'].notna())]
    options = [{"label": row['instance_type'], "value": row['instance_type']} 
               for _, row in provider_df.iterrows()]
    value = options[0]['value'] if options else None
    return options, value


@app.callback(
    [Output("pricing-comparison-results", "children"),
     Output("pricing-model-chart", "figure")],
    [Input("pricing-provider", "value"),
     Input("pricing-instance", "value"),
     Input("pricing-hours", "value"),
     Input("pricing-years", "value")]
)
def update_pricing_comparison(provider, instance, hours, years):
    """Compare pricing models."""
    if not provider or not instance:
        return html.Div("Select provider and instance"), {"data": [], "layout": {}}
    
    try:
        region_map = {"aws": "us-east-1", "gcp": "us-central1", "oci": "us-ashburn-1"}
        region = region_map.get(provider, "us-east-1")
        
        # Calculate costs for different pricing models
        on_demand = cost_model.calculate_tco(provider, instance, region, hours or 730, years or 3, False, False)
        reserved = cost_model.calculate_tco(provider, instance, region, hours or 730, years or 3, True, False)
        spot = cost_model.calculate_tco(provider, instance, region, hours or 730, years or 3, False, True) if provider != "oci" else None
        
        comparison_data = [
            {"Model": "On-Demand", "Cost": on_demand.get('total_cost_5yr', 0), "Savings": "0%"},
            {"Model": "Reserved (1-3yr)", "Cost": reserved.get('total_cost_5yr', 0), "Savings": f"{((on_demand.get('total_cost_5yr', 0) - reserved.get('total_cost_5yr', 0)) / on_demand.get('total_cost_5yr', 1) * 100):.1f}%"}
        ]
        
        if spot:
            comparison_data.append({
                "Model": "Spot Instances",
                "Cost": spot.get('total_cost_5yr', 0),
                "Savings": f"{((on_demand.get('total_cost_5yr', 0) - spot.get('total_cost_5yr', 0)) / on_demand.get('total_cost_5yr', 1) * 100):.1f}%"
            })
        
        comp_df = pd.DataFrame(comparison_data)
        
        fig = px.bar(
            comp_df,
            x="Model",
            y="Cost",
            text="Savings",
            title="Pricing Model Comparison",
            color="Cost",
            color_continuous_scale="Greens_r"
        )
        fig.update_traces(texttemplate='Save %{text}', textposition='outside')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        
        cards = []
        for _, row in comp_df.iterrows():
            cards.append(
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5(row['Model'], className="card-title"),
                            html.H3(f"${row['Cost']:,.2f}", className="text-primary"),
                            html.P(f"Save {row['Savings']}", className="text-success")
                        ])
                    ])
                ], width=4)
            )
        
        return dbc.Row(cards), fig
        
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger"), {"data": [], "layout": {}}


# Export callbacks
@app.callback(
    Output("export-status", "children"),
    [Input("export-csv-btn", "n_clicks"),
     Input("export-pdf-btn", "n_clicks")],
    [State("provider-filter", "value"),
     State("region-filter", "value"),
     State("service-filter", "value")]
)
def handle_exports(csv_clicks, pdf_clicks, provider, region, service):
    """Handle CSV and PDF exports."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        # Filter data
        filtered_df = df.copy()
        if provider != "all":
            filtered_df = filtered_df[filtered_df["provider"] == provider]
        if region != "all":
            filtered_df = filtered_df[filtered_df["region"] == region]
        if service != "all":
            if service == "compute":
                filtered_df = filtered_df[filtered_df["price_per_hour"].notna()]
            elif service == "storage":
                filtered_df = filtered_df[filtered_df["price_per_gb_month"].notna()]
        
        if button_id == "export-csv-btn" and csv_clicks:
            csv_data = export_to_csv(filtered_df)
            filename = f"cloud_cost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return dbc.Alert([
                html.Strong("CSV Export Ready!"), 
                html.Br(),
                html.A("Download CSV", href=f"data:text/csv;base64,{base64.b64encode(csv_data.encode()).decode()}", 
                      download=filename, className="btn btn-success btn-sm mt-2")
            ], color="success")
        
        elif button_id == "export-pdf-btn" and pdf_clicks:
            # Get TCO comparisons for PDF
            comparisons = cost_model.compare_providers("2vcpu-8gb", "us-east-1", hours_per_month=730, years=5)
            valid_comps = [c for c in comparisons if "error" not in c]
            
            pdf_result = generate_pdf_report(filtered_df.to_dict('records'), valid_comps)
            if isinstance(pdf_result, str) and "requires" in pdf_result:
                return dbc.Alert(pdf_result, color="warning")
            
            filename = f"cloud_cost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_base64 = base64.b64encode(pdf_result.getvalue()).decode()
            return dbc.Alert([
                html.Strong("PDF Export Ready!"),
                html.Br(),
                html.A("Download PDF", href=f"data:application/pdf;base64,{pdf_base64}",
                      download=filename, className="btn btn-danger btn-sm mt-2")
            ], color="success")
        
    except Exception as e:
        return dbc.Alert(f"Export error: {str(e)}", color="danger")
    
    return ""


# Anomaly detection callback
@app.callback(
    Output("anomaly-alert", "children"),
    [Input("tabs", "active_tab")]
)
def update_anomalies(active_tab):
    """Update anomaly detection."""
    if active_tab != "recommendations":
        return ""
    
    anomalies = detect_cost_anomalies(pricing_data)
    if not anomalies:
        return dbc.Alert("✅ No cost anomalies detected", color="success")
    
    anomaly_list = []
    for anom in anomalies[:5]:  # Show top 5
        color = "danger" if anom['status'] == 'high' else "warning"
        anomaly_list.append(
            html.Li([
                f"{anom['provider'].upper()} {anom['instance_type']}: "
                f"${anom['cost_per_vcpu']:.4f}/vCPU ({anom['deviation']} deviation)"
            ])
        )
    
    return dbc.Alert([
        html.H5("⚠️ Cost Anomalies Detected", className="alert-heading"),
        html.Ul(anomaly_list)
    ], color="warning")


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=8050)
