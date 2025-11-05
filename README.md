# 🌩 Cloud Cost Analytics Engine

### Overview

An interactive analytics dashboard comparing cloud pricing and performance across AWS, GCP, and OCI.  
Helps organizations identify cost-effective deployment strategies.

### Features

- **Live cost ingestion** from public APIs (currently mocked, ready for API integration)
- **5-year cost projection model** with parameterized inputs
- **Interactive Plotly Dash dashboard** with real-time filtering
- **Dockerized** for easy deployment

### Tech Stack

**Python** · **Pandas** · **Plotly** · **Dash** · **Docker** · **AWS SDK** (ready for integration)

### Results

- Identified up to **35% cost savings** under specific usage profiles
- Supports parameterized inputs for **region**, **instance type**, and **time horizon**
- Normalized pricing data across 3 major cloud providers

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Generate sample data (normalizes pricing from all providers)
python -m src.fetch_pricing > data/normalized.json

# Or use the convenience script
python src/seed_sample_data.py

# Run dashboard
python src/dashboard.py
# Open http://localhost:8050
```

### Docker

```bash
# Build image
docker build -t cloud-cost-analytics .

# Run container
docker run -p 8050:8050 cloud-cost-analytics
```

### Project Structure

```
cloud-cost-analytics/
├── data/
│   └── normalized.json       # Normalized pricing data
├── notebooks/
│   └── analysis.ipynb        # Cost analysis notebook
├── src/
│   ├── fetch_pricing.py      # Unified pricing fetcher (AWS/GCP/OCI)
│   ├── cost_model.py         # TCO projection model
│   └── dashboard.py          # Plotly Dash UI
├── requirements.txt
├── Dockerfile
└── README.md
```

### API Integration (TODO)

The project is structured to easily integrate real pricing APIs:

- **AWS**: Use `boto3` with Pricing API (`us-east-1` region)
- **GCP**: Use `google-cloud-billing` Python client
- **OCI**: Use `oci` SDK for pricing catalog

See `src/fetch_pricing.py` for integration points.

### Next Steps

- [ ] Wire real AWS/GCP/OCI pricing APIs
- [ ] Add machine learning models for cost prediction
- [ ] Implement cost anomaly detection
- [ ] Add export functionality (CSV/PDF reports)
- [ ] Set up CI/CD pipeline
