# Shopping Dataset Analysis

Exploratory data analysis, data cleaning, feature engineering, and insight
generation on a 1,000-row e-commerce (fashion/lifestyle) product dataset.

## Objective

Perform EDA, clean the raw data, engineer new features, and derive
business-relevant insights from a combined product dataset scraped from an
online fashion marketplace.

## Project Structure


shopping-analysis/
├── notebook/
│   └── analysis.ipynb
|   |___combined_dataset
└── README.md


## Dataset

1,000 product listings across 97 categories (tops, dresses, shirts, jeans,
sports shoes, etc.), with 24 raw columns covering pricing, ratings, seller
information, and product metadata.

## What the Notebook Does

1. **Load & Explore** — shape, dtypes, summary statistics, missing-value
   profiling
2. **Clean** — handles missing values (median for numeric columns,
   "Not Available" for categorical columns), removes duplicates, converts
   the text-formatted `final_price` column to numeric
3. **Feature Engineering**
   - `discount_amount` — actual rupee discount (`initial_price - final_price`)
   - `popularity_score` — a weighted (Bayesian-style) score combining
     `rating` and `ratings_count`, so products with few reviews aren't
     overrated
   - `num_size_options` — number of size/variant options, parsed from the
     `sizes` field
   - `department` — a clean top-level grouping (Women / Men / Girls / Boys /
     Unisex), parsed from the `breadcrumbs` field
4. **Analysis** — univariate (rating & price distributions), bivariate
   (price vs. rating, discount vs. rating, correlation heatmap), and
   category-level analysis (top categories, department breakdown, average
   rating/price/discount per category)
5. **Visualization** — histograms, bar charts, boxplots, scatter plots, and
   a correlation heatmap
6. **Insights** — written findings with business implications

## Key Findings

- **36.3% of products** have `final_price` exactly equal to `initial_price`
  despite a nonzero `discount` percentage being listed — the advertised
  discount and the actual price frequently disagree.
- **Raw `rating` is a misleading popularity signal** — products with a
  perfect 5.0 rating from only a handful of reviews can outrank products
  with thousands of reviews. The weighted `popularity_score` corrects for
  this.
- **114 products have `rating = 0`**, always paired with `ratings_count = 0`
  — these are unreviewed listings, not genuinely zero-star products.
- **`earrings`** has the lowest average rating (2.86) *and* the highest
  average discount (68.6%) among top categories — heavy discounting is not
  improving customer satisfaction there.
- The catalog is **55% Women's department**, with `tops`, `dresses`, and
  `shirts` alone making up nearly a third of all listings.

## How to Run

```bash
pip install pandas numpy matplotlib seaborn
jupyter notebook notebook/analysis.ipynb
```

Run all cells top to bottom. Outputs (`cleaned_product_dataset.csv` and
`analyzed_product_dataset.csv`) will be written alongside the notebook.

## Requirements

- Python 3.x
- pandas
- numpy
- matplotlib
- seaborn
