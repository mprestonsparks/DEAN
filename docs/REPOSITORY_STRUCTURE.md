# DEAN Repository Structure

## Root Directory
```
DEAN/
├── docker-compose.prod.yml      # Production Docker composition
├── docker-compose.windows.yml   # Windows-specific overrides
├── .env.production.template     # Environment template
├── README.md                    # Quick start guide
└── LICENSE.md                   # MIT License
```

## Service Directories
```
services/
├── orchestration/              # Core orchestration service
│   ├── Dockerfile.prod        # Production container
│   ├── main.py               # FastAPI application
│   └── requirements.txt      # Python dependencies
├── evolution/                 # Evolution engine
├── dashboard/                # Web UI
└── cli/                     # Command-line tools
```

## Configuration
```
configs/
├── nginx/                   # Reverse proxy configuration
├── airflow/                # DAG definitions
└── prometheus/             # Monitoring configuration
```

## Infrastructure
```
infra/
├── database/               # Schema definitions
├── monitoring/             # Prometheus and Grafana
└── scripts/               # Operational scripts
```

## Documentation
```
docs/
├── deployment/            # Deployment guides
├── api/                  # API reference
├── configuration/        # Configuration guide
└── operations/          # Operations manual
```
EOF < /dev/null