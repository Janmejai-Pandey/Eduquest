"""
it_data.py
Information Technology job role profiles.
"""

job_skill_profiles = {
    "IT Support Engineer": {
        "skills": [
            "windows", "linux", "macos", "active directory", "office 365",
            "networking", "tcp/ip", "dns", "dhcp", "vpn", "troubleshooting",
            "hardware", "software installation", "remote desktop",
            "ticketing systems", "servicenow", "jira", "powershell",
            "bash", "itil", "customer service", "documentation",
            "antivirus", "backup", "recovery"
        ],
        "weights": {
            "windows": 5, "active directory": 4, "networking": 4,
            "troubleshooting": 5, "office 365": 4, "ticketing systems": 3,
            "itil": 3, "customer service": 4, "powershell": 3
        }
    },
    "Network Engineer": {
        "skills": [
            "tcp/ip", "routing", "switching", "cisco", "juniper",
            "firewalls", "vpn", "vlan", "subnetting", "ospf", "bgp",
            "mpls", "wan", "lan", "sd-wan", "wireless", "wifi", "dns",
            "dhcp", "load balancing", "f5", "monitoring", "wireshark",
            "linux", "bash", "python", "automation", "ansible", "git"
        ],
        "weights": {
            "tcp/ip": 5, "routing": 5, "switching": 5, "cisco": 4,
            "firewalls": 4, "vlan": 4, "subnetting": 4, "monitoring": 3
        }
    },
    "System Administrator": {
        "skills": [
            "linux", "windows server", "active directory", "powershell",
            "bash", "python", "vmware", "hyper-v", "docker", "kubernetes",
            "aws", "azure", "monitoring", "nagios", "zabbix", "prometheus",
            "backup", "recovery", "security patching", "scripting",
            "ansible", "puppet", "chef", "git", "networking", "dns",
            "dhcp", "ldap"
        ],
        "weights": {
            "linux": 5, "windows server": 4, "active directory": 4,
            "powershell": 4, "bash": 4, "monitoring": 4, "backup": 4,
            "scripting": 4, "git": 3
        }
    },
    "Database Administrator (IT)": {
        "skills": [
            "sql", "mysql", "postgresql", "oracle", "sql server",
            "mongodb", "backup", "recovery", "replication", "indexing",
            "query optimization", "performance tuning", "etl",
            "data warehousing", "linux", "windows server", "powershell",
            "bash", "python", "monitoring", "security", "git"
        ],
        "weights": {
            "sql": 5, "mysql": 4, "postgresql": 4, "backup": 5,
            "indexing": 4, "query optimization": 4, "performance tuning": 4
        }
    },
    "Cloud Support Engineer": {
        "skills": [
            "aws", "azure", "gcp", "linux", "windows server", "docker",
            "kubernetes", "terraform", "cloudformation", "monitoring",
            "cloudwatch", "azure monitor", "stackdriver", "troubleshooting",
            "networking", "vpc", "ec2", "s3", "iam", "rds", "lambda",
            "powershell", "bash", "python", "ci/cd", "git",
            "ticketing systems", "customer service"
        ],
        "weights": {
            "aws": 5, "azure": 4, "gcp": 4, "linux": 4, "troubleshooting": 5,
            "networking": 4, "ec2": 3, "s3": 3, "customer service": 3
        }
    },
    "IT Project Manager": {
        "skills": [
            "project management", "agile", "scrum", "kanban", "waterfall",
            "jira", "confluence", "ms project", "trello", "asana",
            "stakeholder management", "budgeting", "resource planning",
            "risk management", "communication", "leadership", "pmp",
            "prince2", "itil", "vendor management", "documentation",
            "reporting", "gantt charts"
        ],
        "weights": {
            "project management": 5, "agile": 5, "scrum": 5, "jira": 4,
            "stakeholder management": 4, "leadership": 4, "pmp": 4,
            "communication": 4, "risk management": 4
        }
    },
    "IT Security Engineer": {
        "skills": [
            "networking", "tcp/ip", "firewalls", "ids/ips", "vpn",
            "owasp", "penetration testing", "vulnerability assessment",
            "siems", "splunk", "elastic", "wireshark", "nmap",
            "cryptography", "ssl/tls", "pki", "linux", "windows server",
            "active directory", "powershell", "python", "bash",
            "compliance", "iso 27001", "gdpr", "incident response",
            "forensics", "git"
        ],
        "weights": {
            "networking": 5, "firewalls": 4, "siems": 4,
            "penetration testing": 4, "owasp": 4, "compliance": 4,
            "incident response": 5
        }
    }
}