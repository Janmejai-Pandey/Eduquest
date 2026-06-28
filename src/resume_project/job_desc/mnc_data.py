"""
mnc_data.py
MNC corporate / business job role profiles.
"""

job_skill_profiles = {
    "Business Analyst": {
        "skills": [
            "requirements gathering", "stakeholder management", "sql",
            "excel", "powerpoint", "tableau", "power bi", "data analysis",
            "process mapping", "uml", "agile", "scrum", "jira",
            "confluence", "documentation", "user stories", "wireframing",
            "gap analysis", "business process", "communication",
            "presentation", "problem solving", "critical thinking"
        ],
        "weights": {
            "requirements gathering": 5, "sql": 4, "excel": 4,
            "tableau": 3, "data analysis": 5, "agile": 4,
            "stakeholder management": 4, "documentation": 4,
            "communication": 4
        }
    },
    "Product Manager": {
        "skills": [
            "product management", "roadmap planning", "user research",
            "market analysis", "competitor analysis", "agile", "scrum",
            "kanban", "jira", "confluence", "wireframing", "figma",
            "product strategy", "okrs", "kpis", "metrics", "a/b testing",
            "analytics", "google analytics", "mixpanel", "stakeholder management",
            "communication", "leadership", "presentation",
            "data-driven decision making"
        ],
        "weights": {
            "product management": 5, "roadmap planning": 5, "agile": 4,
            "user research": 4, "market analysis": 4,
            "stakeholder management": 5, "kpis": 4, "communication": 4,
            "leadership": 4
        }
    },
    "Project Manager (MNC)": {
        "skills": [
            "project management", "pmp", "prince2", "agile", "scrum",
            "waterfall", "ms project", "jira", "confluence", "trello",
            "budgeting", "resource planning", "risk management",
            "stakeholder management", "vendor management",
            "communication", "leadership", "team management",
            "documentation", "reporting", "gantt charts",
            "critical path method", "earned value management"
        ],
        "weights": {
            "project management": 5, "pmp": 4, "agile": 5, "scrum": 5,
            "stakeholder management": 5, "leadership": 5,
            "risk management": 4, "communication": 4
        }
    },
    "Consultant": {
        "skills": [
            "consulting", "business analysis", "strategy", "research",
            "market analysis", "financial modeling", "excel", "powerpoint",
            "tableau", "data analysis", "problem solving", "client management",
            "stakeholder management", "presentation", "communication",
            "report writing", "critical thinking", "process improvement",
            "change management", "sap", "salesforce"
        ],
        "weights": {
            "consulting": 5, "business analysis": 5, "strategy": 5,
            "excel": 4, "powerpoint": 4, "data analysis": 4,
            "client management": 5, "presentation": 4
        }
    },
    "Operations Manager": {
        "skills": [
            "operations management", "supply chain", "logistics",
            "inventory management", "process improvement", "lean",
            "six sigma", "kpis", "metrics", "team management", "leadership",
            "budgeting", "vendor management", "negotiation", "sap", "erp",
            "excel", "data analysis", "tableau", "communication",
            "problem solving", "decision making"
        ],
        "weights": {
            "operations management": 5, "process improvement": 4,
            "lean": 4, "six sigma": 4, "team management": 5,
            "leadership": 5, "budgeting": 4, "sap": 4
        }
    },
    "HR Business Partner": {
        "skills": [
            "human resources", "talent acquisition", "recruitment",
            "employee relations", "performance management", "compensation",
            "benefits", "hr policies", "labor law", "training and development",
            "succession planning", "diversity and inclusion", "workday",
            "successfactors", "sap hr", "excel", "powerpoint",
            "data analysis", "hr analytics", "communication",
            "stakeholder management", "negotiation", "conflict resolution"
        ],
        "weights": {
            "human resources": 5, "talent acquisition": 4,
            "employee relations": 4, "performance management": 4,
            "communication": 5, "stakeholder management": 4
        }
    },
    "Financial Analyst": {
        "skills": [
            "financial modeling", "excel", "vba", "powerpoint", "sql",
            "tableau", "power bi", "accounting", "gaap", "ifrs",
            "budgeting", "forecasting", "variance analysis", "valuation",
            "financial statements", "ratio analysis", "investment analysis",
            "risk analysis", "sap", "oracle", "bloomberg",
            "data analysis", "communication", "presentation",
            "attention to detail"
        ],
        "weights": {
            "financial modeling": 5, "excel": 5, "accounting": 5,
            "budgeting": 4, "forecasting": 4, "sql": 3,
            "data analysis": 4, "presentation": 3
        }
    }
}