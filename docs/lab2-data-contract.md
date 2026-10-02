## Data Contract: processed/customers

### Producer
Team / process: Glue ETL job `northstar-dev-transform`

### Consumers
- Feature engineering job `northstar-dev-feature-engineer`
- (Future) Direct model training in Lab 3

### Grain
One row per transaction. A customer appears on many rows.

### Schema
| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `transaction_id` | string | No | Natural transaction identifier; unique after deduplication. |
| `customer_id` | string | No | Customer identifier; whitespace is trimmed before output. |
| `purchase_date` | date | No | Purchase date, normalized from `yyyy-MM-dd` or `MM/dd/yyyy` input. |
| `order_value` | double | No | Gross order value in USD; missing values are median-imputed. |
| `num_items` | integer | No | Number of line items in the order; missing values are median-imputed and rounded. |
| `payment_method` | string | No | Payment method; missing values are represented as `unknown`. |
| `channel` | string | No | Sales channel: `store` or `online`; missing values are represented as `unknown`. |
| `store_id` | string | No | Store identifier or `ONLINE`; missing values are represented as `unknown`. |
| `product_category` | string | No | Primary product category; missing values are represented as `unknown`. |

### Quality Guarantees
- `customer_id` is never null
- No duplicate `transaction_id` rows (a `customer_id` repeating across rows is expected, not a defect)
- `customer_id` is trimmed and is not an empty string
- `purchase_date` is non-null and stored as a Parquet `date`, parsed from either `yyyy-MM-dd` or `MM/dd/yyyy` input
- `order_value` is non-null and satisfies `0 <= order_value < 10000` USD
- `num_items` is non-null, an integer, and satisfies `1 <= num_items <= 9`
- `payment_method`, `channel`, `store_id`, and `product_category` are non-null; missing source values are imputed as `unknown`

### SLA
- Data is available in `processed/customers/` within 2 hours of landing in `raw/customers/`

### Versioning
- Schema changes require a new S3 prefix (e.g., `processed/customers/v2/`)
- Breaking changes require consumer notification 5 business days in advance
