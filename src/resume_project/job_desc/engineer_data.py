# dictionary holding all engineering profiles and skill weights
job_skill_profiles = {
    "Software Engineer": {
        "skills": [
            "java", "python", "c++", "c#", "javascript", "typescript", "go", "rust",
            "data structures", "algorithms", "oop", "design patterns", "system design",
            "microservices", "rest api", "graphql", "grpc", "docker", "kubernetes",
            "aws", "azure", "gcp", "linux", "git", "ci/cd", "jenkins", "github actions",
            "sql", "nosql", "mongodb", "postgresql", "redis", "kafka", "rabbitmq",
            "unit testing", "integration testing", "tdd", "agile", "scrum", "jira"
        ],
        "weights": {
            "java": 4, "python": 4, "c++": 3, "data structures": 5, "algorithms": 5,
            "oop": 4, "system design": 5, "microservices": 4, "rest api": 4,
            "docker": 4, "kubernetes": 3, "aws": 3, "git": 3, "sql": 3,
            "unit testing": 3, "agile": 2
        }
    },
    "Frontend Engineer": {
        "skills": [
            "html", "css", "javascript", "typescript", "react", "angular", "vue",
            "svelte", "next.js", "redux", "zustand", "tailwind", "bootstrap",
            "sass", "less", "webpack", "vite", "babel", "responsive design",
            "accessibility", "web performance", "pwa", "jest", "cypress", "storybook",
            "figma", "ui/ux", "git", "rest api", "graphql", "node.js"
        ],
        "weights": {
            "javascript": 5, "typescript": 4, "react": 5, "html": 3, "css": 3,
            "responsive design": 4, "webpack": 2, "jest": 3, "figma": 2,
            "rest api": 3
        }
    },
    "Backend Engineer": {
        "skills": [
            "python", "java", "c#", "go", "node.js", "express", "django", "flask",
            "spring boot", "asp.net", "rest api", "graphql", "grpc", "microservices",
            "docker", "kubernetes", "aws", "azure", "gcp", "linux", "nginx",
            "sql", "postgresql", "mysql", "mongodb", "redis", "kafka", "rabbitmq",
            "authentication", "jwt", "oauth", "caching", "load balancing", "ci/cd",
            "git", "unit testing", "integration testing", "agile"
        ],
        "weights": {
            "python": 4, "java": 4, "node.js": 4, "rest api": 5, "docker": 4,
            "kubernetes": 3, "aws": 3, "sql": 4, "postgresql": 3, "microservices": 4,
            "unit testing": 3
        }
    },
    "DevOps Engineer": {
        "skills": [
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
            "jenkins", "github actions", "gitlab ci", "ci/cd", "linux", "bash",
            "python", "go", "monitoring", "prometheus", "grafana", "elk stack",
            "logging", "infrastructure as code", "cloudformation", "serverless",
            "lambda", "s3", "ec2", "rds", "vpc", "networking", "security", "ssl/tls",
            "git", "agile", "scrum"
        ],
        "weights": {
            "aws": 5, "docker": 5, "kubernetes": 5, "terraform": 4, "ci/cd": 5,
            "linux": 4, "bash": 3, "monitoring": 4, "prometheus": 3, "git": 3
        }
    },
    "Data Engineer": {
        "skills": [
            "python", "sql", "spark", "hadoop", "hive", "pig", "kafka", "flume",
            "airflow", "luigi", "aws glue", "databricks", "snowflake", "bigquery",
            "redshift", "postgresql", "mongodb", "etl", "elt", "data pipelines",
            "data warehousing", "data modeling", "dimensional modeling", "star schema",
            "snowflake schema", "docker", "kubernetes", "aws", "gcp", "azure",
            "git", "agile", "scrum"
        ],
        "weights": {
            "python": 5, "sql": 5, "spark": 5, "hadoop": 4, "kafka": 4,
            "airflow": 4, "etl": 5, "data warehousing": 4, "aws": 3, "docker": 3
        }
    },
    "Machine Learning Engineer": {
        "skills": [
            "python", "tensorflow", "pytorch", "keras", "scikit-learn", "pandas",
            "numpy", "matplotlib", "seaborn", "jupyter", "sql", "spark", "hadoop",
            "mlflow", "feature engineering", "model deployment", "flask", "fastapi",
            "docker", "kubernetes", "aws sagemaker", "gcp vertex ai", "azure ml",
            "deep learning", "cnn", "rnn", "transformers", "nlp", "computer vision",
            "reinforcement learning", "statistics", "probability", "git", "agile"
        ],
        "weights": {
            "python": 5, "tensorflow": 5, "pytorch": 5, "scikit-learn": 4,
            "deep learning": 5, "nlp": 4, "computer vision": 4, "docker": 3,
            "aws sagemaker": 3, "statistics": 4
        }
    },
    "Cloud Engineer": {
        "skills": [
            "aws", "azure", "gcp", "cloudformation", "terraform", "ansible",
            "docker", "kubernetes", "serverless", "lambda", "s3", "ec2", "rds",
            "vpc", "iam", "security groups", "cloudfront", "route53", "elb",
            "autoscaling", "monitoring", "cloudwatch", "prometheus", "grafana",
            "logging", "elk stack", "ci/cd", "jenkins", "github actions", "git",
            "linux", "bash", "python", "networking", "ssl/tls"
        ],
        "weights": {
            "aws": 5, "azure": 4, "gcp": 4, "terraform": 5, "docker": 4,
            "kubernetes": 4, "serverless": 4, "lambda": 4, "cloudformation": 4,
            "monitoring": 3, "ci/cd": 3
        }
    },
    "Embedded Systems Engineer": {
        "skills": [
            "c", "c++", "rust", "python", "assembly", "rtos", "bare metal",
            "microcontrollers", "arm", "avr", "pic", "fpga", "verilog", "vhdl",
            "iot", "sensors", "actuators", "communication protocols", "uart", "spi",
            "i2c", "can", "modbus", "ethernet", "wifi", "bluetooth", "zigbee",
            "pcb design", "altium", "kicad", "oscilloscope", "logic analyzer",
            "git", "agile", "unit testing", "integration testing"
        ],
        "weights": {
            "c": 5, "c++": 4, "rtos": 5, "microcontrollers": 5, "arm": 4,
            "communication protocols": 4, "uart": 3, "spi": 3, "i2c": 3,
            "pcb design": 3, "git": 2
        }
    },
    "Cybersecurity Engineer": {
        "skills": [
            "networking", "tcp/ip", "dns", "http/https", "firewalls", "ids/ips",
            "vpn", "wireshark", "nmap", "metasploit", "burp suite", "owasp",
            "penetration testing", "ethical hacking", "cryptography", "ssl/tls",
            "pki", "siems", "splunk", "elastic", "linux", "bash", "python",
            "powershell", "windows server", "active directory", "aws security",
            "azure security", "gcp security", "compliance", "gdpr", "iso 27001",
            "nist", "risk assessment", "incident response", "forensics", "git"
        ],
        "weights": {
            "networking": 5, "penetration testing": 5, "owasp": 4, "cryptography": 4,
            "linux": 3, "python": 3, "aws security": 3, "incident response": 4,
            "splunk": 3, "git": 2
        }
    },
    "Site Reliability Engineer": {
        "skills": [
            "linux", "bash", "python", "go", "docker", "kubernetes", "terraform",
            "ansible", "aws", "azure", "gcp", "ci/cd", "jenkins", "github actions",
            "monitoring", "prometheus", "grafana", "logging", "elk stack", "splunk",
            "sre principles", "error budgets", "slis", "slos", "slas", "chaos engineering",
            "load testing", "locust", "jmeter", "incident management", "postmortems",
            "capacity planning", "scaling", "high availability", "disaster recovery",
            "git", "agile", "scrum"
        ],
        "weights": {
            "linux": 4, "docker": 5, "kubernetes": 5, "terraform": 4, "aws": 4,
            "monitoring": 5, "prometheus": 4, "sre principles": 5, "incident management": 4,
            "git": 3
        }
    },
    "Full-Stack Engineer": {
        "skills": [
            "html", "css", "javascript", "typescript", "react", "angular", "vue",
            "node.js", "express", "django", "flask", "spring boot", "rest api",
            "graphql", "docker", "kubernetes", "aws", "azure", "gcp", "sql",
            "postgresql", "mongodb", "redis", "git", "ci/cd", "unit testing",
            "integration testing", "agile", "scrum", "ui/ux", "figma"
        ],
        "weights": {
            "javascript": 5, "typescript": 4, "react": 4, "node.js": 4,
            "rest api": 4, "docker": 3, "aws": 3, "sql": 3, "git": 3
        }
    },
    "Robotics Engineer": {
        "skills": [
            "c++", "python", "ros", "ros2", "matlab", "simulink", "control systems",
            "pid control", "kinematics", "dynamics", "sensors", "lidar", "camera",
            "computer vision", "opencv", "tensorflow", "pytorch", "embedded systems",
            "microcontrollers", "arduino", "raspberry pi", "fpga", "pcb design",
            "mechanical design", "cad", "solidworks", "autocad", "git", "agile"
        ],
        "weights": {
            "c++": 5, "python": 4, "ros": 5, "control systems": 5, "sensors": 4,
            "computer vision": 4, "embedded systems": 4, "git": 3
        }
    }
}

# Helper function to easily grab a specific profile
def get_job_skill_profile(job_role):
    return job_skill_profiles.get(job_role, {"skills": [], "weights": {}})


ml_profile = get_job_skill_profile("Machine Learning Engineer")
print("Successfully loaded profile!")
print("Sample Skills:", ml_profile["skills"][:5]) 