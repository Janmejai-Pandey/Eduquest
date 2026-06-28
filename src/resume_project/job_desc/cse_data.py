"""
cse_data.py
Computer Science Engineering job role profiles.
"""

job_skill_profiles = {
    "Software Developer": {
        "skills": [
            "python", "java", "c++", "c#", "javascript", "typescript", "go",
            "data structures", "algorithms", "oop", "design patterns",
            "system design", "rest api", "graphql", "git", "github",
            "docker", "kubernetes", "aws", "azure", "linux", "bash",
            "sql", "mongodb", "postgresql", "mysql", "redis",
            "unit testing", "integration testing", "tdd", "ci/cd",
            "agile", "scrum", "jira", "debugging", "code review"
        ],
        "weights": {
            "python": 4, "java": 4, "c++": 4, "data structures": 5,
            "algorithms": 5, "oop": 4, "system design": 5, "git": 4,
            "rest api": 4, "sql": 3, "docker": 3, "unit testing": 3,
            "agile": 2, "debugging": 4
        }
    },
    "Backend Developer": {
        "skills": [
            "python", "java", "node.js", "express", "django", "flask",
            "spring boot", "go", "rest api", "graphql", "grpc",
            "microservices", "sql", "postgresql", "mysql", "mongodb",
            "redis", "kafka", "rabbitmq", "docker", "kubernetes",
            "aws", "azure", "gcp", "linux", "nginx", "authentication",
            "jwt", "oauth", "caching", "load balancing", "git", "ci/cd",
            "unit testing", "agile"
        ],
        "weights": {
            "python": 4, "java": 4, "node.js": 4, "rest api": 5,
            "microservices": 4, "sql": 4, "postgresql": 4, "docker": 4,
            "kubernetes": 3, "aws": 3, "git": 3, "authentication": 3
        }
    },
    "Frontend Developer": {
        "skills": [
            "html", "css", "javascript", "typescript", "react", "angular",
            "vue", "next.js", "redux", "tailwind", "bootstrap", "sass",
            "webpack", "vite", "responsive design", "accessibility",
            "web performance", "jest", "cypress", "storybook", "figma",
            "ui/ux", "rest api", "graphql", "git", "node.js"
        ],
        "weights": {
            "javascript": 5, "typescript": 4, "react": 5, "html": 3,
            "css": 3, "responsive design": 4, "tailwind": 3, "jest": 3,
            "figma": 2, "rest api": 3, "git": 3
        }
    },
    "Full Stack Developer": {
        "skills": [
            "html", "css", "javascript", "typescript", "react", "angular",
            "vue", "node.js", "express", "django", "flask", "rest api",
            "graphql", "docker", "kubernetes", "aws", "sql", "postgresql",
            "mongodb", "redis", "git", "ci/cd", "unit testing", "agile",
            "ui/ux", "figma"
        ],
        "weights": {
            "javascript": 5, "typescript": 4, "react": 4, "node.js": 4,
            "rest api": 4, "docker": 3, "aws": 3, "sql": 3, "git": 3,
            "mongodb": 3
        }
    },
    "DevOps Engineer": {
        "skills": [
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "ansible", "jenkins", "github actions", "gitlab ci", "ci/cd",
            "linux", "bash", "python", "go", "monitoring", "prometheus",
            "grafana", "elk stack", "logging", "infrastructure as code",
            "cloudformation", "serverless", "lambda", "s3", "ec2",
            "networking", "security", "git", "agile"
        ],
        "weights": {
            "aws": 5, "docker": 5, "kubernetes": 5, "terraform": 4,
            "ci/cd": 5, "linux": 4, "bash": 3, "monitoring": 4, "git": 3
        }
    },
    "Cloud Engineer": {
        "skills": [
            "aws", "azure", "gcp", "cloudformation", "terraform",
            "docker", "kubernetes", "serverless", "lambda", "s3", "ec2",
            "rds", "vpc", "iam", "cloudfront", "route53", "monitoring",
            "cloudwatch", "prometheus", "ci/cd", "jenkins", "github actions",
            "git", "linux", "bash", "python", "networking", "ssl/tls"
        ],
        "weights": {
            "aws": 5, "azure": 4, "gcp": 4, "terraform": 5, "docker": 4,
            "kubernetes": 4, "serverless": 4, "lambda": 4, "ci/cd": 3
        }
    },
    "Database Administrator": {
        "skills": [
            "sql", "postgresql", "mysql", "oracle", "mongodb", "redis",
            "cassandra", "dynamodb", "database design", "normalization",
            "indexing", "query optimization", "stored procedures",
            "triggers", "backup", "recovery", "replication", "sharding",
            "performance tuning", "etl", "linux", "bash", "python",
            "monitoring", "security", "ssl/tls", "git", "aws", "azure"
        ],
        "weights": {
            "sql": 5, "postgresql": 4, "mysql": 4, "database design": 5,
            "indexing": 4, "query optimization": 4, "backup": 4, "git": 2
        }
    },
    "Cybersecurity Analyst": {
        "skills": [
            "networking", "tcp/ip", "firewalls", "ids/ips", "vpn",
            "wireshark", "nmap", "metasploit", "burp suite", "owasp",
            "penetration testing", "ethical hacking", "cryptography",
            "ssl/tls", "siems", "splunk", "linux", "bash", "python",
            "windows server", "active directory", "aws security",
            "compliance", "risk assessment", "incident response",
            "forensics", "git"
        ],
        "weights": {
            "networking": 5, "penetration testing": 5, "owasp": 4,
            "cryptography": 4, "linux": 3, "python": 3,
            "incident response": 4, "splunk": 3
        }
    }
}