| Component | Monthly Estimate | Key Assumptions | One Optimization |
|-----------|-----------------|----------------|-----------------|
| SageMaker Studio | $11.25 | $0.05/hr × 56hours/week actually used | Shutting down Studio when idle reduces usage from 56 hrs/week to 20 hrs/week, saving ~$7.20/month |
| S3 storage | $2.30 | 100 GB at $0.023/GB | |
| Internet Gateway | $0.01 | 1 GB outbound transfer at $0.01/GB | |
| DynamoDB (state lock) | $0.00 | On-demand, near-zero reads | |
| S3 state bucket | $0.00 | MBs of storage | |
| **Total** | **$13.56** | | |