"""End-to-end test using mock data — verifies template filling without API calls."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from template_filler import fill_template

# Mock data shaped like what Claude returns
MOCK_CANDIDATE = {
    "first_name": "Sipho",
    "surname": "Mthembu",
    "identity_number": "(info absent on CV)",
    "equity": "(info absent on CV)",
    "residential_area": "Sandton, Johannesburg",
    "language": "English, isiZulu, Sesotho",
    "transport": "Own transport",
    "drivers_licence": "Code 8",
    "current_salary": "R65,000 per month",
    "required_salary": "R85,000 - R95,000 per month",
    "availability": "2 calendar months notice",
    "achievements": [
        "Top Performer Award - Tiger Brands 2021",
        "Successfully launched Jungle Oats new SKU range generating R80M annual revenue",
        "Grew Knorr brand market share by 6 percentage points over 2 years"
    ],
    "computer_skills": [
        "MS Office (Word, Excel, PowerPoint, Outlook) - Advanced",
        "Google Analytics - Certified",
        "HubSpot Marketing Hub",
        "Adobe Creative Suite (Photoshop, Illustrator)",
        "SAP Marketing Cloud"
    ],
    "education": [
        {
            "institution": "University of the Witwatersrand (Wits Business School)",
            "date": "2017",
            "qualification": "Postgraduate Diploma in Marketing Management"
        },
        {
            "institution": "University of Pretoria",
            "date": "2016",
            "qualification": "Bachelor of Commerce (Honours), Marketing"
        }
    ],
    "employment_history": [
        {
            "company": "Unilever South Africa",
            "period": "Mar 2022 - Present",
            "position": "Marketing Manager",
            "duties": [
                "Led integrated marketing campaigns for Knorr and Robertsons brands, achieving 18% YoY revenue growth",
                "Managed a marketing budget of R45M across digital, TV, and in-store activations",
                "Built and managed a team of 7 marketing professionals",
                "Spearheaded shift to programmatic advertising, reducing CAC by 32%"
            ],
            "reason_for_leaving": "(info absent on CV)"
        },
        {
            "company": "Tiger Brands",
            "period": "Jun 2019 - Feb 2022",
            "position": "Senior Brand Executive",
            "duties": [
                "Managed brand strategy for Jungle Oats portfolio, growing market share from 28% to 34%",
                "Launched 4 new SKUs that contributed R80M to annual revenue",
                "Collaborated with R&D, sales, and supply chain on go-to-market plans"
            ],
            "reason_for_leaving": "Sought greater scope at Unilever"
        },
        {
            "company": "Distell Group",
            "period": "Jan 2018 - May 2019",
            "position": "Marketing Coordinator",
            "duties": [
                "Supported brand managers on Hunter's and Savanna marketing campaigns",
                "Coordinated event activations at major SA festivals",
                "Managed social media content calendars across 5 brand pages"
            ],
            "reason_for_leaving": "Career progression to brand executive role"
        }
    ],
    "references": [
        {
            "name": "Sarah Naidoo",
            "company": "Tiger Brands",
            "phone": "+27 11 555 0123"
        },
        {
            "name": "Michael van der Merwe",
            "company": "Distell Group",
            "phone": "+27 21 809 7000"
        }
    ]
}


if __name__ == "__main__":
    template = Path(__file__).parent / "templates" / "pro_talent_template.docx"
    output = Path(__file__).parent / "output" / "Sipho_Mthembu_PT_profile.docx"

    fill_template(template, MOCK_CANDIDATE, output)
    print(f"Filled Pro Talent template saved to {output}")
