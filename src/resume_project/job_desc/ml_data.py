"""
ml_data.py
Machine Learning specialist job role profiles.
"""

job_skill_profiles = {
    "Machine Learning Engineer": {
        "skills": [
            "python", "scikit-learn", "tensorflow", "pytorch", "keras",
            "pandas", "numpy", "matplotlib", "seaborn", "jupyter",
            "feature engineering", "model selection", "hyperparameter tuning",
            "cross validation", "regression", "classification", "clustering",
            "ensemble methods", "xgboost", "lightgbm", "catboost",
            "deep learning", "neural networks", "model deployment",
            "flask", "fastapi", "docker", "kubernetes", "aws sagemaker",
            "mlflow", "kubeflow", "airflow", "sql", "spark", "git",
            "linux", "statistics", "probability", "agile"
        ],
        "weights": {
            "python": 5, "scikit-learn": 5, "tensorflow": 4, "pytorch": 4,
            "feature engineering": 5, "model selection": 4,
            "hyperparameter tuning": 4, "xgboost": 4, "deep learning": 4,
            "model deployment": 5, "docker": 3, "statistics": 4
        }
    },
    "Data Scientist": {
        "skills": [
            "python", "r", "sql", "pandas", "numpy", "scikit-learn",
            "tensorflow", "pytorch", "matplotlib", "seaborn", "plotly",
            "jupyter", "statistics", "probability", "hypothesis testing",
            "a/b testing", "regression", "classification", "clustering",
            "time series", "forecasting", "feature engineering",
            "data cleaning", "exploratory data analysis", "tableau",
            "power bi", "excel", "big data", "spark", "hadoop",
            "communication", "storytelling", "business acumen", "git"
        ],
        "weights": {
            "python": 5, "sql": 5, "statistics": 5, "pandas": 5,
            "scikit-learn": 4, "exploratory data analysis": 4,
            "feature engineering": 4, "communication": 4,
            "storytelling": 4, "tableau": 3
        }
    },
    "Data Analyst": {
        "skills": [
            "sql", "excel", "python", "pandas", "numpy", "tableau",
            "power bi", "looker", "data visualization", "data cleaning",
            "exploratory data analysis", "statistics", "hypothesis testing",
            "a/b testing", "reporting", "dashboards", "kpis", "metrics",
            "google analytics", "google sheets", "vba", "r", "etl",
            "data warehousing", "snowflake", "bigquery", "communication",
            "storytelling", "business acumen"
        ],
        "weights": {
            "sql": 5, "excel": 5, "tableau": 4, "power bi": 4,
            "data visualization": 5, "data cleaning": 4,
            "exploratory data analysis": 4, "communication": 4,
            "python": 3
        }
    },
    "Data Engineer": {
        "skills": [
            "python", "sql", "spark", "hadoop", "hive", "kafka",
            "airflow", "dbt", "aws glue", "databricks", "snowflake",
            "bigquery", "redshift", "postgresql", "mongodb", "etl",
            "elt", "data pipelines", "data warehousing", "data modeling",
            "dimensional modeling", "star schema", "docker", "kubernetes",
            "aws", "gcp", "azure", "scala", "java", "git", "agile"
        ],
        "weights": {
            "python": 5, "sql": 5, "spark": 5, "kafka": 4, "airflow": 5,
            "etl": 5, "data warehousing": 4, "snowflake": 4, "aws": 3,
            "docker": 3
        }
    },
    "MLOps Engineer": {
        "skills": [
            "python", "docker", "kubernetes", "aws", "gcp", "azure",
            "mlflow", "kubeflow", "airflow", "dvc", "ci/cd", "jenkins",
            "github actions", "terraform", "ansible", "monitoring",
            "prometheus", "grafana", "model serving", "tensorflow serving",
            "torchserve", "triton", "model versioning", "feature store",
            "feast", "experiment tracking", "weights and biases",
            "linux", "bash", "git", "tensorflow", "pytorch",
            "scikit-learn", "agile"
        ],
        "weights": {
            "python": 5, "docker": 5, "kubernetes": 5, "mlflow": 5,
            "ci/cd": 5, "model serving": 5, "aws": 4, "monitoring": 4,
            "kubeflow": 4
        }
    },
    "Business Intelligence Analyst": {
        "skills": [
            "sql", "tableau", "power bi", "looker", "qlik", "excel",
            "vba", "dax", "data modeling", "data warehousing", "etl",
            "snowflake", "bigquery", "redshift", "ssrs", "ssis", "ssas",
            "google analytics", "kpis", "metrics", "reporting",
            "dashboards", "storytelling", "communication",
            "business acumen", "python", "r"
        ],
        "weights": {
            "sql": 5, "tableau": 5, "power bi": 5, "excel": 4,
            "dax": 4, "data modeling": 4, "etl": 4, "dashboards": 5,
            "communication": 4
        }
    }
}